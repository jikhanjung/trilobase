# Phase 40: CORS + Custom SPA Example + EXE Renaming

**날짜:** 2026-02-13

## 목표

SCODA Desktop을 진정한 "SCODA 런타임"으로 만들기 위한 3가지 개선:
1. CORS 헤더 추가 — 외부 SPA가 Flask API를 소비할 수 있도록
2. Genus Explorer 예제 SPA — manifest 방식 외에 커스텀 SPA로 API를 활용하는 예시
3. EXE 리네이밍 — `trilobase.exe` → `ScodaDesktop.exe`

## 변경 사항

### Phase 40a: CORS 추가

- **`app.py`**: `@app.after_request` 핸들러 추가
  - `Access-Control-Allow-Origin`: 요청 Origin 반영 (없으면 `*`)
  - `Access-Control-Allow-Headers`: `Content-Type`
  - `Access-Control-Allow-Methods`: `GET, POST, DELETE, OPTIONS`
  - 별도 라이브러리(flask-cors) 없이 구현
- **`test_app.py`**: `TestCORS` 클래스 2개 테스트 추가
  - `test_cors_headers_present`: API 응답에 CORS 헤더 존재 확인
  - `test_cors_preflight`: OPTIONS 요청 처리 확인

### Phase 40b: Genus Explorer 예제 SPA

- **`examples/genus-explorer/index.html`** (신규, ~250줄)
  - 순수 HTML + CSS + vanilla JS (프레임워크 없음)
  - Bootstrap 5 CDN (SCODA Desktop과 일관된 스타일)
  - 기능:
    - 실시간 이름 검색 필터
    - 시대(temporal_code) 드롭다운 필터
    - Valid/Invalid 필터
    - 반응형 카드 그리드 (col-md-4 col-lg-3)
    - 카드 클릭 → 모달에 상세 정보 (`/api/genus/{id}`)
    - 결과 수 + 총 수 표시
    - 성능: 500개 제한 렌더링
  - 사용 API:
    - `GET /api/queries/genera_list/execute` — 전체 genus 목록
    - `GET /api/genus/{id}` — 상세 정보
  - `file://`로 직접 열어서 테스트 가능 (CORS 지원)

### Phase 40c: EXE 리네이밍

- **`trilobase.spec` → `ScodaDesktop.spec`** (git mv)
  - `name='trilobase'` → `name='ScodaDesktop'`
  - `name='trilobase_mcp'` → `name='ScodaDesktop_mcp'`
  - 주석/docstring 업데이트
- **`scripts/build.py`**:
  - spec 파일명: `trilobase.spec` → `ScodaDesktop.spec`
  - exe_name: `trilobase.exe` → `ScodaDesktop.exe`
  - 타이틀: "Trilobase" → "SCODA Desktop"
- **`scripts/gui.py`**:
  - `class TrilobaseGUI` → `class ScodaDesktopGUI`
  - 인스턴스 생성 코드 동시 변경
- **`templates/index.html`**:
  - `<title>` → `SCODA Desktop`
  - navbar brand → `SCODA Desktop`

## 변경하지 않은 파일

- `scoda_package.py`: 데이터 파일명 `trilobase.scoda`/`trilobase.db`는 데이터셋 이름이므로 유지
- `mcp_server.py`: 변경 없음

## 테스트 결과

```
194 passed in 229.80s
```

| 파일 | 테스트 수 | 상태 |
|------|---------|------|
| `test_app.py` | 177개 | 통과 |
| `test_mcp_basic.py` | 1개 | 통과 |
| `test_mcp.py` | 16개 | 통과 |
| **합계** | **194개** | **전부 통과** |

## 파일 변경 요약

| 파일 | 변경 |
|------|------|
| `app.py` | CORS after_request 핸들러 추가 |
| `test_app.py` | TestCORS 클래스 (2개 테스트) 추가 |
| `examples/genus-explorer/index.html` | 신규 — 단일 파일 SPA 예제 |
| `trilobase.spec` → `ScodaDesktop.spec` | 리네임 + name 변경 |
| `scripts/build.py` | exe_name, spec, 타이틀 변경 |
| `scripts/gui.py` | TrilobaseGUI → ScodaDesktopGUI |
| `templates/index.html` | title, navbar brand 변경 |
