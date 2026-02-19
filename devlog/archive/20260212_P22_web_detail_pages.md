# Web UI 상세 페이지 및 상호 링크 추가 계획

> 목적: Countries, Formations, Bibliography 테이블 뷰에 클릭 가능한 상세 모달을 추가하고, Genus detail과 상호 링크하여 엔티티 간 양방향 탐색 가능하게 함

---

## 1. 배경

### 1.1 현재 상태

- Countries, Formations, Bibliography, All Genera 테이블 뷰는 목록만 표시
- 행을 클릭해도 아무 동작 없음
- Genus detail 모달의 countries/formations 항목에도 링크 없음
- 엔티티 간 상호 탐색 불가능

### 1.2 목표

1. Countries/Formations/Bibliography/All Genera 테이블 행 클릭 → 상세 모달
2. 각 상세 모달에 연결된 genera 목록 표시 (클릭 → genus detail)
3. Genus detail의 countries/formations에 역방향 링크 추가

---

## 2. 수정 파일

| 파일 | 변경 |
|------|------|
| `app.py` | API 3개 추가 (`/api/country/<id>`, `/api/formation/<id>`, `/api/bibliography/<id>`) |
| `static/js/app.js` | 상세 함수 3개 + 행 클릭 핸들러 + genus detail 링크 보강 |
| `static/css/style.css` | 클릭 가능 행 + 링크 스타일 |

---

## 3. 구현 단계

### Step 1: `app.py` — API 엔드포인트 3개 추가

**`GET /api/country/<int:country_id>`**
- countries 기본 정보 (name, taxa_count)
- cow_states 매핑 정보 (있으면, country_cow_mapping + cow_states JOIN)
- 연결된 genera (genus_locations JOIN taxonomic_ranks)

**`GET /api/formation/<int:formation_id>`**
- formations 기본 정보 (name, formation_type, country, period, taxa_count)
- 연결된 genera (genus_formations JOIN taxonomic_ranks)

**`GET /api/bibliography/<int:bib_id>`**
- bibliography 기본 정보 전체
- 관련 genera: author 성(last name) + year 매칭으로 검색

### Step 2: `static/js/app.js` — 테이블 행 클릭 핸들러

`renderTableViewRows()` 수정 — viewKey에 따라 행에 onclick 추가:
- `countries_table` → `showCountryDetail(row.id)`
- `formations_table` → `showFormationDetail(row.id)`
- `references_table` → `showBibliographyDetail(row.id)`
- `genera_table` → `showGenusDetail(row.id)`

### Step 3: `static/js/app.js` — 상세 함수 3개 추가

기존 `showGenusDetail()` 패턴 따름. 같은 `#genusModal` 재사용.

- `showCountryDetail(id)` — 국가 정보 + COW 매핑 + genera 테이블
- `showFormationDetail(id)` — formation 정보 + genera 테이블
- `showBibliographyDetail(id)` — bibliography 정보 + raw entry + 관련 genera

### Step 4: `static/js/app.js` — Genus detail 내 링크 추가

- Countries 항목에 `showCountryDetail()` 링크
- Formations 항목 렌더링 추가 + `showFormationDetail()` 링크

### Step 5: `static/css/style.css` — 스타일 추가

- 클릭 가능 행에 `cursor: pointer`
- `.detail-link` 스타일
- `.genera-list` 스크롤 가능 영역

---

## 4. 검증

1. Countries 탭 → 행 클릭 → 국가 상세 + genera 목록 → genus 클릭 → genus detail
2. Formations 탭 → 행 클릭 → formation 상세 + genera 목록 → genus 클릭 → genus detail
3. Bibliography 탭 → 행 클릭 → bibliography 상세 + 관련 genera
4. All Genera 탭 → 행 클릭 → genus detail 모달
5. Genus detail → Countries 링크 → country detail
6. Genus detail → Formations 링크 → formation detail
7. 기존 테스트 111개 통과
