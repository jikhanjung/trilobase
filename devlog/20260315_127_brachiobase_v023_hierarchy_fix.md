# 20260315_127 — Brachiobase v0.2.3: 계층 구조 수정 + classification reference 추가

## 작업 배경

brachiobase Profile 2 (Revised 2000-2006)에서 일부 Order들이 올바른 Class 아래가 아니라
Phylum BRACHIOPODA 에 직접 붙는 문제가 보고됨.

원인: `build_brachiobase_db.py`의 `parse_hierarchy_body()`는 파일별로 독립적으로
스택을 리셋한다. vol2(2000)는 Phylum→Subphylum→Class 순서로 시작하므로 정상이지만,
vol3~vol5는 중간 계층(Order 또는 Suborder)부터 시작하여 스택이 비어 있어
`parent_name = None` → 고아 노드 → "bridge edges to Phylum BRACHIOPODA" 처리됨.

- **vol3**: `Suborder PRODUCTIDINA` 로 시작 (Order/Class 없음)
- **vol4**: `Order PENTAMERIDA` 로 시작 (Class 없음)
- **vol5**: `Order SPIRIFERIDA` 로 시작 (Class 없음)

## 해결 방법

### 1. Suprafamilial classification 레퍼런스 파일 생성

Treatise Brachiopoda Revised 2000 vol.2, pp.22-27의 "Outline of Suprafamilial
Classification and Authorship" 섹션을 추출하여 TSF-compatible reference 파일 작성:

**`data/sources/brachiopoda_classification.txt`**

구조:
- Phylum Brachiopoda
  - Subphylum Linguliformea (Class Lingulata, Paterinata)
  - Subphylum Craniiformea (Class Craniata)
  - Subphylum Rhynchonelliformea (Class Chileata, Obolellata, Kutorginata,
    Strophomenata, Rhynchonellata)
- 25 Orders, 33 Suborders, 158 Superfamilies 전체 계층 포함

### 2. `load_classification_edges()` 함수 추가

`brachiopoda_classification.txt`를 pre-pass로 처리하여 Phylum→Subphylum→Class→Order
전체 구조의 edge를 생성하는 함수 추가 (`build_brachiobase_db.py:412-456`).

### 3. Profile 2 처리 시 pre-pass 실행

source file 루프 전에 classification prepass를 실행하여 167개 structural edge를
미리 생성. 이후 vol3~vol5 source file이 Order로 시작해도 이미 해당 Order→Class
edge가 존재하여 고아가 되지 않음.

### 4. ALL_CAPS 이름 정규화 범위 확장

기존: `Family`, `Subfamily`, `Superfamily`, `Suborder` 만 정규화
수정: 모든 rank에 대해 정규화 (`name == name.upper()` → titlecase)

Source file의 `PENTAMERIDA`, `ORTHIDA` 등이 classification file의 `Pentamerida`,
`Orthida` 와 같은 taxon으로 resolve되도록 수정.

## 결과

### 계층 구조 확인 (Profile 2)

| 분류군 | 이전 | 이후 |
|--------|------|------|
| Order Spiriferida | → Phylum BRACHIOPODA | → Class Rhynchonellata → Subphylum Rhynchonelliformea |
| Order Pentamerida | → Phylum BRACHIOPODA | → Class Rhynchonellata → Subphylum Rhynchonelliformea |
| Order Orthida | → Phylum BRACHIOPODA | → Class Rhynchonellata → Subphylum Rhynchonelliformea |
| Order Atrypida | → Phylum BRACHIOPODA | → Class Rhynchonellata → Subphylum Rhynchonelliformea |
| Order Athyridida | → Phylum BRACHIOPODA | → Class Rhynchonellata → Subphylum Rhynchonelliformea |
| Suborder Productidina | → Phylum BRACHIOPODA | → Order Productida → Class Strophomenata |

Profile 2 bridge edges: **25개 → 0개**

### 빌드 통계 (v0.2.3)

| 항목 | 수량 |
|------|------|
| Phylum | 1 |
| Subphylum | 3 |
| Class | 10 |
| Order | 28 |
| Suborder | 33 |
| Superfamily | 158 |
| Family | 429 |
| Subfamily | 511 |
| Genus | 4,664 |
| 총 taxa | 5,837 |
| Profile 1 edges | 1,223 |
| Profile 2 edges | 4,918 |

## 변경 파일

- `data/sources/brachiopoda_classification.txt` — 신규: suprafamilial classification reference
- `scripts/build_brachiobase_db.py` — `load_classification_edges()` 추가, prepass 로직, 정규화 수정, VERSION→0.2.3
- `db/brachiobase-0.2.3.db` — 신규 DB
- `dist/brachiobase-0.2.3.scoda` — 신규 패키지 (399KB, 19,238 records)

## 참고

- PDF_SOURCE_STATUS.md: KU 아카이브 43개 권호 기준으로 전면 재구성 (data/pdf/ gitignore로 커밋 불가)
- Profile 1 (1965)는 INARTICULATA/ARTICULATA 등 6개가 여전히 Brachiopoda에 직접 붙음 —
  1965 classification이 2000 revised와 다르므로 별도 처리 필요 (추후 과제)
