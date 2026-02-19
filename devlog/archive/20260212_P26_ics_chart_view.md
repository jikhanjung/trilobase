# Phase 30 계획: ICS Chronostratigraphic Chart 뷰

**작성일:** 2026-02-12

## 목표

Chronostratigraphy 탭을 평범한 플랫 테이블에서 ICS 공식 차트 스타일의 계층형 색상 코딩 테이블로 변경.

## 변경 사항

### 데이터

- `ics_chronostrat_list` 쿼리에 `parent_id` 컬럼 추가
- 매니페스트 `chronostratigraphy_table` type: `"table"` → `"chart"`

### 렌더링 알고리즘

1. fetch → 트리 빌드 (Super-Eon 자식을 루트로 승격)
2. DFS로 leaf count 계산 (= rowspan)
3. leaf 행 수집 (각 행 = root→leaf 경로)
4. 7컬럼 테이블: Eon | Era | Period | Sub-Period | Epoch | Age | Age(Ma)

### 특수 처리

- **Precambrian (Super-Eon)**: 자식을 루트로 승격
- **Carboniferous Sub-Period**: colspan 분리 (Pennsylvanian/Mississippian)
- **Pridoli**: parent-child 컬럼 gap 감지 → 자식 col을 부모 끝 다음으로 조정, colspan 확장
- **Hadean**: leaf 노드로서 전체 컬럼 span

### 수정 파일

1. `trilobase.db` — 쿼리 + 매니페스트 수정
2. `templates/index.html` — chart 컨테이너 추가
3. `static/js/app.js` — chart 렌더링 로직
4. `static/css/style.css` — chart 스타일
5. `test_app.py` — 테스트 업데이트
