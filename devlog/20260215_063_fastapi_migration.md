# 063: Flask → FastAPI 마이그레이션

**날짜**: 2026-02-15
**상태**: 완료
**계획 문서**: `devlog/20260215_P46_fastapi_migration.md`

## 요약

Flask(WSGI) + asgiref WsgiToAsgi 이중 스택 → FastAPI 단일 ASGI 스택 전환.
P45 로드맵의 최우선 과제. 8개 파일 변경, 226개 테스트 전부 통과.

## 변경 내역

### requirements.txt
- `flask`, `asgiref` 제거 → `fastapi`, `httpx` 추가
- `uvicorn`, `starlette` 유지 (기존 MCP에서 사용 중)

### scoda_desktop/app.py (핵심)
- `Flask(__name__)` → `FastAPI(title="SCODA Desktop")`
- `@app.after_request` CORS → `CORSMiddleware` 미들웨어
- `Jinja2Templates` (TemplateResponse) 도입
- 12개 라우트 데코레이터: `@app.route()` → `@app.get()` / `@app.post()` / `@app.delete()`
- Path param 문법: `<name>` → `{name}`, `<int:id>` → 타입 힌트 `id: int`
- `request.args` → `request.query_params`
- `jsonify(result)` → dict 직접 반환 (FastAPI 자동 직렬화)
- `render_template` → `templates.TemplateResponse(request, "index.html")`
- `send_from_directory` → `FileResponse`
- `AnnotationCreate(BaseModel)` Pydantic 모델 추가 (POST /api/annotations)
- `__main__`: `app.run()` → `uvicorn.run(app)`
- 모든 헬퍼 함수 (`_fetch_*`, `_execute_query`, `_create_annotation` 등) 변경 없음

### scoda_desktop/serve.py
- `app.run(debug=False, ...)` → `uvicorn.run(app, host='127.0.0.1', port=8080, log_level='info')`
- Flask import/에러 메시지 정리

### scoda_desktop/gui.py
- `_run_flask_app()` → `_run_web_server()`: `WsgiToAsgi` 래핑 제거, `from .app import app` 직접 사용
- `self.flask_app` 인스턴스 변수 제거
- 주석/로그: "Flask" → "web server"
- 로그 감지: "Serving Flask" → "Uvicorn running"

### ScodaDesktop.spec
- hiddenimports: `flask`, `asgiref`, `asgiref.wsgi` → `fastapi`, `fastapi.responses`, `fastapi.staticfiles`, `fastapi.templating`, `fastapi.middleware.cors`

### tests/conftest.py
- Flask `app.test_client()` → Starlette `TestClient(app)`
- `app.config['TESTING'] = True` 제거

### tests/test_runtime.py + tests/test_trilobase.py
| 패턴 | Before (Flask) | After (httpx/TestClient) | 건수 |
|------|---------------|--------------------------|------|
| JSON 파싱 | `json.loads(response.data)` | `response.json()` | 72건 |
| POST body | `data=json.dumps({...}), content_type='...'` | `json={...}` | 9건 |
| HTML 텍스트 | `response.data.decode()` | `response.text` | 2건 |
| 바이너리 | `response.data` | `response.content` | 3건 |
| 인라인 클라이언트 | `app.test_client()` | `TestClient(app)` | 5건 |
| CORS 테스트 | 헤더 이름 대문자 | 소문자 + Origin 헤더 추가 | 2건 |

## 변경 없는 파일

- `scoda_desktop/scoda_package.py` — Flask 의존 없음
- `scoda_desktop/mcp_server.py` — 독립 Starlette/MCP 앱 (포트 8081)
- `scoda_desktop/templates/index.html` — Jinja2 호환
- `scoda_desktop/static/` — 정적 파일
- `scripts/`, `data/`, `spa/`, `examples/` — 무관

## 핵심 설계 결정

| 결정 사항 | 선택 | 이유 |
|-----------|------|------|
| 라우트 함수 | sync `def` | SQLite 동기, FastAPI threadpool 자동 실행 |
| MCP 통합 | 별도 유지 (8081) | 안정화 후 통합, 동시 변경 리스크 회피 |
| Response 모델 | dict 기반 유지 | 동적 구조(ui_queries 등)가 많아 Pydantic 모델은 추후 |
| POST body | Pydantic BaseModel | annotation 생성에만 사용 |

## 테스트

```
226 passed in 193s
```

## 후속 과제

1. MCP + Web API 단일 프로세스 통합 (포트 8080 하나로)
2. Pydantic response_model 추가 → OpenAPI 자동 문서화 (`/docs`)
3. aiosqlite 전환 (성능 필요 시)
