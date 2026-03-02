# R01: 시간에 따라 변화하는 Taxonomy를 효과적으로 관리하는 방법

**Date:** 2026-03-02
**Type:** Review (아이디어 탐색)

## 배경

### 현재 assertion DB 구조

```
taxon (5,391)  ←  assertion (6,563)  →  reference (2,134)
                      ↓
              classification_profile (3)
                      ↓
           classification_edge_cache (10,221)
```

- `taxon`: parent_id 없음. 모든 계층은 assertion에서 파생
- `assertion`: subject → predicate → object 형태. PLACED_IN이 계층 구조를 결정
- `reference`: 각 assertion의 출처 논문
- `classification_profile`: 특정 규칙으로 assertion을 선별하여 tree를 구성
- `classification_edge_cache`: profile별로 미리 계산된 parent-child 인접 리스트

### 현재 데이터 현황

| Profile | 설명 | Edge 수 |
|---------|------|---------|
| default (id=1) | JA2002 + A2011 accepted | 5,083 |
| ja2002_strict (id=2) | JA2002만 (데이터 거의 없음) | - |
| treatise2004 (id=3) | default + Treatise override | 5,138 |

### 핵심 문제

현재 시스템은 **대형 모노그래프** (JA2002, Treatise 등) 단위로 설계되어 있다.
이들은 대부분의 taxa를 다루기 때문에 하나의 profile로 tree 전체를 구성할 수 있다.

하지만 실제 분류학에서는:

1. **부분 개정(partial revision)**: "Phacopidae의 revision" — 한 Family만 다룸
2. **점진적 축적**: 수십 년에 걸쳐 여러 논문이 조금씩 분류를 수정
3. **의견 충돌**: 같은 taxon에 대해 저자마다 다른 배치를 주장
4. **다중 해상도**: 어떤 논문은 Genus 배치만, 어떤 논문은 Family 간 관계도 수정

부분 개정 논문의 경우, 해당 논문이 "어떤 전체 분류 체계를 따르는지"가 불명확하다.
Smith (2015)가 Phacopidae 5속을 재배치했다면, 나머지 5,000+속은 어떤 분류를 따를 것인가?

---

## 아이디어 1: Layered Profile (계층적 프로필 합성)

**핵심**: Profile을 단일 규칙이 아닌, 여러 "layer"의 스택으로 구성한다.

```
profile "working_2026" = [
    Layer 0: default (JA2002 + A2011)    — base, 전체 범위
    Layer 1: Treatise 2004               — Agnostida/Redlichiida 범위
    Layer 2: Smith 2015                  — Phacopidae 범위
    Layer 3: User corrections            — 개별 수정
]
```

상위 layer가 하위를 override한다. 각 taxon의 배치는 가장 높은 layer에서 결정.

**장점:**
- 부분 개정의 자연스러운 통합
- layer 추가/제거로 "만약 이 논문을 반영하면?" 시뮬레이션 가능
- 현재 treatise2004 profile이 이미 이 패턴 (default를 복사 → Treatise 범위만 덮어쓰기)

**구현 스케치:**

```sql
CREATE TABLE profile_layer (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL REFERENCES classification_profile(id),
    layer_order INTEGER NOT NULL,          -- 0 = base, 높을수록 우선
    reference_id INTEGER REFERENCES reference(id),  -- 이 layer의 출처
    scope_description TEXT,                -- "Phacopidae revision" 등
    scope_filter_json TEXT,                -- 자동 범위 결정용
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(profile_id, layer_order)
);
```

Edge cache 빌드 시:
```
for each taxon:
    placement = highest-layer assertion that covers this taxon
    if none found → fall through to base layer
```

**고려사항:**
- "이 논문이 이 taxon을 다루는가?"를 어떻게 판단할 것인가?
  - 명시적: reference가 cover하는 taxon 목록을 직접 지정
  - 암시적: 해당 reference_id를 가진 assertion이 있는 taxon만 해당
  - 범위 기반: "Phacopidae 하위 전체" 같은 규칙으로 지정

