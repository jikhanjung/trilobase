# 20260316-130: TSF 대규모 추출 — Coelenterata, Bryozoa, Porifera, Mollusca, Hexapoda, Bivalvia, Echinodermata

## 작업 개요

이전 세션(20260315_126)에서 시작된 TSF 소스 파일 확장 작업을 이어받아, `data/pdf/`에 있는 미처리 Treatise PDF를 대부분 처리하였다. 이번 세션에서 새로 생성한 소스 파일은 총 **14개**, 추가된 속(genus) 항목은 약 **10,000개** 이상이다.

## 생성된 소스 파일 목록

| 파일명 | 페이지 범위 | 속 수 | 비고 |
|--------|-------------|------:|------|
| `treatise_archaeocyatha_revised_1972.txt` | 79–188 | ~775 | 1972 개정판. 단어별 줄바꿈 → 전체 텍스트 병합 방식 적용 |
| `treatise_porifera_revised_2003_vol2.txt` | 41–100 | ~69 | 분류 체계만 (속 기재 없음) |
| `treatise_porifera_revised_2004_vol3.txt` | 41–904 | ~1,243 | 표준 추출기 적용 |
| `treatise_porifera_revised_2015_vol4.txt` | 262–470 | ~354 | Title Case 저자 → 커스텀 정규식 적용 |
| `treatise_porifera_revised_2015_vol5.txt` | 293–760 | ~303 | 동상 (Stromatoporoidea) |
| `treatise_mollusca_scaphopoda_1989.txt` | 60–374 | ~799 | Scaphopoda·Amphineura·Monoplacophora·Gastropoda |
| `treatise_hexapoda_1992.txt` | 25–524 | ~2,817 | Class Insecta 전체. 표준 추출기 |
| `treatise_bivalvia_1969_vol1.txt` | 263–527 | ~645 | Palaeotaxodonta·Cryptodonta·Pteriomorphia·Palaeoheterodonta |
| `treatise_bivalvia_1969_vol2.txt` | 4–380 | ~1,074 | Heterodonta·Anomalodesmata |
| `treatise_bivalvia_1971_vol3.txt` | 149–264 | ~63 | Ostreina(굴류) 전담 |
| `treatise_bryozoa_revised_1983.txt` | 384–634 | ~136 | Cystoporata·Cryptostomata. "AUTHOR in AUTHOR" 형식 처리 |
| `treatise_echinodermata_1967_vol_s.txt` | 198–655 | ~235 | Part S: Cystoidea·Blastoidea·Eocrinoidea 등 |
| `treatise_echinodermata_2011_vol_t.txt` | 53–265 | ~125 | Part T Rev.: Crinoidea Articulata. Title Case 저자 |
| `treatise_echinodermata_1966_vol_u1.txt` | 69–396 | ~818 | Part U vol1: Asterozoa + Echinoidea partial |
| `treatise_echinodermata_1966_vol_u2.txt` | 9–308 | ~562 | Part U vol2: Euechinoidea + Holothuroidea |

이전 세션에서 생성(이번 세션에서 YAML front matter 추가):
- `treatise_hexapoda_1992.txt` — 추출은 이전 세션 완료, front matter만 추가

## 기술적 이슈 및 해결

### 1. Porifera 2015 (vol4/5) — Title Case 저자
2015년 판은 저자명이 `Neumayr, 1890` 형식(Title Case)으로 표기됨. 표준 `GENUS_START` 정규식(`[A-Z][A-Z\s&.,\'-]+?`)이 매칭 실패. `/tmp/extract_vol45.py`에서 `[A-Z][a-z&\s.,\'-]+?` 패턴으로 수정하여 해결.

### 2. Archaeocyatha 1972 — 스캔 OCR 단어별 줄바꿈
PDF 너비 434px (단일 컬럼). 각 단어가 별도 줄에 OCR되어 2컬럼 클리핑으로는 160줄만 추출됨. `/tmp/extract_archeo2.py`에서 페이지 텍스트를 전체 병합 후 정규식 검색으로 전환 → 587속 추출.

### 3. Bryozoa Revised 1983 — "AUTHOR in AUTHOR" 형식
`HALL in SILLIMAN, SILLIMAN, & DANA, 1851` 형식 15건이 표준 정규식에서 누락. `/tmp/extract_bryozoa_1983.py`에서 `in\s+[A-Z]...` 패턴을 포함한 확장 정규식 추가.

### 4. T_1978 (Crinoidea vol1) — 속 기재 없음
439페이지 전체가 형태·계통·생태 개요. Systematic Descriptions는 미보유 Vol 2/3에 수록. TSF 생성 불가로 처리, 상태 파일에 ⚠️ 표시.

### 5. 커스텀 스크립트 패턴 정리
Volume별 추출 방식:
- **ALL CAPS 저자 (1950–1970년대)**: `extract_pages.py` 표준 추출기
- **Title Case 저자 (2011, 2015년)**: 커스텀 스크립트 (`/tmp/extract_*.py`)
- **스캔 OCR (1972년 이전)**: 텍스트 전체 병합 후 정규식 검색

## PDF_SOURCE_STATUS.md 업데이트

`data/PDF_SOURCE_STATUS.md`를 전면 개정:
- 파일명 오류 수정 (Echinodermata PDF 파일명 실제값 반영)
- 신규 항목 14건 추가
- 요약 수치 갱신: PDF 보유 30건, TSF 생성 28건, 미착수 14건
- T_1978 ⚠️ 메모 추가

## 현재 미처리 PDF

| PDF | 이유 |
|-----|------|
| `Treatise_T_Echinodermata_1978.pdf` | 형태 개요 전담, 속 기재 없음 |

## 다음 단계 (선택)

- 생성된 소스 파일들을 각 DB(coelenteratabase, bivalviabase 등)로 빌드
- 또는 paleobase 통합 패키지(P88 계획) 구현 시 모든 소스를 통합 활용
