# Brachiobase v0.2.2: Temporal Code 추출 + Timeline 기능

**Date**: 2026-03-14

## 목표

Brachiobase에 trilobase와 동일한 geologic/pubyear 타임라인 기능 적용. 이를 위해 누락된 temporal_code 데이터를 PDF에서 추출.

## 변경 사항

### 1. Temporal Code 추출 (treatise_brachiopoda_2000_vol2.txt)

이 파일만 704개 genus 전체에 temporal_code가 없었음. PyMuPDF로 PDF 텍스트를 프로그래밍 방식으로 추출:

- PDF에서 genus 설명 텍스트 내 이탤릭 temporal range를 정규식으로 파싱
- "Upper Devonian–Permian" 같은 텍스트를 `UDEV-PERM` 코드로 변환
- **695/712 genus 추출 성공, 695 전부 코드 변환**, 17개 PDF 텍스트 매칭 실패

| 파일 | Genera | 추출됨 | 누락 |
|------|--------|--------|------|
| 1965 vol1 | 610 | 610 | 0 |
| 1965 vol2 | 230 | 230 | 0 |
| 2000 vol2 | 704 | 687 | 17 |
| 2000 vol3 | 926 | 926 | 0 |
| 2002 vol4 | 1,043 | 1,038 | 5 |
| 2006 vol5 | 1,198 | 1,182 | 16 |

DB 기준: 3,960/4,664 genus (84.9%)에 temporal_code. 704개 미보유는 대부분 synonym/placeholder taxa (assertion 없는 666개 + PLACED_IN 있는 38개).

### 2. 빌드 스크립트 수정 (`build_brachiobase_db.py`)

- `parse_hierarchy_body()`: `|` 뒤 location/temporal_code 파싱 추가 (기존에는 버리고 있었음)
- `process_source()`: temporal_code, location을 taxon에 UPDATE
- `temporal_code_mya` 테이블 생성: PaleoCore 27 + compound codes 자동 추가 → 101건
- Timeline 쿼리 6개 추가: `timeline_geologic_periods`, `timeline_publication_years`, `taxonomy_tree_by_geologic`, `tree_edges_by_geologic`, `taxonomy_tree_by_pubyear`, `tree_edges_by_pubyear`
- Timeline compound view 매니페스트 추가
- VERSION: 0.2.1 → **0.2.2**
- `from db_path import find_paleocore_db` 추가

### 3. Geologic 축 범위

Brachiopoda는 Cambrian~Recent까지 분포하므로, trilobase(LCAM~End Permian)보다 넓은 축:
- LCAM(538.8) ~ HOL(0.0117) + Recent(0.0)

## 빌드 결과

- DB: `brachiobase-0.2.2.db`
- .scoda: `brachiobase-0.2.2.scoda` (0.4 MB)
- temporal_code_mya: 101 mappings
- Profile 1 (Treatise 1965): 1,223 edges
- Profile 2 (Treatise Revised 2000-2006): 4,903 edges

## 수정 파일

- `data/sources/treatise_brachiopoda_2000_vol2.txt` — 687 genus에 temporal code 추가
- `scripts/build_brachiobase_db.py` — temporal_code 파싱 + temporal_code_mya + timeline 쿼리/매니페스트
- `db/brachiobase-0.2.2.db` — 신규
- `dist/brachiobase-0.2.2.scoda` — 신규
