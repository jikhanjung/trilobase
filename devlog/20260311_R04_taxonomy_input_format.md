# R04: Taxonomy 입력 데이터 형식 설계

**Date:** 2026-03-11
**Type:** Review / Design

## 목표

논문에서 추출한 taxonomic assertion을 사람이 정리하여 DB에 입력할 수 있는
**중간 형식(intermediate format)**을 설계한다.

고려 사항:
1. **사람이 정리하기 편할 것** — 논문을 보면서 빠르게 타이핑할 수 있어야 함
2. **파서가 처리하기 명확할 것** — 모호함 없이 assertion으로 변환 가능해야 함
3. **다양한 논문 유형을 수용** — comprehensive treatise, family revision, 단일 속 기재 등
4. **기존 파이프라인과 호환** — Treatise 1959 TXT가 잘 동작하므로 그 장점을 유지

## 현재: Treatise 1959 TXT 형식의 장단점

### 형식

```
Order AGNOSTIDA Kobayashi, 1935
  Suborder AGNOSTINA
    Family AGNOSTIDAE M'Coy, 1849
      Agnostus Brongniart, 1822 [Entomostracites pisiformis]
      ?Rudagnostus Lermontova, 1951
    Family DIPLAGNOSTIDAE Whitehouse, 1936
      Diplagnostus Jaekel, 1909 [Agnostus planicauda Tullberg, 1880]
```

### 장점

- **들여쓰기 + rank 키워드**로 계층이 직관적
- 논문의 분류표를 거의 그대로 옮길 수 있음
- `?` 접두사로 questionable 배치 표현
- `[type species]` 부가 정보를 자연스럽게 포함
- 1,782줄로 1,000+ genera를 표현 — 밀도가 높음

### 한계

- **PLACED_IN만 표현 가능** — synonym, spelling 등 다른 assertion 유형 없음
- **reference 정보 없음** — 파일 전체가 하나의 reference로 암묵 가정
- **scope/coverage 정보 없음** — comprehensive인지 sparse인지 알 수 없음
- **removal 표현 불가** — "이 taxon은 더 이상 여기에 속하지 않음"을 쓸 수 없음
- **메타데이터 헤더 없음** — reference, scope 등을 별도로 관리해야 함

## 제안: 확장된 Taxonomy TXT 형식

기존 TXT 형식의 직관성을 유지하면서, 헤더 블록과 추가 마커로 부족한 부분을 보완한다.

### 전체 구조

```
---
reference: Palmer & Repina, 2004. Treatise on Invertebrate Paleontology, Part O (Revised), Ch.5
scope:
  - taxon: Redlichiida
    coverage: comprehensive
  - taxon: Ptychopariida
    coverage: sparse
---

Order REDLICHIIDA Richter, 1932
  Suborder REDLICHIINA Richter, 1932
    Superfamily REDLICHIOIDEA Poulsen, 1927
      Family REDLICHIIDAE Poulsen, 1927
        Subfamily REDLICHIINAE Poulsen, 1927
          Redlichia Cossman, 1902 [R. noetlingi]
          Gondwanaspis Öpik, 1975
          ?Guanshancephalus Lu & Qian, 1983
        Subfamily PARAREDLICHIINAE Lu, 1950
          ...
      Family NEOREDLICHIIDAE Hupé, 1953 => REDLICHIIDAE
        # 2004에서 Neoredlichiidae를 Redlichiidae의 junior synonym으로 처리
      -Gigantopygus Hupé, 1953
        # Redlichiidae에서 제거됨 (2004에서 미포함)
```

### 헤더 블록 (`---` ... `---`)

YAML 형식의 메타데이터. 파일 맨 앞에 위치.

```yaml
---
reference: 저자, 연도. 제목
  # 또는 기존 DB reference와 매칭할 수 있는 식별 정보

scope:
  - taxon: Redlichiida          # 이 reference가 다루는 subtree root
    coverage: comprehensive     # comprehensive | sparse
  - taxon: Ptychopariida
    coverage: sparse

notes: |
  자유 텍스트 메모. 파서가 무시.
---
```

