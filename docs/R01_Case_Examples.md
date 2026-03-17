# Trilobase 논문 보강 사례 모음

**Date**: 2026-03-12
**Purpose**: R01 Review에서 지적된 "구체적 데이터/예시 부족" 해소를 위한 실제 DB 사례

---

## 1. Assertion Model 핵심 예시

### 1.1 *Olenellus*: 동일 속, 3개 시대, 3개 다른 배치

*Olenellus* BILLINGS, 1861은 대표적인 Lower Cambrian 삼엽충 속으로, 세 문헌에서 서로 다른 분류 위치에 배치되었다.

| # | Subject | Predicate | Object | Reference |
|---|---------|-----------|--------|-----------|
| 1 | *Olenellus* | PLACED_IN | Olenellinae | Moore (Ed.), 1959 |
| 2 | *Olenellus* | PLACED_IN | Olenellidae | Jell & Adrain, 2002 |
| 3 | *Olenellus* | PLACED_IN | Olenellinae | Palmer & Repina, 2004 |

- 1959 Treatise는 subfamily Olenellinae에 배치
- Jell & Adrain (2002)는 subfamily를 사용하지 않고 family Olenellidae에 직접 배치
- 2004 Treatise 개정판은 다시 Olenellinae로 복귀

**논문 활용**: "Which placement is correct?"가 아니라 "all three are recorded assertions" — 이것이 assertion model의 핵심.

### 1.2 유명 삼엽충 속들의 분류 이동 패턴

| Genus | 1959 Treatise | Jell & Adrain 2002 | 2004 Treatise | 변화 유형 |
|-------|--------------|---------------------|---------------|-----------|
| *Agnostus* | Agnostidae | Agnostidae | Agnostinae | family → subfamily |
| *Paradoxides* | Paradoxidinae | Paradoxididae | Paradoxididae | subfamily → family |
| *Phacops* | Phacopinae | Phacopidae | — | subfamily → family |
| *Calymene* | Calymeninae | Calymenidae | — | subfamily → family |
| *Dalmanites* | Dalmanitinae | Dalmanitidae | — | subfamily → family |
| *Illaenus* | Illaeninae | Illaenidae | — | subfamily → family |
| *Proetus* | Proetinae | Proetidae | — | subfamily → family |
| *Asaphus* | Asaphinae | Asaphidae | — | subfamily → family |
| *Sao* | Saoinae | **Solenopleuridae** | — | **과 자체가 변경** |

**패턴**: 1959 Treatise는 subfamily 수준까지 세분화한 반면, Jell & Adrain (2002)는 대부분 family 수준에서 배치. *Sao*의 경우는 과(Family) 자체가 달라지는 더 큰 변화를 보여준다.

### 1.3 Assertion Status의 다양성

단순한 "배치(asserted)" 외에도, 분류학적 불확실성을 assertion level에서 표현한다:

| Status | 건수 | 의미 | 예시 |
|--------|------|------|------|
| asserted | 8,255 | 확정적 배치 | *Olenellus* → Olenellidae |
| questionable | 127 | 잠정적 배치 (?FAMILY) | *Atopiaspis* → ?Alokistocaridae |

**구체적 questionable 사례:**
- *Atopiaspis* → ?Alokistocaridae
- *Avalonia* → ?Atopidae
- *Miraculaspis* → ?Condylopygidae

→ 기존 DB에서는 "belongs to" 또는 "does not belong to"의 이진 관계만 가능하지만, assertion model에서는 `questionable` status로 원문의 불확실성을 보존.

---

## 2. Classification Profile 비교

### 2.1 3개 Profile 규모

| Profile | 설명 | Edge 수 | 포함 Taxa 수 |
|---------|------|---------|-------------|
| default | Jell & Adrain 2002 + Adrain 2011 | 5,113 | 5,113 |
| treatise1959 | Treatise Part O (Moore Ed.) | 1,772 | 1,772 |
| treatise1997 | Treatise 개정 (Agnostida + Redlichiida) | 2,045 | 2,045 |

### 2.2 Profile 간 Taxa 교차

| 범주 | 건수 |
|------|------|
| default에만 존재 | 3,593 |
| treatise1959에만 존재 | 252 |
| 양쪽 공통 | 1,520 |

- **3,593 default-only**: 1959년 이후 신규 기재되었거나 JA2002에서 새로 인정된 taxa
- **252 treatise1959-only**: 1959년 체계에서만 사용된 higher taxa (superfamily 등) 중 이후 폐기/재편된 것들

### 2.3 Higher-Level 재배치 사례

Profile 간 차이는 주로 **family 이상 상위 분류군** 수준에서 발생한다:

#### (a) Order/Suborder 수준 재편

