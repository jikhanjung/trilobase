# Source Data 작성 가이드

이 문서는 `data/sources/` 폴더에 들어가는 분류 소스 파일을 새로 만드는 방법을 설명합니다.

---

## 소스 파일이란?

논문이나 도감에 실린 삼엽충 분류표를 **텍스트 파일 하나**로 옮긴 것입니다. 이 파일들이 모여서 assertion DB가 만들어집니다.

현재 소스 파일 목록:

| 파일 | 출처 | 내용 |
|------|------|------|
| `adrain_2011.txt` | Adrain (2011) | 목(Order)~과(Family) 계층 |
| `jell_adrain_2002.txt` | Jell & Adrain (2002) | 속(Genus) 목록 + 동의어 |
| `treatise_1959.txt` | Treatise (1959) | 전체 분류 체계 |
| `treatise_1997_ch4.txt` | Treatise (1997) ch.4 | Agnostida 개정 |
| `treatise_1997_ch5.txt` | Treatise (1997) ch.5 | Redlichiida 개정 |

---

## 파일 구조

소스 파일은 크게 두 부분으로 나뉩니다: **헤더**와 **본문**.

### 1. 헤더

파일 맨 앞에 `---`로 감싼 메타데이터 블록입니다.

```yaml
---
reference: 저자, 연도. 논문 제목
scope:
  - taxon: 이 논문이 다루는 분류군 이름
    coverage: comprehensive 또는 sparse
notes: |
  자유 메모 (선택사항, 파서가 무시함)
---
```

**실제 예시** (`treatise_1997_ch5.txt`):

```yaml
---
reference: Palmer, A.R. & Repina, L.N., 1997. Classification of the Redlichiida.
  In: Kaesler, R.L. (Ed.), Treatise on Invertebrate Paleontology,
  Part O, Revised, Vol. 1, Ch. 5
scope:
  - taxon: Redlichiida
    coverage: comprehensive
---
```

#### reference

이 파일의 출처 논문입니다. `저자, 연도. 제목` 형식으로 씁니다.

#### scope

이 논문이 **어떤 분류군을 어느 범위까지 다루는지** 선언합니다.

- **`comprehensive`**: 해당 분류군 아래 전체를 다룸. 여기에 안 나온 분류군은 "이 논문에서 제외됨"으로 처리됩니다.
- **`sparse`**: 일부만 다룸. 안 나온 분류군이 있어도 제외로 처리하지 않습니다.

예를 들어 Treatise 1997 ch.5가 Redlichiida를 `comprehensive`로 다루면, 1959년 Treatise에는 있었지만 1997년판에 빠진 속은 "제거된 것"으로 간주합니다.

### 2. 본문

헤더 아래에 분류 계층을 적습니다.

```
Order REDLICHIIDA Richter, 1932
  Suborder OLENELLINA Walcott, 1890
    Superfamily Olenelloidea Walcott, 1890
      Family Olenellidae Walcott, 1890
        Subfamily Olenellinae Walcott, 1890
          Olenellus Hall, 1861
          Fremontella Harrington, 1956
```

---

## 본문 작성 규칙

### 계층 표현

각 줄은 **rank 키워드**로 시작하거나, 키워드 없이 속(Genus) 이름을 씁니다.

인식하는 rank 키워드:

| 키워드 | 분류 단계 |
|--------|-----------|
| `Class` | 강 |
| `Order` | 목 |
| `Suborder` | 아목 |
| `Superfamily` | 상과 |
| `Family` | 과 |
| `Subfamily` | 아과 |
| (키워드 없음) | 속 (Genus) |

**부모-자식 관계는 rank 키워드로 결정됩니다.** 들여쓰기는 가독성을 위한 것이고, 파서는 rank 이름을 보고 계층을 판단합니다. 예를 들어 `Subfamily` 다음에 나오는 키워드 없는 줄은 자동으로 그 Subfamily의 자식(Genus)이 됩니다.

```
Family AGNOSTIDAE M'Coy, 1849          ← Family
  Agnostus Brongniart, 1822            ← Genus (Family의 자식)
  Acmarhachis Resser, 1938             ← Genus (Family의 자식)
Family CLAVAGNOSTIDAE Howell, 1937     ← 다음 Family → stack이 바뀜
  Clavagnostus Howell, 1937            ← 이 Family의 자식
```

### 한 줄의 구성

```
[rank키워드] 이름 저자, 연도 [type species 등 부가정보]
```

- **이름**: 분류군 이름 (예: `Agnostus`, `AGNOSTIDAE`)
- **저자, 연도**: 명명자와 기재 연도 (선택사항)
- **부가정보**: `[` `]` 안에 type species 등 (선택사항, 파서가 무시)

실제 예:

```
Agnostus Brongniart, 1822 [Entomostracites pisiformis]
```

### 특수 마커

#### `?` — 의문시되는 배치 (questionable)

