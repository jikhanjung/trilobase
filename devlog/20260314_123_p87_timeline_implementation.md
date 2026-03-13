# 123 — P87 Timeline 기능 구현 (trilobase 패키지)

**날짜**: 2026-03-14
**관련**: P87, scoda-engine P28
**버전**: trilobase 0.3.0 → 0.3.1

## 작업 내용

scoda-engine의 `tree_chart_timeline` 서브뷰를 trilobase `.scoda` 패키지에서 활성화.

### 1. ui_queries 추가 (5개 → 7개)

| 쿼리 | 용도 |
|------|------|
| `timeline_geologic_periods` | 지질시대 축 (start_mya IS NOT NULL, INDET 제외) |
| `timeline_publication_years` | 출판 연도 축 (reference × assertion JOIN) |
| `taxonomy_tree_by_geologic` | 지질시대 필터 노드 (누적, profile 연동) |
| `taxonomy_tree_by_pubyear` | 출판 연도 필터 노드 (누적, profile 연동) |
| `tree_edges_by_geologic` | 지질시대 필터 edge |
| `tree_edges_by_pubyear` | 출판 연도 필터 edge |

총 ui_queries: 46 → 52

### 2. ui_manifest 수정

- `timeline` compound view 추가 (sub_view 1개: `tree_chart_timeline`)
- A안 채택: 단일 서브뷰 + `axis_modes` 드롭다운 (geologic / pubyear)
- `source_query_override` + `edge_query_override`로 축 모드별 쿼리 교체

### 3. 버전 업그레이드

- `ASSERTION_VERSION`: 0.3.0 → 0.3.1
- 출력: `db/trilobase-0.3.1.db`, `dist/trilobase-0.3.1.scoda`

## 구현 중 해결한 문제

### display type 문제
`tree_chart_timeline`은 compound view의 sub_view로만 동작함.
처음에 standalone top-level view로 만들었다가 빈 캔버스 — compound view로 변경하여 해결.

### INDET 시대 문제
`temporal_ranges`의 `INDET` 코드는 `start_mya`가 NULL.
축 첫 step이 INDET가 되면 geologic 필터가 아무것도 매치하지 못함.
→ 축 쿼리에 `WHERE start_mya IS NOT NULL` 추가하여 제외.

### d3.stratify "missing" 에러
두 가지 원인:

1. **node 쿼리에서 root 누락**: `classification_edge_cache`에서 Class(Trilobita, id=1) 등은
   `child_id`로는 존재하지 않고 `parent_id`로만 존재. `child_id UNION parent_id`로 수정.

2. **edge/node 불일치**: node는 timeline 필터로 줄어드는데 edge는 전체 profile을 반환하면
   orphan parent 참조 발생. 축 모드별 edge 쿼리를 분리하고 동일 조건 적용.

### edge 쿼리 분리
처음에 `tree_edges_by_timeline` 단일 쿼리였으나, geologic과 pubyear의
필터 조건이 다르므로 `tree_edges_by_geologic` / `tree_edges_by_pubyear`로 분리.

## P87 설계 결정사항 반영

| 질문 | 결정 |
|------|------|
| 5-1 상위 분류군 필터링 | 빈 노드 숨기기, 방법(SQL vs JS)은 실제 결과 보고 결정 |
| 5-2 profile 연동 | 모든 타임라인 쿼리에 profile_id 조건 필수 |
| 5-3 edge 필터 | 쿼리에서 직접 필터 (JS 후처리 아님) |

## 검증

- DB 빌드: 정상 (51 ui_queries)
- validate: 17/17 통과
- 테스트: 117 passing
- 쿼리 직접 실행: orphan 0건 확인
- 브라우저: Timeline 탭 동작 확인

## 남은 작업

- 빈 상위 노드 pruning (5-1) — SQL vs JS 방법 결정 후 구현
- morph 애니메이션 동작 확인 (지질시대 / 출판 연도 양쪽)
- scoda-engine 측 `inst.load()` 초기 호출 최적화 (timeline에서는 불필요한 전체 트리 로드)