---

## 아이디어 2: Assertion Timeline (개별 taxon의 의견 이력)

**핵심**: 각 taxon에 대해 시간순으로 모든 의견을 추적하고, 최신 의견을 current로 삼는다.

```
Olenus placement history:
  1959  Whittington  → Olenidae      (original)
  2002  JA2002       → Olenidae      (confirmed)
  2015  Smith        → Oleninae      (subfamily로 세분화)
  2020  Jones        → Olenidae      (subfamily 불인정, 환원)
  Current accepted: Olenidae (Jones 2020)
```

현재 구조에서 이미 가능하다:
- 같은 `subject_taxon_id + predicate=PLACED_IN`에 대해 여러 assertion 가능
- `is_accepted=1`인 것이 현재 배치, 나머지는 이력

**부족한 부분:**
- assertion에 시간 순서가 명시적이지 않음 (reference.year로 유추 가능하나 불완전)
- "이 assertion이 저 assertion을 supersede했다"는 관계가 없음

**개선안:**

```sql
ALTER TABLE assertion ADD COLUMN supersedes_id INTEGER REFERENCES assertion(id);
-- 또는
ALTER TABLE assertion ADD COLUMN effective_year INTEGER;
```

`supersedes_id`가 있으면 의견 변천의 연쇄(chain)를 추적할 수 있다:
```
assertion 4521 (JA2002: Olenus → Olenidae, is_accepted=0, superseded by 8901)
  ↓ superseded by
assertion 8901 (Smith 2015: Olenus → Oleninae, is_accepted=0, superseded by 9102)
  ↓ superseded by
assertion 9102 (Jones 2020: Olenus → Olenidae, is_accepted=1)
```

**장점:**
- 개별 taxon 수준에서 의견 변천사 완전 추적
- UI에서 taxon detail 페이지에 "opinion history" 표시 가능
- "왜 이렇게 배치되었는가?"에 대한 답변 가능

---

## 아이디어 3: Revision Package (개정 논문 일괄 import)

**핵심**: 하나의 논문에서 나온 의견을 "패키지"로 묶어 관리한다.

```sql
CREATE TABLE revision_package (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,                    -- "Smith 2015: Phacopidae revision"
    reference_id INTEGER REFERENCES reference(id),
    scope_taxa TEXT,                        -- JSON: 대상 taxa 범위
    assertion_count INTEGER,
    status TEXT DEFAULT 'pending'
        CHECK(status IN ('pending','reviewed','accepted','rejected')),
    applied_to_profile_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE revision_package_assertion (
    package_id INTEGER NOT NULL REFERENCES revision_package(id),
    assertion_id INTEGER NOT NULL REFERENCES assertion(id),
    PRIMARY KEY (package_id, assertion_id)
);
```

**워크플로우:**

```
1. 논문 import → reference 생성 + assertion 생성 (is_accepted=0) + package 생성
2. Review 단계: 패키지 내 assertion들을 하나씩 또는 일괄 검토
3. Accept: is_accepted=1로 전환, 기존 competing assertion은 is_accepted=0으로
4. Edge cache 재빌드
```

**장점:**
- 대형 모노그래프와 부분 개정 모두 같은 워크플로우
- "이 논문의 변경사항 되돌리기(revert)" 가능 (패키지 단위)
- 검토 상태 추적 가능

---

## 아이디어 4: Working Classification (사용자의 현행 분류)

**핵심**: 특별한 "working" 프로필로, 사용자가 자신의 최선의 판단에 따라 분류를 유지한다.

현재 `default` 프로필이 사실상 이 역할인데, 이를 명시적으로 만들자.

```
classification_profile:
  id=1  "default"           — JA2002+A2011 원본 (immutable, 참조용)
  id=3  "treatise2004"      — Treatise hybrid (immutable, 참조용)
  id=10 "working"           — 사용자의 현행 분류 (mutable)
```

