# Trilobase DB: Canonical vs Assertion-Centric

두 데이터베이스는 같은 삼엽충 분류 데이터를 담고 있지만, **구조가 다릅니다**.

---

## 1. Canonical DB (`trilobase`)

**분류 계층이 테이블 안에 고정되어 있는 구조.**

각 분류군(taxon)이 하나의 행(row)이고, 그 행 안에 `parent_id`라는 칸이 있어서 "이 분류군의 부모는 누구인가"가 직접 기록되어 있습니다.

```
Abadiella  →  parent_id = Abadiellidae
Abadiellidae  →  parent_id = Redlichioidea
Redlichioidea  →  parent_id = Redlichiina
...
```

- **장점**: 단순하고 직관적. "Abadiella는 어디에 속하나?" → 바로 답이 나옴.
- **한계**: 분류 체계가 **하나**뿐. 시대별로 다른 분류 의견을 표현할 수 없음.

예를 들어, Asaphidae라는 과(Family)가 1959년 Treatise에서는 Asaphacea 아래에, 2011년 Adrain에서는 Asaphoidea 아래에 배치되는데, parent_id 방식으로는 둘 중 하나만 기록할 수 있습니다.

---

## 2. Assertion-Centric DB (`trilobase-assertion`)

**분류 관계를 "주장(assertion)"으로 기록하는 구조.**

분류군 테이블에는 `parent_id`가 없고, 대신 별도의 assertion(주장) 테이블에 관계가 기록됩니다.

```
주장 1: Asaphidae → PLACED_IN → Asaphoidea  (근거: Adrain, 2011)
주장 2: Asaphidae → PLACED_IN → Asaphacea   (근거: Treatise, 1959)
```

이렇게 하면 **같은 분류군에 대해 여러 문헌의 서로 다른 의견을 모두 보관**할 수 있습니다.

### Profile (프로필)

여러 주장 중 어떤 것들을 조합해서 하나의 분류 체계를 만들지를 정하는 것이 **프로필**입니다.

| 프로필 | 설명 | 규모 |
|--------|------|------|
| Jell & Adrain 2002 + Adrain 2011 | 기본 분류 체계 (현대적 관점) | 5,113개 관계 |
| Treatise 1959 | 1959년 Treatise의 분류 체계 | 1,772개 관계 |
| Treatise 2004 | 2004년 Treatise 개정판 반영 | 2,045개 관계 |

프로필을 전환하면 **같은 데이터를 다른 분류 체계로 볼 수 있습니다**.

### 동의어(Synonym)도 주장으로 기록

```
주장: Trigonaspis → SYNONYM_OF → Proetus  (근거: Jell & Adrain, 2002)
```

"Trigonaspis는 Proetus의 동의어다"라는 분류학적 판단도 근거 문헌과 함께 기록됩니다.

---

## 비교 요약

|  | Canonical | Assertion-Centric |
|--|-----------|-------------------|
| 분류 체계 | 1개 (고정) | 여러 개 (프로필로 전환) |
| "A는 B에 속한다" | `parent_id = B` | `A → PLACED_IN → B (근거: 논문)` |
| 근거 문헌 | 기록 안 됨 | 모든 관계에 근거 문헌 첨부 |
| 동의어 | 별도 테이블 | 같은 assertion 테이블 |
| 이견 표현 | 불가 | 같은 분류군에 여러 주장 공존 |
| 분류군 수 | 5,341 | 5,627 (Treatise 출처 추가분 포함) |

---

## 왜 Assertion-Centric으로 바꾸었나

삼엽충 분류는 200년 넘게 연구되어 왔고, 같은 속(Genus)이 시대에 따라 다른 과(Family)에 배치되기도 합니다. Canonical 구조에서는 "현재 통용되는 분류"만 저장할 수 있지만, Assertion-Centric 구조에서는 **모든 시대의 분류 의견을 보존하면서, 원하는 관점으로 전환**할 수 있습니다.