| Taxon | Rank | default (JA2002) | treatise1959 | 변화 |
|-------|------|-------------------|--------------|------|
| Illaenina | Suborder | Corynexochida | PTYCHOPARIIDA | **다른 Order로 이동** |
| Eodiscidae | Family | Eodiscida | Eodiscina | order ↔ suborder |
| Corynexochidae | Family | Corynexochina | Corynexochida | suborder ↔ order |

**Illaenina 사례**: 1959 Treatise에서는 Ptychopariida에 속했으나, 현대 분류(JA2002)에서는 Corynexochida로 이동. 그 하위 family들(Illaenidae, Styginidae 등)과 25개 genus가 함께 이동.

#### (b) Superfamily 이름 변경 (명명법 규약 반영)

| Taxon | default (JA2002) | treatise1959 |
|-------|-------------------|--------------|
| Agraulidae | Ellipsocephaloidea | Solenopleuracea |
| Phacopidae | Phacopoidea | Phacopacea |
| Dalmanitidae | Dalmanitoidea | Dalmanitacea |
| Abadiellidae | Redlichioidea | Redlichiacea |

→ `-oidea` (현대 표준) vs `-acea` (1959 관례) — ICZN 명명법 규약 변경을 반영.

#### (c) Genus 수준 재배치

Illaenina 산하 genus들의 family 배치도 profile에 따라 다르다:

| Genus | default (JA2002) | treatise1959 |
|-------|-------------------|--------------|
| *Illaenus* | Illaenidae | Illaeninae |
| *Dysplanus* | Illaenidae | Bumastinae |
| *Stenopareia* | Illaenidae | Illaeninae |
| *Thaleops* | Styginidae | Illaeninae |
| *Panderia* | Panderiidae | Illaeninae |
| *Cekovia* | Styginidae | Illaeninae |

→ 1959년에는 Illaeninae(아과) 하나에 뭉쳐 있던 속들이, JA2002에서는 Illaenidae, Styginidae, Panderiidae 등 여러 과로 분산 배치.

---

## 3. Synonym 관계 네트워크

### 3.1 Synonym Type 분포

Trilobase DB에는 1,075개의 SYNONYM_OF assertion이 있으며, 다음과 같이 분류된다:

| Type | 건수 | 설명 |
|------|------|------|
| j.s.s. (junior subjective synonym) | 725 | 주관적 동의어 — 저자의 판단에 따라 동일 taxon으로 간주 |
| preocc. (preoccupied) | 145 | 선점된 이름 — 다른 분류군에 이미 사용됨 |
| replacement | 125 | 대체 이름 — preoccupied name을 대체 |
| j.o.s. (junior objective synonym) | 53 | 객관적 동의어 — 같은 type specimen에 기반 |
| suppressed | 9 | ICZN에 의해 공식 억제 |

### 3.2 *Sao* BARRANDE, 1846: 9개 동의어 네트워크

Cambrian 삼엽충 *Sao*는 가장 많은 동의어를 가진 속 중 하나이다:

| Junior Synonym | Author | Year | Type |
|----------------|--------|------|------|
| *Monadina* | BARRANDE | 1846 | j.s.s. |
| *Acanthocnemis* | HAWLE & CORDA | 1847 | j.s.s. |
| *Crithias* | HAWLE & CORDA | 1847 | j.s.s. |
| *Endogramma* | HAWLE & CORDA | 1847 | j.s.s. |
| *Enneacnemis* | HAWLE & CORDA | 1847 | j.s.s. |
| *Micropyge* | HAWLE & CORDA | 1847 | j.s.s. |
| *Selenosema* | HAWLE & CORDA | 1847 | j.s.s. |
| *Staurogmus* | HAWLE & CORDA | 1847 | j.s.s. |
| *Tetracnemis* | HAWLE & CORDA | 1847 | j.s.s. |

→ 모두 HAWLE & CORDA (1847)가 분리 기재한 것을 이후 *Sao*의 동의어로 통합. 하나의 속에 대해 10개의 이름이 존재하며, 이 관계를 모두 assertion으로 보존.

### 3.3 다수 동의어를 가진 속 Top 5

| Senior Name | 동의어 수 | Junior Synonyms |
|-------------|-----------|-----------------|
| *Sao* | 9 | Acanthocnemis, Crithias, Endogramma, Enneacnemis, Micropyge, Monadina, Selenosema, Staurogmus, Tetracnemis |
| *Ptychagnostus* | 8 | Acidusus, Aotagnostus, Aristarius, Canotagnostus, Huarpagnostus, Pentagnostus, Triplagnostus, Zeteagnostus |
| *Proetus* | 8 | Aeonia, Devonoproetus, Euproetus, Falcatoproetus, Forbesia, Scotoproetus, Trigonaspis (×2) |
| *Tsunyidiscus* | 6 | Emeidiscus, Guizhoudiscus, Hupeidiscus, Liangshandiscus, Mianxiandiscus, Shizhudiscus |
| *Pseudagnostus* | 6 | Litagnostus, Plethagnostus, Pseudagnostina, Rhaptagnostus, Sulcatagnostus, Xestagnostus |

