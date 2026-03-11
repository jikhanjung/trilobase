# R03: Comprehensive Scope와 Taxon Removal 처리

**Date:** 2026-03-11
**Type:** Review / Design

## 문제 제기

현재 프로필 비교 시 "A에 있는데 B에 없는 taxon"을 모두 동일하게 처리하고 있다.
그러나 출처(reference)의 성격에 따라 해석이 달라야 한다:

- **Treatise 1959**에 있던 Agnostida 속(genus)이 **Treatise 2004**에서 언급되지 않았다면?
  → 2004 Treatise는 Agnostida를 **포괄적(comprehensive)으로 재정리**했으므로,
  **의도적으로 제외(removed)**한 것으로 봐야 한다.

- 반면 어떤 논문이 특정 속 하나만 다뤘는데 다른 속을 언급하지 않았다면?
  → 그 논문은 해당 속에 대해 **의견이 없는(no opinion)** 것이지, 제외한 것이 아니다.

## 핵심 개념

**"침묵(silence)의 의미는 출처의 범위(scope)에 의해 결정된다."**

- comprehensive 출처의 침묵 = 적극적 제외 (deliberate omission)
- sparse 출처의 침묵 = 무관심 (no opinion)

### Scope의 단위: Reference × Taxon

하나의 reference가 모든 하위 분류군을 동일한 깊이로 다루지는 않는다.

예: Treatise 2004 ch4가 Agnostida를 다루되, 어떤 Superfamily는 전면 재정리하고
다른 Superfamily는 몇 속만 언급할 수 있다.

따라서 **scope는 reference 단위가 아니라 reference × taxon 조합 단위**로 기록해야 한다.

| coverage | 의미 | "침묵"의 해석 |
|----------|------|-------------|
| **comprehensive** | 해당 subtree를 전면 재정리 | 미언급 = **제외(removed)** |
| **sparse** | 일부만 언급 | 미언급 = **의견 없음(no opinion)** |

### Profile vs Reference Scope

- **Profile 수준**: Treatise 자체가 특정 root taxa에 대한 comprehensive treatment.
  Profile이 comprehensive한지는 profile의 성격으로 이미 결정됨.
- **Reference 수준**: Profile 내의 개별 reference가 각 subtree를 어떤 깊이로 다루는지.
  같은 reference 안에서도 subtree마다 coverage가 다를 수 있음.

Profile 내에서 reference가 comprehensive한지를 세밀하게 추적할 필요는
현재 Treatise 간 비교에서는 크지 않다 (Treatise 자체가 comprehensive).
그러나 향후 개별 논문을 addendum으로 추가할 때 이 구분이 필수적이 된다.

## 현재 구현의 한계

### 1. treatise2004 프로필 빌드 방식

현재 `import_treatise.py`의 treatise2004 프로필 빌드 로직:

```
treatise2004 = copy(treatise1959)
             → replace(2004 Agnostida assertions)
             → replace(2004 Redlichiida assertions)
```

**문제**: copy-then-replace 방식은 "2004가 언급한 taxa"만 교체하고,
"1959에는 있지만 2004에서 언급하지 않은 taxa"는 1959 배치를 그대로 유지한다.

예를 들어 1959 Agnostida 하위의 어떤 속이 2004에서 완전히 빠졌다면,
현재는 1959의 배치가 그대로 2004 프로필에 남아있다.
그러나 2004 Treatise가 Agnostida를 comprehensive하게 다뤘다면,
**그 속은 2004 프로필에서 제거되어야 한다.**

### 2. Scope 정보의 부재

현재 scope 관련 정보가 체계적으로 관리되지 않는다:

- `reference` 테이블에 scope 관련 컬럼 없음
- `classification_profile.rule_json`에 자유 텍스트로만 기록
  (예: `"scope": ["Agnostida", "Redlichiida", "Eodiscida"]`)
- 프로필 빌드 시 scope를 고려한 removal 로직 없음

## 설계 제안

### Phase 1: Scope 모델링 — `reference_scope` 테이블

