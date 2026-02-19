# Pydantic response_model — FastAPI 응답 스키마 정의

## Context

FastAPI 마이그레이션 완료 후, 모든 엔드포인트가 raw dict/list를 반환하고 있어 `/docs` 자동 문서에 응답 스키마가 표시되지 않음. Pydantic response_model을 추가하여 타입 안전성과 자동 문서화를 확보.

## 현재 상태

- 12개 엔드포인트 중 request model은 `AnnotationCreate` 1개만 존재
- response_model 없음 → `/docs`에서 모든 응답이 빈 스키마로 표시
- 에러 응답은 수동 `JSONResponse({"error": "..."}, status_code=N)`으로 처리

## 설계

### 엔드포인트 분류

**A) 고정 구조 (정확한 모델 정의 가능):**

| 엔드포인트 | response_model |
|-----------|---------------|
| `GET /api/provenance` | `list[ProvenanceItem]` |
| `GET /api/display-intent` | `list[DisplayIntentItem]` |
| `GET /api/queries` | `list[QueryItem]` |
| `GET /api/manifest` | `ManifestResponse` |
| `GET /api/annotations/{type}/{id}` | `list[AnnotationItem]` |
| `POST /api/annotations` | — (다중 상태코드, JSONResponse 유지) |
| `DELETE /api/annotations/{id}` | — (다중 상태코드, JSONResponse 유지) |

**B) 동적 구조 (DB 쿼리 결과, 형태 가변):**

| 엔드포인트 | 처리 |
|-----------|------|
| `GET /api/queries/{name}/execute` | `QueryResult` (rows: `list[dict[str, Any]]`) |
| `GET /api/detail/{query_name}` | `dict[str, Any]` (response_model 생략, `responses` 문서만) |
| `GET /api/composite/{view_name}` | `dict[str, Any]` (response_model 생략, `responses` 문서만) |

**C) HTML/파일 응답 (모델 불필요):**

| 엔드포인트 | 처리 |
|-----------|------|
| `GET /` | `HTMLResponse` (변경 없음) |
| `GET /{filename:path}` | `FileResponse` (변경 없음) |

### Pydantic 모델 정의

`app.py` 상단, `AnnotationCreate` 옆에 정의 (별도 파일 불필요 — 모델 10개 미만):

```python
from pydantic import BaseModel
from typing import Any, Optional

class ProvenanceItem(BaseModel):
    id: int
    source_type: str
    citation: str
    description: Optional[str] = None
    year: Optional[int] = None
    url: Optional[str] = None

class DisplayIntentItem(BaseModel):
    id: int
    entity: str
    default_view: str
    description: Optional[str] = None
    source_query: Optional[str] = None
    priority: int = 0

class QueryItem(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    params: Optional[str] = None  # JSON string
    created_at: str

class QueryResult(BaseModel):
    query: str
    columns: list[str]
    row_count: int
    rows: list[dict[str, Any]]

class PackageInfo(BaseModel):
    name: str = ""
    artifact_id: str = ""
    version: str = ""
    description: str = ""

class ManifestResponse(BaseModel):
    name: str
    description: Optional[str] = None
    manifest: dict[str, Any]   # 뷰 정의는 가변 구조
    created_at: str
    package: PackageInfo

class AnnotationItem(BaseModel):
    id: int
    entity_type: str
    entity_id: int
    entity_name: Optional[str] = None
    annotation_type: str
    content: str
    author: Optional[str] = None
    created_at: str

class ErrorResponse(BaseModel):
    error: str

class DeleteResponse(BaseModel):
    message: str
    id: int
```

### 엔드포인트 변경

```python
# 고정 구조 — response_model 추가
@app.get('/api/provenance', response_model=list[ProvenanceItem])
@app.get('/api/display-intent', response_model=list[DisplayIntentItem])
@app.get('/api/queries', response_model=list[QueryItem])
@app.get('/api/manifest', response_model=ManifestResponse)
@app.get('/api/annotations/{entity_type}/{entity_id}', response_model=list[AnnotationItem])

# 동적 구조 — responses 문서만 추가
@app.get('/api/queries/{name}/execute', response_model=QueryResult,
         responses={404: {"model": ErrorResponse}, 400: {"model": ErrorResponse}})
@app.get('/api/detail/{query_name}',
         responses={404: {"model": ErrorResponse}, 400: {"model": ErrorResponse}})
@app.get('/api/composite/{view_name}',
         responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})

# POST/DELETE — status_code 명시 + responses 문서
@app.post('/api/annotations', status_code=201,
          responses={201: {"model": AnnotationItem}, 400: {"model": ErrorResponse}})
@app.delete('/api/annotations/{annotation_id}',
            responses={200: {"model": DeleteResponse}, 404: {"model": ErrorResponse}})
```

### 주의사항

- `_fetch_provenance()` 등 helper 함수의 반환값은 이미 dict list → Pydantic이 자동 직렬화
- `JSONResponse`로 감싸는 에러 응답은 response_model 바이패스되므로 변경 불필요
- `response_model`이 붙은 엔드포인트에서 `JSONResponse`를 직접 반환하면 모델 검증이 적용되지 않음 → 정상 응답은 dict/list 반환 유지, 에러만 `JSONResponse` 사용

## 변경 파일

| 파일 | 변경 | 설명 |
|------|------|------|
| `scoda_desktop/app.py` | 중 | Pydantic 모델 ~50줄 추가, 데코레이터에 response_model/responses 추가 |
| `tests/test_runtime.py` | 소 | `/docs` 접근 테스트 1개 추가 |

## 검증

```bash
pytest tests/ -x -q   # 228+ 통과

# OpenAPI 스키마 확인
python -m scoda_desktop.serve
curl http://localhost:8080/openapi.json | python -m json.tool
# → components.schemas에 ProvenanceItem, QueryResult 등 모델 표시 확인
# → /docs 페이지에서 응답 스키마 확인
```