### 3.4 Preoccupied Name → Replacement Name 사례

이름이 다른 생물 분류군에서 먼저 사용된 경우, 새 이름(replacement name)이 제안된다:

| Preoccupied Name | Author, Year | Replacement Name | Author, Year |
|------------------|-------------|------------------|-------------|
| *Amphion* | PANDER, 1830 | *Pliomera* | ANGELIN, 1854 |
| *Arethusa* | BARRANDE, 1846 | *Arethusina* | BARRANDE, 1852 |
| *Arges* | GOLDFUSS, 1839 | *Ceratarges* | GURICH, 1901 |
| *Acheilus* | CLARK, 1924 | *Peracheilus* | LUDVIGSEN, 1986 |
| *Actinopeltis* | POULSEN, 1946 | *Grinnellaspis* | POULSEN, 1948 |
| *Anderssonia* | SUN, 1924 | *Anderssonella* | KOBAYASHI, 1936 |

→ 이 두 이름(preoccupied + replacement)은 각각 별도의 taxon 레코드로 존재하며, `preocc.` / `replacement` 타입의 SYNONYM_OF assertion으로 연결.

---

## 4. SCODA 기술 스펙

### 4.1 artifact_metadata

```
artifact_id  : trilobase
name         : Trilobase
version      : 0.3.0
schema_version: 1.0
license      : CC-BY-4.0
description  : Assertion-centric trilobite taxonomy — built from canonical source data
```

### 4.2 ui_manifest 구조 (발췌)

```json
{
  "default_view": "taxonomy_tree",
  "global_controls": [
    {
      "type": "select",
      "param": "profile_id",
      "label": "Profile",
      "source_query": "classification_profiles_selector",
      "default": 1
    }
  ],
  "views": {
    "taxonomy_tree": {
      "type": "hierarchy",
      "display": "tree",
      "title": "Taxonomy",
      "source_query": "taxonomy_tree",
      "hierarchy_options": {
        "id_key": "id",
        "parent_key": "parent_id",
        "label_key": "name",
        "rank_key": "rank",
        "leaf_rank": "Family"
      }
    }
  }
}
```

→ UI는 코드가 아닌 **선언적 manifest**로 정의됨. `source_query`가 named SQL query를 참조하고, `global_controls`의 profile selector가 모든 뷰에 걸쳐 classification profile을 전환.

### 4.3 Named SQL Queries (46개)

DB에 내장된 SQL 쿼리로, 별도 코드 없이 manifest에서 참조:
- `taxonomy_tree`: profile 기반 분류 트리
- `family_genera`: family별 genus 목록
- `genus_detail`: 속 상세 정보
- `genus_synonyms`: 동의어 목록
- `genus_bibliography`: 참고문헌
- `classification_profiles_selector`: profile 목록
- `profile_diff_*`: profile 간 비교 쿼리

---

## 5. 전체 DB 통계 요약

| 항목 | 수 |
|------|-----|
| **Taxon 총계** | **5,627** |
| — Class | 1 (Trilobita) |
| — Order | 15 |
| — Suborder | 16 |
| — Superfamily | 48 |
| — Family | 245 |
| — Subfamily | 146 |
| — Genus | 5,156 |
| Valid genera | 4,771 |
| Invalid genera (synonyms etc.) | 856 |
| **Assertion 총계** | **8,382** |
| — PLACED_IN (asserted) | 7,178 |
| — PLACED_IN (questionable) | 127 |
| — SYNONYM_OF | 1,075 |
| — SPELLING_OF | 2 |
| **Reference** | **2,135** |
| **Classification Profiles** | **3** |
| genus_formations | 4,503 |
| genus_locations | 4,849 |
| ui_queries | 46 |

---

## 6. 논문 반영 권고

### Figure 후보

1. **Assertion Diagram**: *Olenellus*의 3개 PLACED_IN assertion을 시각적으로 표현 — "같은 속, 다른 시대, 다른 배치"
2. **Profile Diff Tree**: Illaenina의 Ptychopariida → Corynexochida 이동을 두 트리로 대비
3. **Synonym Network**: *Sao*의 9개 동의어를 방사형 다이어그램으로 표현

### Table 후보

1. **Table 1**: 유명 삼엽충 속들의 3-source 배치 비교 (Section 1.2)
2. **Table 2**: Synonym type 분포 (Section 3.1)
3. **Table 3**: DB 통계 요약 (Section 5)

### 본문 반영 포인트

- **Section 04 (Assertion Model)**: 1.1의 *Olenellus* 사례 + 1.3의 assertion_status
- **Section 05 (Classification Profiles)**: 2.2–2.3의 profile 교차 분석 + higher-level 재배치
- **Section 06 (SCODA)**: 4.1–4.3의 기술 스펙
- **Section 07 (Case Study)**: 전체 통계(Section 5) + 3.2의 *Sao* 동의어 네트워크