```sql
CREATE TABLE reference_scope (
    id INTEGER PRIMARY KEY,
    reference_id INTEGER NOT NULL REFERENCES reference(id),
    taxon_id     INTEGER NOT NULL REFERENCES taxon(id),
    coverage     TEXT NOT NULL CHECK(coverage IN ('comprehensive', 'sparse')),
    -- comprehensive: 이 subtree를 전면 재정리. 미언급 = 제외.
    -- sparse: 일부만 언급. 미언급 = 의견 없음.
    notes TEXT
);
```

`reference.scope_type` 컬럼은 추가하지 않는다.
Coverage 판단은 전부 `reference_scope` 테이블의 **reference × taxon 조합**에서 결정한다.

#### 데이터 예시

| reference | taxon | coverage | 설명 |
|-----------|-------|----------|------|
| Treatise 1959 | Trilobita | comprehensive | 삼엽충 전체 전면 정리 |
| Treatise 2004 ch4 | Agnostida | comprehensive | Agnostida 전면 재정리 |
| Treatise 2004 ch5 | Redlichiida | comprehensive | Redlichiida 전면 재정리 |
| Jell & Adrain 2002 | Trilobita | comprehensive | 전체 속 목록 |
| 논문 X | Phacopidae | comprehensive | Phacopidae 전면 재분류 |
| 논문 X | Dalmanitidae | sparse | 몇 속만 언급 |
| 논문 Y | *Phacops* | sparse | 단일 속 재기재 |

하나의 reference가 여러 행을 가질 수 있고, 각 subtree별로 coverage가 다를 수 있다.

### Phase 2: Comprehensive Removal 로직

프로필 빌드 시 `reference_scope`를 참조하여 edge cache 생성:

```
프로필 빌드 (예: treatise2004):

1. copy(base_profile)                           -- 기존과 동일
2. replace(새 reference들의 명시적 assertions)   -- 기존과 동일
3. FOR EACH reference R in 이 프로필의 소스들:   -- ★ 신규
     FOR EACH reference_scope RS WHERE RS.reference_id = R.id:
       IF RS.coverage = 'comprehensive':
         scope_subtree = RS.taxon_id 하위의 모든 taxa
         covered_taxa  = R가 PLACED_IN assertion을 가진 taxa

         FOR EACH edge E in 현재 프로필:
           IF E.child ∈ scope_subtree AND E.child ∉ covered_taxa:
             DELETE E  ← "comprehensive scope 내 미언급 = 제외"

       ELSE (sparse):
         -- 아무것도 하지 않음. 명시된 assertion만 이미 step 2에서 반영됨.
```

#### treatise2004 빌드 적용 예시

```
Step 1: copy(treatise1959) → 1,768 edges

Step 2: replace(2004 ch4 + ch5 assertions)
  → Agnostida/Redlichiida 하위 중 2004가 명시한 taxa의 edges 교체/추가

Step 3: comprehensive removal
  RS: (ch4, Agnostida, comprehensive)
    → Agnostida 하위 중 ch4가 assertion하지 않은 taxa의 edges 삭제
  RS: (ch5, Redlichiida, comprehensive)
    → Redlichiida 하위 중 ch5가 assertion하지 않은 taxa의 edges 삭제
```

### Phase 3: Diff 표시 개선

comprehensive removal이 반영되면 프로필 간 diff가 더 정확해진다:

| 상황 | 현재 해석 | 개선된 해석 |
|------|----------|-----------|
| 1959에 있고 2004에 없음 (comprehensive scope 내) | same (1959 배치 유지) | **removed** |
| 1959에 있고 2004에 없음 (comprehensive scope 밖) | same | same (정상) |
| 1959에 없고 2004에 있음 | added | added (정상) |
| 양쪽에 있지만 부모가 다름 | moved | moved (정상) |

#### Removed Taxa 사이드 패널

Removed taxa는 대상 프로필에서 edge가 없으므로 tree에 표시할 수 없다.
Diff Tree / Animation 뷰 옆에 **사이드 패널**로 별도 표시한다.