Working profile의 특징:
- 처음에는 default의 복사본
- 사용자가 assertion을 추가/수정하면 working profile의 edge cache가 갱신
- 다른 profile은 항상 원본 상태 유지 (비교 가능)

**장점:**
- 원본 데이터를 건드리지 않고 분류 커스터마이징
- "내 분류 vs JA2002 vs Treatise" 비교 가능
- 되돌리기가 쉬움 (working을 default로 리셋)

---

## 아이디어 5: Scope-Aware Assertion (범위 인식 assertion)

**핵심**: 각 assertion에 "이 의견이 적용되는 범위"를 명시한다.

부분 개정 논문의 가장 큰 문제는 "이 논문이 다루지 않은 taxa는 어떻게 되는가?"이다.
범위를 명시하면 이 문제가 해결된다:

```sql
-- 예: Smith 2015가 Phacopidae 내부를 개정한 경우
-- scope = "이 논문은 Phacopidae 하위 taxa의 배치에 대해 의견을 제시"
-- 범위 밖의 taxa에 대해서는 이 논문의 assertion이 존재하지 않으므로 이전 의견 유지

-- 범위가 중요한 이유:
-- Smith 2015에 Phacops가 언급되지 않았다면
--   해석1: Smith는 기존 배치에 동의 (silence = agreement)
--   해석2: Smith는 Phacops를 다루지 않았을 뿐 (silence = no opinion)
```

이것은 사실 현재 구조에서도 자연스럽게 처리된다:
- 논문이 다루는 taxa에 대해서만 assertion이 생성됨
- 언급하지 않은 taxa에 대해서는 assertion이 없음 → 이전 의견 유지

따라서 **별도 메타데이터 없이 "assertion이 없으면 의견 없음"** 규칙으로 충분할 수 있다.
다만, "침묵 = 동의"인지 "침묵 = 의견 없음"인지는 논문마다 다를 수 있어서,
reference 수준에서 `scope_type` 메타데이터가 있으면 좋을 수 있다:

```sql
ALTER TABLE reference ADD COLUMN scope_type TEXT
    CHECK(scope_type IN ('comprehensive','partial','targeted'));
-- comprehensive: 전체 분류를 다룸 (언급 안 된 taxa = 기존과 동일하다고 봄)
-- partial: 특정 그룹만 다룸 (언급 안 된 taxa = 의견 없음)
-- targeted: 특정 taxa만 다룸 (가장 좁은 범위)
```

---

## 아이디어 6: Temporal Authority (시간적 우선권)

**핵심**: 같은 taxon에 대한 여러 의견 중, 기본적으로 가장 최신 의견을 채택한다.

```
Rule: accepted assertion = latest reference.year for each (subject, predicate)
```

이것은 자동화된 "working classification" 빌드에 해당한다:
- 수동으로 is_accepted를 관리하는 대신
- reference.year를 기준으로 자동 결정
- 예외가 필요하면 사용자가 override

**장점:**
- 새 논문 import 시 자동으로 분류 업데이트
- 관리 부담 최소화

**위험:**
- 최신이 항상 최선은 아님 (contrarian 의견, 반박된 논문 등)
- 사용자 검토 없이 자동 적용되면 위험

**절충안**: temporal authority를 `auto_accept` 옵션으로만 제공하고, 기본값은 수동 검토

---

## 종합 제안: 단계적 접근

현재 구조는 이미 핵심 기반을 갖추고 있다:
- assertion으로 다중 의견 저장 ✓
- reference로 출처 추적 ✓
- profile로 대안 분류 구현 ✓
- is_accepted로 현행 분류 표시 ✓
- edge cache로 빠른 tree 탐색 ✓

### Phase A: 최소한의 구조 보강

현재 구조에 작은 추가만으로 큰 효과를 낼 수 있는 것들:

1. **`assertion.effective_year`** 추가 — reference.year에서 파생하되 독립적으로 override 가능.
   시간순 정렬 및 "최신 의견 우선" 로직의 기반.

