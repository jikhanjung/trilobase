# Phase 14: Display Intent + Saved Queries 구현 완료

**날짜:** 2026-02-07
**브랜치:** `feature/scoda-implementation`

## 작업 내용

SCODA 4-layer UI 모델 중 핵심 2개 레이어를 구현:
- **Level 0 (Display Intent)**: "이 데이터를 어떤 형태로 보여줄 것인가" 힌트
- **Level 2 (Saved Queries)**: 이름 붙은 재사용 가능한 쿼리

## 새 테이블 (2개)

### ui_display_intent (6건)

| entity | default_view | priority | 의미 |
|--------|-------------|----------|------|
| genera | tree | 0 (primary) | 분류 계층이 주요 구조 |
| genera | table | 1 (secondary) | 검색/필터용 평면 목록 |
| references | table | 0 | 참고문헌 정렬 목록 |
| synonyms | graph | 0 | 동의어 네트워크 |
| formations | table | 0 | 지층 검색 목록 |
| countries | table | 0 | 국가별 taxa 수 |

### ui_queries (14건)

app.py의 하드코딩된 SQL을 Named Query로 등록하여, 외부 SCODA 뷰어도 동일한 쿼리를 실행 가능.

| name | description | params |
|------|-------------|--------|
| taxonomy_tree | Class~Family 계층 트리 | 없음 |
| family_genera | Family별 Genus 목록 | family_id |
| genus_detail | Genus 상세정보 | genus_id |
| rank_detail | Rank 상세정보 | rank_id |
| genera_list | 전체 Genus 평면 목록 | 없음 |
| valid_genera_list | 유효 Genus만 | 없음 |
| genus_synonyms | Genus의 동의어 | genus_id |
| genus_formations | Genus의 지층 | genus_id |
| genus_locations | Genus의 산지 | genus_id |
| bibliography_list | 참고문헌 목록 | 없음 |
| formations_list | 지층 목록 | 없음 |
| countries_list | 국가 목록 | 없음 |
| genera_by_country | 국가별 Genus | country_name |
| genera_by_period | 시대별 Genus | temporal_code |

쿼리 파라미터는 `:param_name` 형식 (SQLite named parameter).

## 새 API 엔드포인트 (3개)

- `GET /api/display-intent` — Display Intent 목록
- `GET /api/queries` — 등록된 쿼리 목록 (SQL 제외, 이름/설명/파라미터)
- `GET /api/queries/<name>/execute` — Named Query 실행
  - 쿼리 파라미터를 URL query string으로 전달: `?family_id=10`
  - 응답: `{query, columns, row_count, rows}`

## 파일 변경

| 파일 | 변경 |
|------|------|
| `scripts/add_scoda_ui_tables.py` | **신규** — Phase 14 마이그레이션 스크립트 |
| `app.py` | 수정 — 3개 엔드포인트 추가, `request` import 추가 |
| `test_app.py` | 수정 — UI 테이블 fixture + 16개 테스트 추가 |
| `trilobase.db` | 수정 — 2개 테이블 추가 |
| `CLAUDE.md` | 수정 — Phase 완료 시 필수 작업 규칙 추가 |

## 테스트

- 기존 47개 + 신규 16개 = **63개 전체 통과**
- TestApiDisplayIntent (6개): 목록, primary/secondary view, source_query, 구조 검증
- TestApiQueries (4개): 목록, 구조, 정렬 검증
- TestApiQueryExecute (6개): 파라미터 없는 실행, 파라미터 있는 실행, 정렬, 404, 컬럼, row 구조

## schema_descriptions 추가

ui_display_intent, ui_queries 테이블의 컬럼 설명 12건 추가 (총 102건).
