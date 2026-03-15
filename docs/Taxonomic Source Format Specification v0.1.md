# Taxonomic Source Format (TSF) v0.1

_Draft_

---

# 1. Overview

**Taxonomic Source Format (TSF)**는 고생물학 및 생물학 문헌에서 제시된 분류학 정보를 구조화하여 기록하기 위한 **human-readable text format**이다.

TSF의 목적은 다음과 같다.
- 문헌 기반 taxonomy 정보를 **사람이 읽기 쉬운 형태로 기록**    
- **Git 기반 버전 관리 가능**    
- **자동 파싱을 통한 데이터베이스 구축 지원**    
- 문헌 provenance 유지    
- taxonomy extraction pipeline의 **중간 표현(intermediate representation)** 제공    

TSF 문서는 두 부분으로 구성된다.
```
YAML metadata
Taxonomy body (DSL)
```
---
# 2. Document Structure

TSF 문서는 다음 구조를 가진다.
```
---
YAML metadata
---

taxonomy DSL body
```
예:
```
---
reference: Bulman, O.M.B., 1955...
scope:
  - taxon: Graptolithina
    coverage: comprehensive
notes: Class-level treatment of Graptolithina
---

Class Graptolithina Bronn, 1846
Order DENDROIDEA Nicholson, 1872
  Family DENDROGRAPTIDAE Roemer in Frech, 1897
    Dendrograptus HALL, 1858 [*Graptolithus hallianus] | L.Cret.(L.Hauteriv.-U.Hauteriv.), Eu.-Patag. | LCRET
      = Callodendrograptus DECKER, 1945
```
---
# 3. Metadata Layer (YAML)

이 레이어는 **문헌 provenance와 문서 범위**를 기록한다.
## Required
### reference
문헌 출처.
```yaml
reference: Bulman, O.M.B., 1955. Graptolithina...
```
---
## Recommended
### scope
문헌이 다루는 taxon 범위.
```yaml
scope:
  - taxon: Graptolithina
    coverage: comprehensive
```
coverage 값 예:
```
comprehensive
partial
```
---
### notes
문헌에 대한 설명.
```yaml
notes: |
  Class-level treatment of Graptolithina.
```
---
## Optional
다음 필드는 프로젝트 관리용이다.
```
editor
date_created
source_pdf
format
version
```
예:
```yaml
format: TSF
version: 0.1
```
---
# 4. Taxonomy DSL Layer

이 레이어는 **taxonomy 구조와 taxon 정보를 기록**한다.
Hierarchy는 **indentation**으로 표현된다.
```
Class
  Order
    Family
      Genus
```
---
# 5. Taxon Header (Required)

모든 taxon line은 다음 정보를 포함한다.
```
Rank Name Author, Year
```

예:
```
Class Graptolithina Bronn, 1846
Order DENDROIDEA Nicholson, 1872
Family DENDROGRAPTIDAE Roemer in Frech, 1897
```
---
# 6. Type Species (Recommended)

Genus entry에서는 type species를 기록할 수 있다.
```
[*type species]
```

예:
```
Dendrograptus HALL, 1858 [*Graptolithus hallianus]
```
---
# 7. Synonym (Recommended)

Synonym은 다음과 같이 기록한다.
```
= synonym AUTHOR, YEAR
```

예:
```
= Callodendrograptus DECKER, 1945
```

---

# 8. Temporal Code (Recommended)

Treatise style의 **temporal code**는 별도 필드로 기록된다.
```
| temporal_code
```

예:
```
LCRET
```

이 값은 나중에 ICS stage 등과 매핑될 수 있다.

---
# 9. Source Distribution Text (Source-Preserving Field)

Treatise의 다음 텍스트는 **원문 그대로 보존**한다.

예:
```
L.Cret.(U.Barrem.-L.Alb.), W.Eu.-S.Afr.-E.Austral.
```

TSF에서는 이 필드를 **정규화하지 않고 보존**한다.

예:
```
| L.Cret.(U.Barrem.-L.Alb.), W.Eu.-S.Afr.-E.Austral. |
```

이 필드는 다음 정보를 포함할 수 있다.
- stratigraphic description    
- geographic distribution    
- lithostratigraphic hints    

TSF v0.1에서는 **문법을 강제하지 않는다.**

---
# 10. Genus Line Structure

TSF v0.1에서 **genus entry는 반드시 한 줄(one-liner)**로 기록한다.

구조:
`TaxonHeader | SourceDistributionText | TemporalCode`

구성 요소:

| Field                  | Description                                                  |
| ---------------------- | ------------------------------------------------------------ |
| TaxonHeader            | genus name, author, year, type species                       |
| SourceDistributionText | Treatise style distribution / range text (source-preserving) |
| TemporalCode           | machine-readable temporal code                               |

---
## Syntax
`Genus Author, Year [*Type species] | DistributionText | TemporalCode`

---
## Example
```
Protaconeceras CASEY, 1954 [*Oppelia patagoniensis FAVRE, 1908] | L.Cret.(L.Hauteriv.-U.Hauteriv.), Eu.-Patag. | LCRET
```

```
Aconeceras HYATT, 1903 [*Am. nisus D'ORBIGNY, 1841] | L.Cret.(U.Barrem.-L.Alb.), W.Eu.-S.Afr.-E.Austral. | LCRET
```

```
Falciferella CASEY, 1954 [*F. millbournei] | L.Cret.(M.Alb.), Eu. | LCRET
```

---

## Parser Rule

Genus line은 다음 방식으로 파싱할 수 있다.

`split("|", maxsplit=2)`

결과:

`[0] TaxonHeader [1] SourceDistributionText [2] TemporalCode`

---

## Design Rationale

Genus entry를 one-liner로 제한하는 이유:
- parser 단순화    
- Git diff 안정성    
- Treatise typography와 호환    
- 수작업 입력 편의성```

---
# 11. Optional Structured Fields

필요할 경우 다음 필드를 추가할 수 있다.
```
geo
country
formation
locality
notes
```

예:
```
geo: USA; Canada
formation: Kaili Formation
locality: Guizhou
```

하지만 TSF v0.1에서는 **권장되지 않는다**.  
가능하면 **source text 보존 방식을 우선**한다.

---
# 12. Parser Output (Recommended Structure)

TSF parser는 다음 데이터 구조를 생성할 수 있다.
```
Taxon
TaxonParent
Synonym
TypeSpecies
TemporalRange
DistributionText
```

---
# 13. Pipeline Position

TSF는 다음 pipeline에서 사용된다.

```
Literature (PDF)
      ↓
Manual / AI extraction
      ↓
TSF document
      ↓
Parser
      ↓
Taxonomic assertions
      ↓
Database
```

---

# 14. Design Principles

TSF는 다음 원칙을 따른다.
1. human readable    
2. literature structure preservation    
3. git diff friendly    
4. minimal syntax    
5. extensible    

---

# 15. Summary of Field Categories

## Required

```
rank
name
author
year
parent (indentation)
```

---
## Recommended

```
type species
synonym
temporal_code
```

---
## Source-preserving

```
source_distribution_text
```

---

TSF는 **taxonomy literature extraction을 위한 intermediate knowledge format**으로 설계되었으며  Treatise, Jell & Adrain (2002) 등의 taxonomy 문헌 구조를 직접 표현할 수 있도록 한다.