**scope 블록**은 R03에서 설계한 `reference_scope` 테이블로 직접 매핑된다:

| 헤더 필드 | → DB 테이블 |
|----------|-----------|
| `reference` | `reference` (매칭 또는 신규 생성) |
| `scope[].taxon` | `reference_scope.taxon_id` |
| `scope[].coverage` | `reference_scope.coverage` |

### 계층 본문 (기존 TXT 호환)

기존 형식을 **그대로 유지**하되, 아래 마커를 추가:

#### 기본 PLACED_IN (기존과 동일)

```
Family REDLICHIIDAE Poulsen, 1927
  Redlichia Cossman, 1902 [R. noetlingi]
```
→ `PLACED_IN(Redlichia, REDLICHIIDAE)` assertion 생성

#### `?` — Questionable 배치 (기존과 동일)

```
  ?Guanshancephalus Lu & Qian, 1983
```
→ `PLACED_IN(Guanshancephalus, parent, assertion_status='questionable')`

#### `-` — Removal (제거)

```
  -Gigantopygus Hupé, 1953
```
→ "이전 프로필에서 이 parent 아래에 있었으나, 이 reference에서 제거됨"
→ comprehensive scope에서는 미언급으로도 제거가 추론되지만,
  **명시적 제거**가 필요한 경우 (sparse scope, 또는 의도를 분명히 할 때) 사용.

#### `=>` — Synonym 선언 (Family 이상)

```
Family NEOREDLICHIIDAE Hupé, 1953 => REDLICHIIDAE
```
→ `SYNONYM_OF(Neoredlichiidae, Redlichiidae)`

#### `= ` — Synonym 선언 (Genus)

```
  Kirbyia Reed, 1918 = Encrinurella
```
→ `SYNONYM_OF(Kirbyia, Encrinurella)`

#### `~` — Spelling variant

```
  ~Ptychopyge = Ptychopyge Angelin, 1854
```
→ `SPELLING_OF(Ptychopyge variant, Ptychopyge)`

#### `#` — 주석 (파서 무시)

```
  # 2004에서 Neoredlichiidae를 Redlichiidae의 junior synonym으로 처리
```

#### `[incertae sedis]` — 분류 불확실

```
  Changqingia [incertae sedis]
```
→ `PLACED_IN(Changqingia, parent, assertion_status='incertae_sedis')`

### 마커 요약

| 마커 | 위치 | 의미 | → assertion |
|------|------|------|-------------|
| (없음) | 행 시작 | 정상 배치 | `PLACED_IN` (asserted) |
| `?` | 이름 앞 | 의문시되는 배치 | `PLACED_IN` (questionable) |
| `-` | 이름 앞 | 제거 | removal 기록 |
| `=>` | 이름 뒤 | Family+ synonym | `SYNONYM_OF` |
| `=` | 이름 뒤 | Genus synonym | `SYNONYM_OF` |
| `~` | 이름 앞 | 철자 변이 | `SPELLING_OF` |
| `#` | 행 시작 | 주석 | (무시) |
| `[incertae sedis]` | 이름 뒤 | 분류 불확실 | `PLACED_IN` (incertae_sedis) |

## 파싱 파이프라인

```
taxonomy_input.txt
    │
    ▼
[1] parse_header()     → reference 정보 + scope 목록
    │
    ▼
[2] parse_hierarchy()  → 계층 트리 (기존 parse_treatise_txt.py 확장)
    │                    PLACED_IN + removal + synonym + spelling 추출
    ▼
[3] resolve_taxa()     → DB 기존 taxa와 매칭 (fuzzy match)
    │                    신규 taxa 식별
    ▼
[4] generate_assertions() → assertion 레코드 생성
    │                       reference_scope 레코드 생성
    ▼
[5] preview & confirm  → 사람이 결과 확인 (dry-run 모드)
    │
    ▼
[6] import_to_db()     → assertion DB에 삽입
                         edge cache 재빌드 (comprehensive removal 적용)
```

