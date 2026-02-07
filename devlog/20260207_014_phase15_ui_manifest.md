# Phase 15: UI Manifest (선언적 뷰 정의)

**날짜:** 2026-02-07
**브랜치:** `feature/scoda-implementation`

## 작업 내용

SCODA UI 레이어의 세 번째 계층인 **UI Manifest**를 구현.
Display Intent(Phase 14)가 "genera는 tree로 보여라" 같은 힌트만 제공했다면,
UI Manifest는 구체적인 뷰 구조(컬럼, 정렬, 검색, 아이콘 등)를 JSON으로 정의.

## 새 테이블

### ui_manifest
| 컬럼 | 타입 | 설명 |
|------|------|------|
| name | TEXT PK | 매니페스트 식별자 (default) |
| description | TEXT | 설명 |
| manifest_json | TEXT | 전체 JSON 뷰 정의 |
| created_at | TEXT | 생성 시각 |

## 매니페스트 내용 (6개 뷰 정의)

| 뷰 | 타입 | source_query | 설명 |
|----|------|-------------|------|
| taxonomy_tree | tree | taxonomy_tree | 기존 트리뷰 |
| genera_table | table | genera_list | 전체 Genus 목록 |
| genus_detail | detail | genus_detail | Genus 상세 |
| references_table | table | bibliography_list | 참고문헌 |
| formations_table | table | formations_list | 지층 |
| countries_table | table | countries_list | 국가 |

table 타입 뷰는 columns (key, label, sortable, searchable, type), default_sort, searchable 속성을 포함.

## API

- `GET /api/manifest` — 기본 매니페스트 반환 (manifest_json을 파싱하여 JSON 객체로 반환)
  - 매니페스트 없으면 404

## 프론트엔드 변경

- **View Tabs**: navbar 아래에 매니페스트 기반 탭 UI 동적 생성
  - detail 타입은 탭에서 제외
  - 매니페스트 로드 실패 시 기존 UI 유지 (graceful degradation)
- **Table View**: 매니페스트 columns 정의를 사용한 범용 테이블 렌더러
  - 컬럼 클릭 정렬 (asc/desc 토글)
  - 검색 (searchable 컬럼 대상)
  - `/api/queries/<name>/execute` API 활용
- **View Switching**: tree ↔ table 뷰 전환

## 새 파일

- `scripts/add_scoda_manifest.py` — 마이그레이션 스크립트

## 수정 파일

- `app.py` — `/api/manifest` 엔드포인트 + `import json`
- `templates/index.html` — 뷰 탭 바 + 뷰 컨테이너
- `static/js/app.js` — 매니페스트 로딩, 뷰 전환, 테이블 렌더러
- `static/css/style.css` — 탭/테이블 뷰 스타일
- `test_app.py` — fixture 업데이트 + TestApiManifest (16개 테스트)

## 테스트 결과

- 기존: 63개 → 신규: 79개 (전체 통과)
- 신규 16개: TestApiManifest 클래스
  - 응답 구조, JSON 파싱, 뷰 타입, 컬럼 정의, source_query 통합 검증

## schema_descriptions 추가

- ui_manifest 테이블/컬럼 설명 5건 추가 (총 107건)
