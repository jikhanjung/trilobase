# P46: Flask → FastAPI 마이그레이션 계획

**날짜**: 2026-02-15
**상태**: 계획

## Context

현재 SCODA Desktop은 **이중 스택**: Flask(WSGI, 포트 8080) + Starlette/Uvicorn(ASGI, MCP SSE 포트 8081)으로 운영 중. FastAPI로 전환하면 단일 ASGI 스택으로 통합되고, 자동 OpenAPI 문서화, Pydantic 검증 등의 이점을 얻는다. P45 로드맵의 최우선 과제.

## 핵심 설계 결정

| 결정 사항 | 선택 | 이유 |
|-----------|------|------|
| 라우트 함수 | **sync `def`** (async 아님) | SQLite는 동기, FastAPI가 threadpool에서 자동 실행, 기존 헬퍼 함수 재사용 |
| MCP 통합 | **별도 유지** (8081) | 안정화 후 통합, 동시 변경 리스크 회피 |
| 마이그레이션 방식 | **일괄 전환** | app.py 431줄, 12 라우트 — 점진적 전환보다 깔끔 |
| Response 모델 | **dict 기반** 유지 | 동적 구조(ui_queries 등)가 많아 Pydantic 모델은 추후 |
| POST body | **Pydantic BaseModel** | annotation 생성에만 사용, 검증 자동화 |

## 파일 변경 계획

### Step 1: `requirements.txt` 수정

```diff
- flask
- asgiref
+ fastapi
+ httpx
```
유지: `uvicorn`, `starlette`, `mcp>=1.0.0`, `pyinstaller`, `requests`, `pytest`, `pytest-asyncio`

### Step 2: `scoda_desktop/app.py` 전환 (핵심)

**변경 범위**: import + CORS + 12개 라우트 데코레이터/응답 패턴
**변경 안 되는 것**: `_fetch_*`, `_execute_query`, `_create_annotation`, `_delete_annotation`, `_get_reference_spa_dir` 헬퍼 함수 전부 그대로 유지

주요 변환 패턴:
```python
# Before (Flask)
from flask import Flask, render_template, jsonify, request, send_from_directory
app = Flask(__name__)
@app.after_request / add_cors_headers
@app.route('/api/queries/<name>/execute')
def api_query_execute(name):
    params = {k: v for k, v in request.args.items()}
    return jsonify(result)

# After (FastAPI)
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
app = FastAPI(title="SCODA Desktop")
app.add_middleware(CORSMiddleware, allow_origins=["*"], ...)
@app.get('/api/queries/{name}/execute')
def api_query_execute(name: str, request: Request):
    params = dict(request.query_params)
    return result  # FastAPI 자동 직렬화
```

라우트별 변환:

| Flask | FastAPI | 비고 |
|-------|---------|------|
| `@app.route('/api/provenance')` | `@app.get('/api/provenance')` | `jsonify()` 제거 |
| `@app.route('/api/display-intent')` | `@app.get('/api/display-intent')` | 동일 |
| `@app.route('/api/queries')` | `@app.get('/api/queries')` | 동일 |
| `@app.route('/api/queries/<name>/execute')` | `@app.get('/api/queries/{name}/execute')` | path param 문법 |
| `@app.route('/api/manifest')` | `@app.get('/api/manifest')` | 404 → `JSONResponse(status_code=404)` |
| `@app.route('/api/detail/<query_name>')` | `@app.get('/api/detail/{query_name}')` | `request.args` → `request.query_params` |
| `@app.route('/api/composite/<view_name>')` | `@app.get('/api/composite/{view_name}')` | 동일 |
| `GET annotations` | `@app.get('/api/annotations/{entity_type}/{entity_id}')` | `<int:id>` → 타입 힌트 |
| `POST annotations` | `@app.post('/api/annotations')` | `request.get_json()` → Pydantic model |
| `DELETE annotations` | `@app.delete('/api/annotations/{annotation_id}')` | 동일 |
| `GET /` | `@app.get('/')` | `render_template` → `Jinja2Templates` |
| `GET /<path:filename>` | `@app.get('/{filename:path}')` | `send_from_directory` → `FileResponse` |
| `__main__` | `uvicorn.run(app, ...)` | `app.run()` 제거 |

### Step 3: `scoda_desktop/serve.py` 수정

```python
# Before
from .app import app
app.run(debug=False, host='127.0.0.1', port=8080, use_reloader=False)

# After
import uvicorn
from .app import app
uvicorn.run(app, host='127.0.0.1', port=8080, log_level='info')
```

### Step 4: `scoda_desktop/gui.py` 수정 (~10줄)

`_run_flask_app()` 메서드에서 `WsgiToAsgi` 래핑 제거:
```python
# Before
from asgiref.wsgi import WsgiToAsgi
asgi_app = WsgiToAsgi(self.flask_app)
config = uvicorn.Config(asgi_app, ...)

# After
from .app import app
config = uvicorn.Config(app, ...)  # FastAPI는 이미 ASGI
```

기타: 주석/로그 메시지에서 "Flask" → "web server" 수정, `self.flask_app` 제거 (직접 import)

### Step 5: `ScodaDesktop.spec` 수정

```diff
hiddenimports에서:
- 'flask',
- 'asgiref',
- 'asgiref.wsgi',
+ 'fastapi',
+ 'fastapi.responses',
+ 'fastapi.staticfiles',
+ 'fastapi.templating',
+ 'fastapi.middleware.cors',
```

### Step 6: 테스트 인프라 수정

**`tests/conftest.py`** — client 픽스처 변경:
```python
# Before
from scoda_desktop.app import app
app.config['TESTING'] = True
with app.test_client() as client: yield client

# After
from starlette.testclient import TestClient
from scoda_desktop.app import app
with TestClient(app) as client: yield client
```

**`tests/test_runtime.py` + `tests/test_trilobase.py`** — 기계적 치환:

| 패턴 | Before (Flask) | After (httpx/TestClient) | 건수 |
|------|---------------|--------------------------|------|
| JSON 파싱 | `json.loads(response.data)` | `response.json()` | 72건 |
| POST body | `data=json.dumps({...}), content_type='application/json'` | `json={...}` | 9건 |
| 바이너리 | `response.data` (나머지) | `response.content` | ~7건 |

### Step 7: devlog + HANDOVER.md 갱신

## 검증

```bash
pip install fastapi httpx && pip uninstall flask asgiref -y
pytest tests/                                    # 226 전체 테스트 통과
python -m scoda_desktop.serve --package trilobase # localhost:8080 확인
python -m scoda_desktop.gui                       # GUI 시작/중지 확인
```

## 변경 없는 파일

- `scoda_desktop/scoda_package.py` — Flask 의존 없음
- `scoda_desktop/mcp_server.py` — 독립 Starlette 앱
- `scoda_desktop/templates/index.html` — Jinja2 호환
- `scoda_desktop/static/` — 정적 파일
- `scripts/`, `data/`, `spa/` — 무관

## 후속 과제 (이번 범위 밖)

1. MCP + Web API 단일 프로세스 통합 (포트 8080 하나로)
2. Pydantic response_model 추가 → OpenAPI 자동 문서화
3. aiosqlite 전환 (성능 필요 시)