### Step 5: Preview가 중요

자동 파싱 결과를 사람이 확인하는 단계:

```
$ python scripts/import_taxonomy_txt.py data/palmer_repina_2004.txt --dry-run

Reference: Palmer & Repina, 2004 → matched ref id=2135
Scope: Redlichiida (comprehensive), Ptychopariida (sparse)

Assertions to create:
  PLACED_IN:  224 (asserted 198, questionable 12, incertae_sedis 14)
  SYNONYM_OF: 3
  REMOVAL:    7

New taxa to create:
  [Subfamily] Metaredlichiinae
  [Subfamily] Neoredlichiinae
  [Genus] Pseudopaokannia

Fuzzy matches (confirm):
  "Redlicha" → Redlichia (score=0.95) ✓
  "Guanshancephalus" → (new, no match)

Proceed? [y/N]
```

## 실제 예시: 개별 논문

### 예시 1: Family revision (comprehensive for one Family)

```
---
reference: Chatterton et al., 1999. Revision of Phacopidae
scope:
  - taxon: Phacopidae
    coverage: comprehensive
---

Family PHACOPIDAE Hawle & Corda, 1847
  Subfamily PHACOPINAE Hawle & Corda, 1847
    Phacops Emmrich, 1839 [P. latifrons]
    Eldredgops Struve, 1990 [Phacops rana crassituberculata]
    Viaphacops Maximova, 1972
    -Paciphacops Delo, 1935
      # Phacopinae에서 제거, Eldredgops의 junior synonym으로 처리
    Paciphacops Delo, 1935 = Eldredgops
  Subfamily REEDOPINAE Richter & Richter, 1955
    Reedops Richter & Richter, 1955
    ...
```

### 예시 2: 단일 속 기재 (sparse, targeted)

```
---
reference: Kim & Park, 2023. A new trilobite genus from Korea
scope:
  - taxon: Asaphidae
    coverage: sparse
---

Family ASAPHIDAE Burmeister, 1843
  Koreasaphus Kim & Park, 2023 [K. peninsularis]
    # 신속 기재. Asaphidae 내 정확한 위치는 미확정.
```

### 예시 3: 여러 Family를 혼합 coverage로

```
---
reference: Fortey & Owens, 1997. Evolutionary trends in Proetidae
scope:
  - taxon: Proetidae
    coverage: comprehensive
  - taxon: Aulacopleuridae
    coverage: sparse
notes: |
  Proetidae 전면 재분류. Aulacopleuridae는 비교 목적으로 일부 언급.
---

Family PROETIDAE Salter, 1864
  Subfamily PROETINAE Salter, 1864
    Proetus Steininger, 1831 [P. stokesi]
    Gerastos Goldfuss, 1843
    ...
  Subfamily CORNUPROETINAE Richter & Richter, 1919
    Cornuproetus Richter & Richter, 1919
    ...

Family AULACOPLEURIDAE Angelin, 1854
  Aulacopleurella Ruzicka, 1927
    # sparse scope — 이 Family의 다른 속은 이 논문에서 다루지 않음
```

## Canonical Source Data 아키텍처

확장 형식 파서는 **새 확장 형식만 처리**한다. 기존 헤더 없는 형식과의 호환은 불필요.

각 문헌을 확장 형식의 독립 파일로 작성하면, 이 파일들이 **canonical source data**가 된다.
기존 파이프라인(`parse_treatise_txt.py`, `import_treatise.py`, `import_treatise1959.py` 등)은
확장 형식 파일이 준비되면 폐기 가능하다.

### 소스 파일 구조

```
data/sources/
  treatise_1959.txt          # comprehensive for Trilobita
  treatise_2004_ch4.txt      # comprehensive for Agnostida
  treatise_2004_ch5.txt      # comprehensive for Redlichiida
  jell_adrain_2002.txt       # comprehensive for Trilobita (genus list + synonyms)
  adrain_2011.txt            # comprehensive for Trilobita (suprafamilial hierarchy)
```

