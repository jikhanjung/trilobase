# Plan P34: Phase 40 — CORS + Custom SPA Example + EXE Renaming

**작성일:** 2026-02-13

## Context

Phase 39에서 manifest-driven 범용 렌더러를 완성했다. 이제 SCODA Desktop을 진정한 "SCODA 런타임"으로 만들기 위해:
1. **CORS 추가** — 외부 SPA가 Flask API를 소비할 수 있도록
2. **Genus Explorer 예제 SPA** — manifest 방식 외에 커스텀 SPA로 API를 활용하는 예시
3. **EXE 리네이밍** — `trilobase.exe` → `ScodaDesktop.exe` (범용 런타임 명칭)

## 파일 변경 목록

| 파일 | 변경 내용 |
|------|-----------|
| `app.py` | CORS `after_request` 핸들러 추가 |
| `examples/genus-explorer/index.html` | **신규** — 단일 파일 Genus Explorer SPA |
| `trilobase.spec` → `ScodaDesktop.spec` | **리네임** + name 변경 |
| `scripts/build.py` | exe_name, spec 파일명 변경 |
| `scripts/gui.py` | 클래스명 `TrilobaseGUI` → `ScodaDesktopGUI` |
| `templates/index.html` | title, navbar 브랜드 업데이트 |
| `test_app.py` | CORS 테스트 추가 |

`scoda_package.py`는 변경 없음 (데이터 파일명 `trilobase.scoda`/`trilobase.db`는 데이터셋 이름이므로 유지).

---

## Phase 40a: CORS 추가

**`app.py`** — `app = Flask(__name__)` 직후에 추가:

```python
@app.after_request
def add_cors_headers(response):
    """Allow cross-origin requests for custom SPA support."""
    origin = request.headers.get('Origin', '*')
    response.headers['Access-Control-Allow-Origin'] = origin
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, DELETE, OPTIONS'
    return response
```

별도 라이브러리(flask-cors) 없이 `after_request`로 구현. localhost 기반 사용이므로 origin 반영.

**`test_app.py`** — CORS 테스트 2개 추가:
- `test_cors_headers_present` — API 응답에 `Access-Control-Allow-Origin` 존재 확인
- `test_cors_preflight` — OPTIONS 요청 처리 확인

---

## Phase 40b: Genus Explorer 예제 SPA

**`examples/genus-explorer/index.html`** — 단일 HTML 파일 (~250줄):

기능:
- 상단: 검색바 (이름 실시간 필터) + 시대 필터 드롭다운
- 본문: 반응형 카드 그리드 (genus 카드: 이름, 저자·연도, 시대, type species, valid/invalid 뱃지)
- 카드 클릭 → 모달에 상세 정보 (`/api/genus/{id}`)
- 하단: 결과 수 + 총 수

사용 API:
- `GET /api/queries/genera_list/execute` — 전체 genus 목록
- `GET /api/genus/{id}` — 상세 정보

구현:
- 순수 HTML + CSS + vanilla JS (프레임워크 없음)
- API 베이스 URL 설정 (`const API_BASE = 'http://localhost:8080'`)
- Bootstrap 5 CDN (SCODA Desktop과 일관된 스타일)
- 클라이언트 사이드 필터링 (전체 로드 후 JS 필터)
- 반응형 카드 레이아웃 (Bootstrap grid, col-md-4)

---

## Phase 40c: EXE 리네이밍

### 1. `trilobase.spec` → `ScodaDesktop.spec`

파일 리네임 (git mv) + 내용 변경:
- Line 56: `name='trilobase'` → `name='ScodaDesktop'`
- Line 114: `name='trilobase_mcp'` → `name='ScodaDesktop_mcp'`
- 주석/docstring 업데이트

### 2. `scripts/build.py`

- Line 55: `'trilobase.spec'` → `'ScodaDesktop.spec'`
- Line 123: `exe_name = 'trilobase.exe'` → `'ScodaDesktop.exe'`
- Line 137: 배포 안내 메시지 업데이트
- Line 147-148: 타이틀 "Trilobase" → "SCODA Desktop"
- Line 159: spec 파일 존재 확인 업데이트

### 3. `scripts/gui.py`

- Line 45: `class TrilobaseGUI` → `class ScodaDesktopGUI`
- Line 676: `gui = TrilobaseGUI()` → `gui = ScodaDesktopGUI()`
- (title "SCODA Desktop"은 이미 적용됨)

### 4. `templates/index.html`

- Line 6: `<title>Trilobase - Trilobite Taxonomy Database</title>` → `<title>SCODA Desktop</title>`
- Line 16: navbar brand `Trilobase` → `SCODA Desktop`

---

## Phase 40d: 테스트 + 문서

- `pytest test_app.py test_mcp_basic.py test_mcp.py` — 전체 통과 확인
- devlog 작성: `devlog/20260213_050_phase40_cors_spa_rename.md`
- `docs/HANDOVER.md` 갱신

---

## 검증 방법

1. `pytest` — 전체 테스트 통과 (192 기존 + 2 CORS = 194)
2. `examples/genus-explorer/index.html`을 브라우저에서 `file://`로 직접 열어 Flask API 호출 확인
3. `python scripts/build.py` — `ScodaDesktop.spec` 참조 확인
