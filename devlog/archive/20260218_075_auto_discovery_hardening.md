# 075: Auto-Discovery 보완 — 메타데이터 차단 + openDetail fallback (A-1)

**날짜:** 2026-02-18
**로드맵:** A-1 (Auto-Discovery Detail View)

## 작업 내용

A-1 기존 구현 감사 후 누락된 3가지 보완:

### 1. 메타데이터 테이블 접근 차단 (`app.py`)
- `/api/auto/detail/{table}` 엔드포인트에 `SCODA_META_TABLES` 차단 추가
- `ui_manifest`, `ui_queries`, `artifact_metadata` 등 6개 테이블 → 403 Forbidden
- 기존: sqlite_master 존재 확인만 (메타데이터 테이블도 접근 가능했음)

### 2. `openDetail()` fallback + `renderAutoDetail()` (`app.js`)
- manifest에 detail view가 없을 때 자동 fallback:
  - `openDetail('foo_detail', id)` → `/api/auto/detail/foo?id=N` 호출
- `renderAutoDetail()`: 모든 컬럼을 key-value grid로 렌더링
  - 제목: `data.name || data.title || data.code || "{table} #{id}"`
  - null 값 필터링, 컬럼명 Title Case 변환

### 3. 테스트 2개 추가
- 메타데이터 테이블 6개 전부 403 확인 (`client` fixture)
- no_manifest 환경에서도 메타데이터 차단 확인 (`no_manifest_client` fixture)

## 수정 파일

| 파일 | 변경 |
|------|------|
| `scoda_desktop/app.py` | +5줄 (메타데이터 차단) |
| `scoda_desktop/static/js/app.js` | +38줄 (fallback + renderAutoDetail) |
| `tests/test_runtime.py` | +12줄 (테스트 2개) |

## 테스트: 247개 전부 통과
