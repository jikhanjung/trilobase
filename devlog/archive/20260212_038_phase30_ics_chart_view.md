# Phase 30: ICS Chronostratigraphic Chart 뷰 구현

**완료일:** 2026-02-12

## 목표

Chronostratigraphy 탭을 ICS 공식 차트 스타일의 계층형 색상 코딩 테이블로 변경.

## 변경 사항

### DB (trilobase.db)

- `ics_chronostrat_list` 쿼리에 `parent_id` 컬럼 추가
- 매니페스트 `chronostratigraphy_table` type: `"table"` → `"chart"`

### Frontend

- `templates/index.html`: `view-chart` 컨테이너 추가
- `static/js/app.js`:
  - `switchToView()`: `view.type === 'chart'` 분기 추가
  - `renderChronostratChart()`: fetch → tree build → DFS → HTML 렌더
  - `buildChartTree()`: 트리 구축, Super-Eon 자식 루트 승격
  - `computeLeafCount()`: leaf 수 계산 (= rowspan)
  - `collectLeafRows()`: DFS leaf 행 수집, parent-child gap 보정
  - `isLightColor()`: 배경색 밝기 기반 텍스트 색상 결정
  - `renderChartHTML()`: 7컬럼 HTML 테이블 생성
- `static/css/style.css`: `.chart-view-*`, `.ics-chart` 스타일 추가

### 7컬럼 레이아웃

| Col 0 | Col 1 | Col 2 | Col 3 | Col 4 | Col 5 | Col 6 |
|-------|-------|-------|-------|-------|-------|-------|
| Eon | Era | System/Period | Sub-Period | Series/Epoch | Stage/Age | Age(Ma) |

### 특수 처리

- **Precambrian (Super-Eon)**: 자식(Hadean, Archean, Proterozoic) 루트 승격
- **Carboniferous**: Sub-Period 컬럼 사용 (Pennsylvanian/Mississippian)
- **Pridoli**: parent-child 컬럼 gap 감지 → col 4에 배치, colspan=2
- **Hadean**: leaf → colspan=6 (전체 데이터 컬럼 span)

## 테스트

- `test_app.py`: 147개 (기존 145 + 신규 2)
  - `test_chronostrat_query_includes_parent_id`: parent_id 컬럼 포함 확인
  - `test_manifest_chart_type`: chronostratigraphy_table type "chart" 확인
- 전체 통과

## 검증 포인트

1. Chronostratigraphy 탭 → ICS 스타일 차트 (117행 중첩 테이블)
2. 각 셀 ICS 지정 색상 배경 + 밝기 기반 텍스트 색상
3. Phanerozoic: 5단계 중첩 + Carboniferous Sub-Period 분리
4. Pridoli: Epoch 컬럼에 배치, colspan으로 Age까지 확장
5. Hadean: Eon 셀이 전체 컬럼 span
6. 셀 클릭 → detail 모달