### 빌드: 소스 파일들 → assertion DB

```bash
# 모든 소스를 순서대로 처리하여 assertion DB 생성
python scripts/build_assertion_db.py data/sources/*.txt \
  --output db/trilobase-assertion-x.x.x.db
```

파일 순서 = layer 순서. 먼저 처리된 파일이 base, 이후 파일이 override.
comprehensive scope 내의 미언급 taxa는 자동 제거 (R03 removal 로직).

```
build_assertion_db.py:

1. 빈 DB 생성 (schema only)
2. FOR EACH source_file in 입력 파일 순서:
     parse(source_file) → reference + scope + assertions
     import(assertions)
     apply_comprehensive_removal(scope)
3. build_edge_cache() per profile
4. validate()
```

### 재현성

이 소스 파일들만 있으면:
- assertion DB를 **처음부터 완전히 재빌드** 가능
- 각 파일이 하나의 문헌에 대응 → **출처 추적** 명확
- 파일 diff로 **데이터 변경 이력** 관리 (git)

### 기존 파이프라인과의 관계

| 기존 | → 대체 |
|------|--------|
| `data/treatise_1959_taxonomy.txt` (헤더 없음) | `data/sources/treatise_1959.txt` (헤더 포함) |
| `data/treatise_1959_taxonomy.json` | 불필요 (TXT → DB 직접) |
| `scripts/parse_treatise_txt.py` | `scripts/build_assertion_db.py` (통합 파서) |
| `scripts/import_treatise1959.py` | 위와 동일 |
| `scripts/import_treatise.py` | 위와 동일 |
| `scripts/create_assertion_db.py` | schema + metadata 부분만 존속 |

기존 파일과 스크립트는 프로젝트 구축 과정 기록으로 보존하되,
운영 파이프라인에서는 사용하지 않는다.

### JA2002의 특수성

`jell_adrain_2002.txt`는 다른 파일과 성격이 다르다:
- PLACED_IN 뿐 아니라 **SYNONYM_OF 1,055건**이 핵심
- Formation, Location, Bibliography 등 **부가 데이터**가 방대
- 현재 `trilobite_genus_list.txt`에서 파싱하는 raw_entry 기반 데이터

이 파일은 확장 형식의 계층 본문만으로는 표현이 어려울 수 있으므로,
**synonym 블록**과 **부가 데이터 참조** 방식을 별도로 설계해야 한다.
(향후 R05에서 다룰 예정)

## 구현 우선순위

| 단계 | 작업 | 설명 |
|------|------|------|
| **1** | 확장 형식 파서 | YAML 헤더 + 마커 확장 파싱 |
| **2** | dry-run preview | 파싱 결과 요약 + 확인 프롬프트 |
| **3** | `treatise_1959.txt` 변환 | 기존 TXT → 확장 형식 (헤더 추가) |
| **4** | `treatise_2004_ch4/ch5.txt` 작성 | 기존 JSON 데이터 기반으로 확장 형식 작성 |
| **5** | `build_assertion_db.py` | 소스 파일들 → assertion DB 통합 빌드 |
| **6** | `jell_adrain_2002.txt` 형식 설계 | synonym + 부가 데이터 포함 (R05) |
| **7** | 기존 파이프라인 폐기 | 개별 import 스크립트 retire |

## 관련 문서

- `devlog/20260311_R03_comprehensive_scope_and_removal.md` — Scope 모델, removal 로직
- `devlog/20260302_R01_taxonomy_management.md` — Layered Profile, Revision Package
- `data/treatise_1959_taxonomy.txt` — 기존 TXT 형식 (확장 형식으로 변환 대상)
- `scripts/parse_treatise_txt.py` — 기존 TXT 파서 (통합 파서로 대체 예정)
