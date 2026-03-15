# 20260315_126 — TSF 소스 파일 대규모 확장 + pdf-to-taxonomy 스킬 개선

## 작업 내용

### 1. treatise_ammonoidea_1957.txt 완성

Arkell et al. (1957) Treatise on Invertebrate Paleontology Part L, Ammonoidea 전체 체계적 고생물학 섹션 추출 완료.

- **범위**: L1–L437 (vol1 + vol2 전체)
- **규모**: 2,632줄
- **커버리지**:
  - Paleozoic Ammonoidea (Devonian–Permian): Anarcestida, Clymeniida, Goniatitida, Prolecanitida, Ceratitida
  - Mesozoic Ammonoidea (Triassic–Cretaceous): Phylloceratida, Lytoceratida, Ammonitina (전체 수십 개 family/subfamily)
  - 마지막 패밀리: Sphenodiscidae (Maastrichtian)
  - Aptychi 섹션(L438–L490)은 분류학 외 내용으로 제외

**처리 방식**: PDF vision mode (이미지 직접 판독), 세션 다수에 걸쳐 페이지 단위 순차 처리

---

### 2. 신규 TSF 소스 파일 5종 추가

| 파일 | 내용 | 줄수 |
|------|------|------|
| `treatise_ammonoidea_1996.txt` | Wright et al. 1996, Cretaceous Ammonoidea (Part L Revised) | 1,205 |
| `treatise_bryozoa_1953.txt` | Bassler 1953, Bryozoa (Part G) | 1,032 |
| `treatise_cephalopoda_1964.txt` | Part K Cephalopoda 1964 | 603 |
| `treatise_coelenterata_1956.txt` | Coelenterata 1956 Treatise | 836 |
| `treatise_mollusca_1960.txt` | Mollusca 1960 Treatise | 860 |
| `treatise_archaeocyatha_porifera_1955.txt` | Part E Archaeocyatha & Porifera 1955 | 899 |

이 파일들은 자동 추출 스크립트(`scripts/pdf_to_tsf/`) 또는 별도 세션에서 생성됨.

---

### 3. pdf-to-taxonomy 스킬 개선

**변경 전**: 페이지 단위 순차 처리 (`/pdf-to-taxonomy <pdf> <page_number>`)
**변경 후**: 배치 처리 + 자동 감지 지원 (`/pdf-to-taxonomy <pdf> [<start>-<end>]`)

주요 변경:
- `argument-hint` 업데이트
- 페이지 범위 미지정 시 PDF 스캔으로 체계적 고생물학 섹션 자동 감지
- `.claude/commands/pdf-to-taxonomy.md` 삭제 (skills 디렉토리로 통합)

---

### 4. TSF 명세 문서 추가

`docs/Taxonomic Source Format Specification v0.1.md` (338줄)
- TSF 포맷의 공식 명세 문서
- YAML 프론트매터, 계층 구조, 시간 코드, 동의어 표기법 등 정의

---

### 5. pdf_to_tsf 스크립트 추가

`scripts/pdf_to_tsf/` 디렉토리:
- `treatise_extractor.py` — 핵심 추출 엔진 (2단 컬럼 처리, 시간 코드 매핑)
- `run_cephalopoda.py` — Part K Cephalopoda 전용 실행 스크립트
- `run_mollusca.py` — Mollusca 전용 실행 스크립트
- `extract_pages.py` — 페이지 범위 추출 유틸리티

---

### 6. CLAUDE.md 소폭 수정

`data/sources/` 디렉토리 설명을 "assertion DB 빌드 소스" → "taxonomic source files"로 갱신 (범용 소스 파일로 확장 반영)

---

## 현재 data/sources/ 현황 (전체)

```
adrain_2011.txt
jell_adrain_2002.txt
treatise_1959.txt
treatise_2004_ch4.txt
treatise_2004_ch5.txt
treatise_ammonoidea_1957.txt       ← 이번 완성 (2,632줄)
treatise_ammonoidea_1996.txt       ← 신규
treatise_archaeocyatha_porifera_1955.txt  ← 신규
treatise_brachiopoda_1965_vol1.txt
treatise_brachiopoda_1965_vol2.txt
treatise_brachiopoda_2000_vol2.txt
treatise_brachiopoda_2000_vol3.txt
treatise_brachiopoda_2002_vol4.txt
treatise_brachiopoda_2006_vol5.txt
treatise_bryozoa_1953.txt          ← 신규
treatise_cephalopoda_1964.txt      ← 신규
treatise_chelicerata_1955.txt
treatise_coelenterata_1956.txt     ← 신규
treatise_graptolite_1955.txt
treatise_graptolite_1970.txt
treatise_graptolite_2023.txt
treatise_mollusca_1960.txt         ← 신규
treatise_ostracoda_1961.txt
```

총 23개 소스 파일.
