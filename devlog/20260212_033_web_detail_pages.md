# Web UI 상세 페이지 및 상호 링크 추가

**날짜:** 2026-02-12
**Phase:** Web UI Enhancement

## 작업 내용

Countries, Formations, Bibliography, All Genera 테이블 뷰에서 행 클릭 시 상세 모달을 표시하고, 각 엔티티 간 상호 탐색이 가능하도록 링크를 추가했다.

## 변경 파일

### `app.py` — API 엔드포인트 3개 추가

| 엔드포인트 | 설명 |
|-----------|------|
| `GET /api/country/<id>` | 국가 기본정보 + COW 매핑 + 연결된 genera |
| `GET /api/formation/<id>` | Formation 기본정보 + 연결된 genera |
| `GET /api/bibliography/<id>` | 참고문헌 기본정보 + raw_entry + 관련 genera |

- Bibliography의 관련 genera: 첫 번째 저자 성(last name) + year 매칭으로 검색

### `static/js/app.js` — 프론트엔드 상호 링크

**테이블 행 클릭 핸들러:**
- `countries_table` → `showCountryDetail(id)`
- `formations_table` → `showFormationDetail(id)`
- `references_table` → `showBibliographyDetail(id)`
- `genera_table` → `showGenusDetail(id)`

**상세 모달 함수 3개:**
- `showCountryDetail()`: 국가명, COW 매핑, genera 테이블
- `showFormationDetail()`: Formation 정보, genera 테이블
- `showBibliographyDetail()`: 전체 인용 정보, raw entry, 관련 genera

**Genus detail 링크 보강:**
- Countries 항목: 클릭 → `showCountryDetail()`
- Formations 항목 (신규): 클릭 → `showFormationDetail()`

### `static/css/style.css` — 스타일

- `.manifest-table tbody tr[onclick]`: cursor: pointer
- `.detail-link`: 인라인 엔티티 링크 스타일
- `.genera-list`: max-height 400px, 스크롤

## 테스트

- 기존 111개 테스트 전부 통과