2. **`reference.scope_type`** 추가 — comprehensive/partial/targeted.
   부분 개정 논문의 범위를 명시.

3. **Taxon opinion history UI** — 이미 가능한 데이터로 taxon detail에
   "이 속에 대한 모든 PLACED_IN 의견" 목록을 시간순으로 표시.

### Phase B: Revision Package 워크플로우

4. **revision_package 테이블** — 논문 단위로 assertion을 묶어 관리.
   import → review → accept/reject 워크플로우.

5. **Package accept/reject** — 패키지 내 모든 assertion을 일괄
   accept (기존 competing assertion은 자동 deactivate).

### Phase C: Layered Profile

6. **profile_layer 테이블** — profile을 layer 스택으로 구성.
   부분 개정 논문을 layer로 추가하면 자동으로 합성된 tree 생성.

7. **"Working" profile** — 사용자의 현행 분류를 관리하는 mutable profile.
   default를 base로, 개별 수정과 논문 반영을 layer로 쌓아감.

### Phase D: Tree-Based Editing (향후)

8. **Tree UI에서 drag-and-drop** — taxon을 다른 parent로 옮기면
   자동으로 assertion 생성 + working profile 갱신.

---

## 고려할 질문들

1. **is_accepted 관리**: 수동 vs 자동(최신 우선) vs 하이브리드?
2. **Profile immutability**: 논문 기반 profile은 immutable, working만 mutable?
3. **충돌 해결**: 같은 taxon에 대해 동시에 두 논문이 다른 배치를 주장하면?
4. **사용자 권한**: 누구나 working profile을 수정할 수 있는가?
   (현재는 single-user이므로 문제 없지만, 향후 multi-user 시 중요)
5. **Edge cache 성능**: layer 수가 많아지면 빌드 시간은?
   (현재 5,000 edge 기준 문제 없지만, layer 10개 × 5,000이면?)
6. **Data import format**: 새 논문의 분류를 어떤 형식으로 입력받을 것인가?
   (JSON? CSV? Interactive UI?)
7. **Treatise import 패턴**: 현재 `import_treatise.py`가 하는 일을
   일반화하여 "any revision import" 스크립트로 만들 수 있는가?

---

## 현재 시스템으로 가능한 것 vs 추가 필요한 것

| 기능 | 현재 가능? | 추가 필요 |
|------|-----------|----------|
| 다중 의견 저장 | ✅ assertion 테이블 | - |
| 출처 추적 | ✅ reference_id | - |
| 대안 분류 비교 | ✅ profile + edge cache | - |
| 의견 이력 조회 | ⚠️ 데이터 있음, UI 없음 | UI query 추가 |
| 부분 개정 반영 | ⚠️ 수동으로 가능 | Layered profile |
| 논문 단위 import/revert | ❌ | Revision package |
| 최신 의견 자동 채택 | ❌ | effective_year + 로직 |
| Working classification | ⚠️ default가 사실상 담당 | 명시적 working profile |
| Tree UI에서 편집 | ❌ | Tree interaction layer |

---

## 결론

현재 assertion-centric 모델은 **기반은 탄탄하다**. `taxon + assertion + reference + profile`의
4-pillar 구조가 다중 의견 관리에 적합하게 설계되어 있다.

가장 시급하고 실용적인 개선은:
1. **Taxon opinion history UI** — 이미 가능한 데이터로 즉시 구현 가능
2. **Revision package** — 논문 단위 일괄 처리 워크플로우
3. **Layered profile** — 부분 개정의 자연스러운 통합

이 세 가지가 있으면, "시간에 따라 변화하는 taxonomy"를 **논문 단위로 import하고,
taxon 단위로 이력을 추적하며, profile 단위로 대안을 비교**할 수 있는 시스템이 된다.

다만 실제 데이터(부분 개정 논문)를 넣어봐야 현실적인 문제점이 드러날 것이다.
Treatise import 경험을 일반화하는 것이 좋은 출발점이 될 수 있다.
