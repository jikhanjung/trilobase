# 118: Canonical Source Data 파일 생성 (R04 확장 형식)

**Date:** 2026-03-11

## 변경 사항

### 1. 변환 스크립트 (scripts/convert_to_source_format.py, NEW)

기존 데이터 파일들로부터 R04 확장 형식의 canonical source data 파일을 생성하는 스크립트.

4개 문헌 × 5개 파일 변환:
- `data/treatise_1959_taxonomy.txt` → `data/sources/treatise_1959.txt`
- `data/treatise_ch4_taxonomy.json` → `data/sources/treatise_2004_ch4.txt`
- `data/treatise_ch5_taxonomy.json` → `data/sources/treatise_2004_ch5.txt`
- `data/adrain2011.txt` → `data/sources/adrain_2011.txt`
- `data/trilobite_genus_list.txt` → `data/sources/jell_adrain_2002.txt`

### 2. JA2002 파서

- 5,115개 속(genus) 100% 파싱 (unparsed 0건)
- Authority regex: 대소문자 혼합(de/van/von), 다중 저자(&), 연도 접미사(a/b) 처리
- 214개 Family로 그룹화, 744개 synonym line, 7개 spelling line 추출
- Synonym 유형: j.s.s., j.o.s., preocc., suppressed, replacement, misspelling 등

### 3. `nov.` → 출판 연도 대체 (context-aware)

각 문헌의 `nov.` (신설 분류군)를 해당 문헌의 출판 연도로 대체:

| 문헌 | `nov.` 대체 연도 | 예시 |
|------|-----------------|------|
| Treatise 1959 | 1959 | `Poulsen, nov.` → `Poulsen, 1959` |
| Adrain 2011 | 2011 | `Aulacopleurida nov.` → `Aulacopleurida, 2011` |
| JA2002 | 2002 | `JELL, nov.` → `JELL, 2002` |

`parse_genus_entry()`의 `pub_year` 파라미터로 일반화.

### 4. 생성된 소스 파일 (data/sources/, NEW)

| 파일 | 행수 | scope |
|------|------|-------|
| treatise_1959.txt | 1,790 | Trilobita, comprehensive |
| treatise_2004_ch4.txt | 205 | Agnostida, comprehensive |
| treatise_2004_ch5.txt | 233 | Redlichiida, comprehensive |
| adrain_2011.txt | 210 | Trilobita, comprehensive (suprafamilial) |
| jell_adrain_2002.txt | 6,351 | Trilobita, comprehensive |

각 파일은 YAML 헤더(reference + scope) + 계층 본문 구조.

## 관련

- `devlog/20260311_R04_taxonomy_input_format.md` — 확장 형식 설계 문서