```
┌──────────────────────────┬─────────────────────┐
│                          │ Removed (23)        │
│                          │ ─────────────────── │
│   Diff Tree /            │ Agnostidae          │
│   Animation              │   Geragnostus       │
│                          │   Cotalagnostus     │
│   (tree canvas)          │ Diplagnostidae      │
│                          │   Oidalagnostus     │
│                          │ ...                 │
│                          │                     │
└──────────────────────────┴─────────────────────┘
```

**패널 표시 내용:**
- Removed taxa 목록 (base 프로필에서의 계층 구조로 그룹화)
- 각 taxon의 **마지막 소속** (base 프로필에서의 parent) 표시
  → "어디서 빠졌는지" 맥락 제공
- Rank 아이콘/색상으로 Family, Genus 등 구분

**인터랙션:**
- 클릭 → taxon detail view로 이동
- 패널 접기/펼치기 토글 (tree canvas 영역 확보)
- Diff Table 뷰에서는 removed taxa가 테이블 행으로 이미 표시되므로 패널 불필요

**데이터 소스:**
- `profile_diff` 쿼리의 `diff_status = 'removed'` 행들
- 또는 base 프로필 edges − target 프로필 edges에서 산출

## 일반화: Layered Profile과의 관계

이 개념은 R01에서 제안한 **Layered Profile**과 자연스럽게 연결된다:

```
Profile = Base Layer + Override Layer₁ + Override Layer₂ + ...
```

각 Layer는 하나의 reference에 대응하고, 그 reference의 `reference_scope` 행들이
layer의 동작 방식을 결정한다:

- **comprehensive scope 행**: 해당 subtree의 기존 배치를 **전면 대체**.
  기존 배치 중 새 reference에서 언급되지 않은 것은 제거.
- **sparse scope 행**: 명시된 taxa에 대해서만 **추가/수정(addendum)**.
  언급되지 않은 기존 배치는 영향받지 않음.

```
예시:

treatise2004 =
    Layer 0: treatise1959
             reference_scope: (Trilobita, comprehensive)
             → 삼엽충 전체 기반

    Layer 1: Shergold et al. 2004
             reference_scope: (Agnostida, comprehensive)
             → Agnostida 하위 전면 교체, 1959에만 있던 것은 제거

    Layer 2: Palmer & Repina 2004
             reference_scope: (Redlichiida, comprehensive)
             → Redlichiida 하위 전면 교체

향후 개별 논문 추가 예시:

my_working_classification =
    Layer 0: treatise2004 (위의 결과)
    Layer 3: Smith 2020
             reference_scope: (Phacopidae, comprehensive),
                              (Dalmanitidae, sparse)
             → Phacopidae 전면 교체 (미언급 taxa 제거)
             → Dalmanitidae는 명시된 것만 수정, 나머지 유지
```

## 구현 우선순위

| 단계 | 작업 | 난이도 | 영향 |
|------|------|--------|------|
| **1** | `reference_scope` 테이블 추가 | 낮음 | 데이터 모델 |
| **2** | 기존 Treatise reference에 scope 데이터 입력 | 낮음 | 데이터 |
| **3** | `import_treatise.py`에 removal 로직 추가 | 중간 | treatise2004 프로필 정확도 |
| **4** | Diff 뷰에서 removal 정확도 개선 확인 | 낮음 | UX |
| **5** | Layered Profile 구조로 일반화 (R01 Phase C) | 높음 | 아키텍처 |

**단계 1~3만으로 현재 treatise2004 프로필의 정확도가 크게 개선된다.**
단계 5는 향후 다양한 논문을 추가할 때 필요하며, 현재 Treatise 간 비교에는 1~3으로 충분하다.

## 관련 문서

- `devlog/20260302_R01_taxonomy_management.md` — Layered Profile, Revision Package 설계
- `devlog/20260302_R02_tree_diff_visualization.md` — Profile Comparison UI 설계
- `devlog/20260301_105_P78_treatise_import.md` — Treatise 2004 import 상세
