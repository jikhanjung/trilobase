# parent_id NULL Family 25건 → Order Uncertain 이동

**날짜:** 2026-02-21

## 작업 내용

`taxonomic_ranks` 테이블에서 `parent_id`가 NULL인 Family 25건을 "Order Uncertain" (id=144) 하위로 이동.

## 배경

- Phase 7(Order 통합) 시 기존 order에 배정된 family만 연결되었고, order 배정이 없는 family 25건은 `parent_id = NULL`로 남아 있었음
- 트리 구조에서 루트 직속 자식(Class와 동급)으로 표시되는 문제
- "Order Uncertain" 노드(id=144, rank=Order)에 배정하여 계층 구조 내에 위치시킴

## 이동된 Family 목록 (25건, 총 434 genera)

| ID | Family | Genus 수 | 비고 |
|----|--------|----------|------|
| 201 | Agnostidae | 33 | Agnostida 후보 |
| 202 | Ammagnostidae | 13 | Agnostida 후보 |
| 203 | Bohemillidae | 2 | |
| 204 | Burlingiidae | 2 | |
| 205 | Chengkouaspidae | 11 | |
| 206 | Clavagnostidae | 11 | Agnostida 후보 |
| 207 | Condylopygidae | 3 | Agnostida 후보 |
| 208 | Conokephalinidae | 13 | |
| 209 | Diplagnostidae | 33 | Agnostida 후보 |
| 210 | Dokimocephalidae | 46 | |
| 211 | Doryagnostidae | 3 | Agnostida 후보 |
| 212 | Glyptagnostidae | 3 | Agnostida 후보 |
| 213 | Metagnostidae | 23 | Agnostida 후보 |
| 214 | Ordosiidae | 12 | |
| 215 | Pagodiidae | 19 | |
| 216 | Peronopsidae | 21 | Agnostida 후보 |
| 217 | Pilekiidae | 17 | |
| 218 | Ptychagnostidae | 20 | Agnostida 후보 |
| 219 | Saukiidae | 32 | |
| 220 | Toernquistiidae | 4 | |
| 221 | Linguaproetidae | 1 | |
| 222 | Scutelluidae | 1 | |
| 223 | INDET | 29 | 특수: 미확정 family |
| 224 | UNCERTAIN | 74 | 특수: family 미확정 속 컨테이너 |
| 225 | NEKTASPIDA | 8 | 특수: Trilobita 외 택사 가능성 |

## 참고: Agnostida 관련

Agnostidae, Ammagnostidae, Clavagnostidae, Condylopygidae, Diplagnostidae, Doryagnostidae, Glyptagnostidae, Metagnostidae, Peronopsidae, Ptychagnostidae (10개 family)는 Agnostida 목에 속할 가능성이 높으나, Jell & Adrain (2002) 원문에서 order 배정이 명시되지 않아 Order Uncertain에 임시 배치. 향후 T-1(Uncertain Family Opinions 확장) 작업에서 문헌 기반 opinion으로 처리 예정.

## 결과

- parent_id NULL Family: 25 → **0건** (모두 해소)
- Order Uncertain 하위 Family: 56 → **81건** (+25)
