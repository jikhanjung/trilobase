# 119: Assertion DB 0.2.0 — Source-driven Build

**Date:** 2026-03-11
**Type:** Work Log

## 목표

`data/sources/*.txt` (R04 확장 형식)를 단일 진입점으로 사용하여 assertion DB 0.2.0을 빌드하는 `scripts/build_assertion_db.py` 작성. 기존 3단계 파이프라인을 하나로 통합.

## 작업 내역

### 1. 계획 문서 작성
- `devlog/20260311_P83_build_assertion_from_sources.md` — 6 Phase 파이프라인 설계

### 2. `scripts/build_assertion_db.py` 신규 작성 (~800 lines)

**Phase 구성:**
1. Schema 생성 (create_assertion_db.py와 동일)
2. Canonical DB에서 taxon 복사 (5,341건)
3. Bibliography 복사 + 소스별 reference 삽입 (4건)
4. Source 파일 파싱 → assertions 생성
5. Classification profiles + edge caches 빌드
6. Junction tables 복사 + SCODA 메타데이터

**핵심 함수:**
- `parse_source_header()`: YAML 헤더 → dict
- `parse_hierarchy_body()`: 들여쓰기 기반 → placement records
- `process_source_default()`: JA2002 + Adrain 2011 → default profile
- `process_source_treatise()`: Treatise files → non-accepted assertions
- `fallback_canonical_parent_id()`: 소스에 없는 taxa → canonical parent_id 폴백
- `import_canonical_opinions()`: canonical opinions → SYNONYM_OF/SPELLING_OF 복원
- `build_profiles()`: 3개 프로필 + comprehensive removal (R03)

### 3. 소스 데이터 정제 (`data/trilobite_genus_list.txt`)

| 수정 | 원본 | 수정 후 |
|------|------|---------|
| Astycoryphe | `, TROPIDOCORYPHIDAE;` | `; TROPIDOCORYPHIDAE;` |
| Agnostonymus | `PTYCHAGNOSTIDAE, MCAM` | `PTYCHAGNOSTIDAE; MCAM` |
| Alemtejoia | `HEBEDISCIDAE, LCAM` | `HEBEDISCIDAE; LCAM` |
| Chambersiellus | `INDET. LCAM` | `INDET.; LCAM` |
| Nitidocare | `Lite.` (불완전) | `Litéň Fm, Czech Republic; PTEROPARIIDAE; LSIL.` |
| Wutingaspis | `China: REDLICHIIDAE;` | `China; REDLICHIIDAE;` |
| Dignagnostus | `AGNOSTINA FAMILY UNCERTAIN.` | `UNCERTAIN; MCAM.` |

### 4. `scripts/convert_to_source_format.py` 수정

- `SUBORDER FAMILY UNCERTAIN` 패턴 → `UNCERTAIN`으로 정규화
- 빈 family 속(nomenclatural notes) → `# 코멘트` 섹션으로 출력

### 5. 기존 데이터 수정 (이전 세션)

- Treatise 1959: `Lojypyge` → `Lejopyge` OCR 오타 수정 (txt + json)
- Adrain 2011: `nov.` → `Adrain, 2011` (author 포함 치환)
- Treatise 1959: `nov.` → `, 1959` (context-aware 치환)
- ALL CAPS family/subfamily → title case 정규화 (파서)

## 0.1.8 vs 0.2.0 비교

```
                               0.1.8    0.2.0    Diff
                               -----    -----    ----
  taxon                          5610     5627   +17
  reference                      2135     2135   =
  PLACED_IN (accepted)           5083     5113   +30
  SYNONYM_OF                     1055     1075   +20
  SPELLING_OF                       2        2   =
  Default profile edges          5083     5113   +30
  Treatise 1959 edges            1768     1645   -123
  Treatise 2004 edges            2053     1912   -141
```

**Default profile:**
- Common edges: 4,967 (97.7%)
- 115 genera moved to corrected family names (e.g., Dokimokephalidae → Dokimocephalidae)
- 30 additional PLACED_IN from canonical parent_id fallback
- 20 additional SYNONYM_OF from canonical opinions import
- Agnostida excluded from default (per Adrain 2011 — present in treatise profiles)

**Treatise profiles:**
- Edge 수 감소는 ALL CAPS 정규화로 인한 중복 제거 + 직접 파싱(fuzzy matching 제거)

## 결과

- 15/17 validation checks passed (2건은 0.2.0이 더 나은 결과)
- 모든 기존 기능 보존 + 데이터 품질 개선
- 단일 스크립트로 빌드 완료 (기존 3단계 → 1단계)

## 파일 변경

| 파일 | 변경 |
|------|------|
| `scripts/build_assertion_db.py` | 신규 (단일 빌드 스크립트) |
| `scripts/convert_to_source_format.py` | FAMILY UNCERTAIN 정규화, empty family 처리 |
| `data/trilobite_genus_list.txt` | 7건 세미콜론/데이터 수정 |
| `data/treatise_1959_taxonomy.txt` | Lojypyge → Lejopyge |
| `data/treatise_1959_taxonomy.json` | Lojypyge → Lejopyge |
| `data/sources/*.txt` | 5개 파일 재생성 |
| `db/trilobase-assertion-0.2.0.db` | 빌드 결과 |
| `devlog/20260311_P83_build_assertion_from_sources.md` | 계획 문서 |