이름 앞에 `?`를 붙이면 "이 분류군이 여기에 속하는지 확실하지 않음"을 뜻합니다.

```
  ?Guanshancephalus Lu & Qian, 1983
```

#### `= ` — 동의어 (synonym)

앞 줄의 속(Genus)에 대한 동의어를 표시합니다. 반드시 `= `(등호+공백)으로 시작합니다.

```
  Parabadiella W. ZHANG, 1966
    = Abadiella (j.s.s., fide JELL in BENGTSON et al., 1990)
```

이것은 "Abadiella는 Parabadiella의 junior subjective synonym이다 (Jell의 의견)"를 뜻합니다.

괄호 안의 약어:
- **j.s.s.** = junior subjective synonym (주관적 후행 동의어)
- **j.o.s.** = junior objective synonym (객관적 후행 동의어)
- **fide 저자, 연도** = ~의 견해에 따르면

#### `~` — 철자 변이 (spelling variant)

```
  ~Ptychopyge = Ptychopyge Angelin, 1854
```

#### `[incertae sedis]` — 분류 위치 불확실

```
  Changqingia [incertae sedis]
```

#### `#` — 주석

파서가 무시하는 메모입니다.

```
  # 2004에서 이 과를 Redlichiidae의 동의어로 처리
```

---

## JA2002 소스의 특수 형식

`jell_adrain_2002.txt`는 속(Genus) 카탈로그이므로 추가 정보가 붙습니다.

```
Family ABADIELLIDAE
  Abadiella HUPE, 1953a [bourgini] | Amouslek Fm, Morocco | LCAM
    = Parabadiella (=Abadiella) (j.s.s., fide W. ZHANG et al., 1997)
```

`|`(파이프)로 구분된 필드:
1. **type species** — `[bourgini]`
2. **산지** — `Amouslek Fm, Morocco` (지층과 국가)
3. **시대 코드** — `LCAM` (Lower Cambrian)

이 파이프 뒤의 부가 정보는 속 목록에만 쓰이는 형식이며, 다른 소스 파일에서는 사용하지 않습니다.

---

## 새 소스 파일 만들기: 단계별

### Step 1: 논문 파악

논문을 읽고 다음을 판단합니다:
- 이 논문이 **어떤 분류군**을 다루는가? (예: Phacopidae)
- **전면 개정**(comprehensive)인가, 일부만 언급(sparse)하는가?

### Step 2: 헤더 작성

```yaml
---
reference: Chatterton, B.D.E. et al., 1999. Revision of Phacopidae
scope:
  - taxon: Phacopidae
    coverage: comprehensive
---
```

### Step 3: 본문 작성

논문의 분류표를 보면서 계층을 옮깁니다.

```
Family PHACOPIDAE Hawle & Corda, 1847
  Subfamily PHACOPINAE Hawle & Corda, 1847
    Phacops Emmrich, 1839
    Eldredgops Struve, 1990
    Viaphacops Maximova, 1972
  Subfamily REEDOPINAE Richter & Richter, 1955
    Reedops Richter & Richter, 1955
```

작성 시 주의사항:

- **rank 키워드를 정확히**: `Family`, `Subfamily`, `Order` 등. 오타가 있으면 파서가 Genus로 인식합니다.
- **이름 철자**: DB에 이미 있는 분류군과 정확히 일치해야 합니다. 일치하지 않으면 새 분류군으로 생성됩니다.
- **들여쓰기**: 스페이스든 탭이든 상관없습니다. 파서는 rank 키워드만 봅니다. 다만 사람이 읽기 좋게 들여쓰기를 맞추는 것을 권장합니다.

### Step 4: 검증

```bash
python scripts/build_assertion_db.py
python scripts/validate_assertion_db.py
```

빌드 후 검증 스크립트를 돌려서 17/17 통과하는지 확인합니다.

---

## 요약: 마커 한눈에 보기

| 표기 | 의미 | 예시 |
|------|------|------|
| `Order/Family/...` | rank 키워드 | `Family AGNOSTIDAE M'Coy, 1849` |
| (키워드 없음) | 속(Genus) | `Agnostus Brongniart, 1822` |
| `?` | 의문시되는 배치 | `?Guanshancephalus Lu & Qian, 1983` |
| `= 대상 (상세)` | 동의어 | `= Abadiella (j.s.s., fide JELL, 1990)` |
| `~` | 철자 변이 | `~Ptychopyge = Ptychopyge` |
| `[incertae sedis]` | 분류 불확실 | `Changqingia [incertae sedis]` |
| `#` | 주석 (무시됨) | `# 이 과는 2004에서 폐기` |

| 헤더 필드 | 의미 |
|-----------|------|
| `reference` | 출처 논문 |
| `scope.taxon` | 다루는 분류군 |
| `scope.coverage` | `comprehensive` (전면) / `sparse` (일부) |
| `notes` | 자유 메모 |
