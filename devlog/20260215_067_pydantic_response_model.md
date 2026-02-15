# Pydantic response_model 추가 — FastAPI 응답 스키마 정의

**날짜:** 2026-02-15
**유형:** 작업 완료

## 목표

FastAPI 엔드포인트에 Pydantic response_model을 추가하여 `/docs` 자동 문서에 응답 스키마 표시 + 타입 안전성 확보.

## 변경 내용

### Pydantic 모델 10개 추가 (`app.py` 상단)

| 모델 | 용도 |
|------|------|
| `ProvenanceItem` | `/api/provenance` 응답 항목 |
| `DisplayIntentItem` | `/api/display-intent` 응답 항목 |
| `QueryItem` | `/api/queries` 응답 항목 |
| `QueryResult` | `/api/queries/{name}/execute` 응답 |
| `PackageInfo` | `ManifestResponse` 내부 패키지 정보 |
| `ManifestResponse` | `/api/manifest` 응답 |
| `AnnotationItem` | annotation 관련 응답 항목 |
| `ErrorResponse` | 에러 응답 (`{"error": "..."}`) |
| `DeleteResponse` | annotation 삭제 응답 |

### 엔드포인트별 적용

- **고정 구조** (response_model 직접 지정): provenance, display-intent, queries, manifest, annotations GET
- **동적 구조** (responses 문서만): detail, composite — `dict[str, Any]` 반환이라 response_model 생략
- **QueryResult**: `rows: list[dict[str, Any]]` — 반고정 구조로 response_model 적용
- **POST/DELETE**: JSONResponse 사용 유지, responses 문서로 스키마 노출

### 테스트

- `TestOpenAPIDocs.test_openapi_json_contains_schemas`: `/openapi.json`에 모델 정의 포함 확인
- 229개 전부 통과 (기존 228 + 신규 1)

## 변경 파일

| 파일 | 변경 | 설명 |
|------|------|------|
| `scoda_desktop/app.py` | 중 | Pydantic 모델 ~60줄 추가, 데코레이터에 response_model/responses 추가 |
| `tests/test_runtime.py` | 소 | OpenAPI 스키마 테스트 1개 추가 |

## 계획 문서

`devlog/20260215_P49_pydantic_response_model.md`
