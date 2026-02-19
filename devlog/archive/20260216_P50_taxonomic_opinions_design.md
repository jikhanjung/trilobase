# P50: Taxonomic Opinions — DB 설계 방안

**작성일:** 2026-02-16
**유형:** Plan (설계 문서)
**상태:** P52로 대체됨

### 문서 관계

- **이 문서 (P50)**: 방안 A/B/C 초기 분석, Eurekiidae 중심 사례
- **P51**: P50에 대한 리뷰 → A' 권고
- **P52 (최종)**: P50 + P51 + 논의를 종합한 확정 계획
- **P53**: 장기 아키텍처 비전 (assertion-centric 모델)

## 문제 정의

현재 DB의 모든 taxonomic_ranks 행은 **하나의 opinion**을 암묵적으로 표현한다.
각 행의 `parent_id`는 "이 taxon은 X에 속한다"는 배치 의견이고,
`is_valid`는 "이 이름은 유효/무효하다"는 유효성 의견이다.

문제는 **하나의 taxon에 대해 복수의 의견이 존재할 때** 이를 표현할 구조가 없다는 것.

### 근거 문헌 (Provenance)

현재 DB의 암묵적 provenance:

| 레벨 | 근거 문헌 | provenance.id |
|------|----------|---------------|
| Family 이상 (Order, Suborder, Superfamily) | Adrain, 2011 | 2 |
| Genus (5,115건) | Jell & Adrain, 2002 | 1 |

하지만 이 연결이 행 단위로 명시되어 있지 않다.
`taxonomic_ranks`에 `provenance_id` 컬럼이 없고,
`bibliography`와 `taxonomic_ranks` 사이에 FK도 없다.

### 규모

"Uncertain" Order (id=144)에 **56개 Family**(전체 191개의 29%)가 배치됨.
Adrain(2011)이 이 Family들의 Order를 결정하지 못한 것.
Eurekiidae는 이 56개 중 하나일 뿐이다.

추가로:
- `?FAMILY` 형태의 불확실 배치: 21개 genus
- INDET (완전 미정): 25개 genus
- parent_id NULL (family 자체 없음): 342개 genus (대부분 무효)

## 중심 사례: Eurekiidae

### 현재 DB 상태

```
Trilobita (Class, id=1, Walch 1771)
  └─ Uncertain (Order, id=144, 저자 없음) ← placeholder, 56개 Family 포함
       └─ Eurekiidae (Family, id=164, Hupé 1953, "11 genera, 32 species")
            ├─ Eurekia (WALCOTT, 1924) — Nevada, USA; UCAM
            ├─ Corbinia (WALCOTT, 1924) — Alberta, Canada; UCAM
            ├─ Tostonia (WALCOTT, 1924) — Nevada, USA; UCAM
            ├─ Maladia (WALCOTT, 1924) — Idaho, USA; UCAM
            ├─ Bayfieldia (CLARK, 1924) — Quebec, Canada; UCAM
            ├─ Bandalaspis (IVSHIN, 1962) — Kazakhstan; UCAM
            ├─ Leocephalus (IVSHIN, 1962) — Kazakhstan; UCAM
            ├─ Lochmanaspis (IVSHIN, 1962) — Kazakhstan; UCAM
            └─ Magnacephalus (STITT, 1971) — Oklahoma, USA; UCAM
```

- 9개 genus 전부 유효 (is_valid=1), 동의어 없음
- 전부 Upper Cambrian (UCAM)
- 지리적 분포: 북미 (USA, Canada) + 중앙아시아 (Kazakhstan)

### 표현해야 할 의견들

**질문: "Eurekiidae는 어떤 Order에 속하는가?"**

| # | 의견 | 근거 | parent_id |
|---|------|------|-----------|
| 1 | Order 미정 (incertae sedis) | Adrain, 2011 | 144 (Uncertain) |
| 2 | Asaphida 소속 | Fortey, 1990 (예시) | 115 (Asaphida) |
| 3 | Ptychopariida 소속 | 다른 저자 (예시) | 99 (Aulacopleurida) |

현재는 의견 1만 DB에 존재. 의견 2, 3을 추가할 구조가 없음.

### 후보 Order 정보

```
id=115  Asaphida (Salter, 1864) — 3 superfamilies, 12 families
id=99   Aulacopleurida (Adrain, 2011) — 15 families (구 Ptychopariida 일부)
id=96   Proetida (Fortey & Owens, 1975) — 2 families
```

참고: Adrain(2011)은 기존 Ptychopariida를 해체하여 Aulacopleurida 등으로 재편함.

## Opinion의 세 가지 유형

분석 결과, opinion이 필요한 필드는 3가지:

### 1. 배치 (Placement)

> "이 taxon은 어디에 속하는가?"

- `parent_id` 값에 대한 의견
- 주요 대상: 56개 Uncertain Family, 21개 `?FAMILY` genus
- 사례: Eurekiidae → Uncertain vs Asaphida vs Ptychopariida

### 2. 유효성 (Validity)

> "이 이름은 유효한가?"

- `is_valid` 값에 대한 의견
- 동의어 관계 (`synonyms` 테이블)도 유효성 의견의 일종
- 현재 synonyms 테이블이 이미 `fide_author/fide_year`로 opinion을 부분적으로 추적 (721건)
- 사례: Bronteus는 Scutellum의 j.s.s. (fide RICHTER & RICHTER, 1926)

### 3. 확신도 (Confidence)

> "이 배치/유효성에 얼마나 확신하는가?"

- `?CERATOPYGIDAE` (물음표), `??DAMESELLIDAE` (물음표 2개), `INDET` (미정)
- 현재는 family 텍스트 필드에 `?` 문자로만 표현
- 구조적 표현 없음

## 설계 방안

### 방안 A: 별도 테이블 (추가형, 최소 변경)

기존 `taxonomic_ranks`는 변경하지 않고, opinion만 별도 테이블에 기록.

```sql
CREATE TABLE taxonomic_opinions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    taxon_id        INTEGER NOT NULL REFERENCES taxonomic_ranks(id),
    opinion_type    TEXT NOT NULL,       -- 'placement', 'validity', 'synonymy'

    -- Placement opinion
    proposed_parent_id INTEGER REFERENCES taxonomic_ranks(id),

    -- Validity opinion
    proposed_valid  INTEGER,            -- 1=valid, 0=invalid

    -- 근거
    bibliography_id INTEGER REFERENCES bibliography(id),
    provenance_id   INTEGER REFERENCES provenance(id),
    author          TEXT,               -- 의견을 제시한 저자
    year            INTEGER,            -- 의견 제시 연도

    -- 상태
    is_accepted     INTEGER DEFAULT 0,  -- 현재 수용된 의견인가?
    confidence      TEXT,               -- 'high', 'medium', 'low', 'uncertain'
    notes           TEXT,

    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_opinions_taxon ON taxonomic_opinions(taxon_id);
CREATE INDEX idx_opinions_type ON taxonomic_opinions(opinion_type);
```

**Eurekiidae 데이터:**

```sql
-- 현재 수용된 의견 (Adrain 2011: incertae sedis)
INSERT INTO taxonomic_opinions
  (taxon_id, opinion_type, proposed_parent_id, provenance_id, author, year, is_accepted, confidence)
VALUES
  (164, 'placement', 144, 2, 'Adrain', 2011, 1, 'low');

-- 대안적 의견 (Fortey 1990: Asaphida)
INSERT INTO taxonomic_opinions
  (taxon_id, opinion_type, proposed_parent_id, bibliography_id, author, year, is_accepted, confidence)
VALUES
  (164, 'placement', 115, NULL, 'Fortey', 1990, 0, 'medium');
```

**장점:**
- 기존 스키마 변경 없음 — taxonomic_ranks, synonyms 테이블 그대로
- 기존 쿼리 100% 호환 (parent_id 기반 트리가 그대로 작동)
- 점진적 데이터 입력 가능 (빈 테이블에서 시작)
- PaleoCore 영향 없음

**단점:**
- `parent_id`와 `is_accepted=1` opinion의 일관성을 수동 관리
- 현재 데이터의 provenance가 여전히 암묵적 (taxonomic_ranks 행 자체에 "이건 Adrain 2011 기반"이라는 표시 없음)
- synonyms 테이블의 기존 fide 데이터와 이중 구조

**일관성 규칙:**
- `taxon.parent_id`는 항상 `is_accepted=1`인 placement opinion의 `proposed_parent_id`와 일치해야 함
- opinion 변경 시 두 테이블 동시 업데이트 (트랜잭션)
- 또는: parent_id를 VIEW로 만들어 opinions에서 파생 (방안 C)

---

### 방안 B: 기존 테이블에 provenance 추가 + 별도 테이블

```sql
-- Step 1: 기존 행의 근거를 명시
ALTER TABLE taxonomic_ranks ADD COLUMN placement_provenance_id
    INTEGER REFERENCES provenance(id);
ALTER TABLE taxonomic_ranks ADD COLUMN placement_confidence TEXT;

-- Step 2: 대안적 의견은 별도 테이블 (방안 A와 동일)
CREATE TABLE taxonomic_opinions (...);
```

**초기 데이터 마이그레이션:**

```sql
-- Family 이상: Adrain 2011 (provenance.id=2)
UPDATE taxonomic_ranks
SET placement_provenance_id = 2
WHERE rank IN ('Order', 'Suborder', 'Superfamily', 'Family');

-- Genus: Jell & Adrain 2002 (provenance.id=1)
UPDATE taxonomic_ranks
SET placement_provenance_id = 1
WHERE rank = 'Genus';

-- Uncertain 배치에는 confidence='low' 표시
UPDATE taxonomic_ranks
SET placement_confidence = 'low'
WHERE parent_id = 144;  -- Uncertain Order 하위 56개 Family
```

**장점:**
- 현재 배치의 근거가 행 단위로 명시됨
- "이 parent_id는 어떤 문헌을 따른 것인가?"에 즉시 답변 가능
- 방안 A의 장점도 그대로 유지

**단점:**
- taxonomic_ranks 스키마 변경 필요 (컬럼 2개 추가)
- PaleoCore의 taxonomic_ranks와 스키마 불일치 발생 가능
- 기존 .scoda 패키지 재생성 필요

---

### 방안 C: 배치를 완전히 opinion으로 분리

```sql
-- taxonomic_ranks에서 parent_id 제거하지는 않지만,
-- "현재 수용된 배치"를 VIEW로 제공

CREATE VIEW accepted_placement AS
SELECT taxon_id, proposed_parent_id AS parent_id
FROM taxonomic_opinions
WHERE opinion_type = 'placement' AND is_accepted = 1;
```

기존 `parent_id`는 캐시/편의용으로 유지하되, 진짜 데이터는 opinions 테이블에.

**장점:** 완전한 모델, 모든 배치가 근거와 함께 존재
**단점:** 기존 모든 쿼리에 JOIN 추가, 5,340건의 초기 마이그레이션 필요, 복잡도 높음

---

## 방안 비교

| 기준 | 방안 A | 방안 B | 방안 C |
|------|--------|--------|--------|
| 기존 스키마 변경 | 없음 | 컬럼 2개 추가 | 없음 (VIEW 추가) |
| 기존 쿼리 호환 | 100% | 100% | 변경 필요 |
| 현재 데이터 provenance | 암묵적 | 명시적 | 명시적 |
| 대안적 의견 | 지원 | 지원 | 지원 |
| PaleoCore 영향 | 없음 | 스키마 불일치 | 없음 |
| 초기 마이그레이션 | 선택적 | 필수 (UPDATE) | 필수 (5,340건 INSERT) |
| 복잡도 | 낮음 | 중간 | 높음 |
| 일관성 관리 | 수동 동기화 | 수동 동기화 | 자동 (VIEW) |

## 미결정 사항

### 1. synonyms 테이블과의 관계

현재 synonyms 테이블은 이미 opinion-aware:
```
synonyms.fide_author = 'SHERGOLD & LAURIE'
synonyms.fide_year = '1997'
```

이것을 새 opinions 테이블에 통합할 것인가, 별도로 유지할 것인가?

- **통합**: opinion_type='synonymy'로 opinions에 넣고, synonyms는 레거시로 유지
- **별도 유지**: synonyms는 그대로, opinions는 placement/validity만 담당
- **권장**: 1차에서는 별도 유지. synonyms의 fide 패턴이 잘 작동하고 있으므로 건드리지 않음

### 2. Canonical vs Overlay

- **Canonical DB에 넣는 경우**: 문헌 기반 의견은 불변 데이터 → canonical이 자연스러움
- **Overlay DB에 넣는 경우**: 사용자가 직접 추가하는 의견은 overlay
- **권장**: opinions 테이블을 canonical에 생성하되, 사용자 의견은 `overlay.taxonomic_opinions`에 같은 스키마로 별도 생성. UI에서 merge하여 표시.

### 3. 초기 데이터 범위

56개 Uncertain Family 전부에 대해 기본 opinion을 넣을 것인가?

- **최소**: Eurekiidae 등 몇 개만 시범 입력
- **전체**: 56개 Family 전부 `(placement, Uncertain, Adrain 2011, accepted, low)` 입력
- **확장**: 5,340 전 행에 대해 기본 opinion 생성

### 4. Genus 레벨 적용

`?CERATOPYGIDAE` 같은 21개 genus에도 적용할 것인가?
이 경우 `placement_confidence = 'uncertain'`으로 표현 가능.

### 5. bibliography_id 연결

현재 bibliography 테이블에 Adrain(2011)은 없고 Fortey 논문 일부만 존재.
opinions에 bibliography_id를 넣으려면 해당 문헌이 bibliography에 있어야 함.
→ `provenance_id`로 대체하거나, bibliography에 누락 문헌을 추가하거나.

### 6. 백오피스와의 관계

데이터 큐레이션 기능으로서:
- 문헌을 검색/추가
- 해당 문헌의 의견을 taxon에 연결
- 수용 여부(is_accepted) 변경 시 parent_id 자동 동기화

이 워크플로우를 어떤 형태로 제공할 것인가? (웹 UI, CLI, MCP 도구)

## 제안하는 진행 순서

1. **방안 A로 시작** — 가장 위험이 적고 기존 호환성 유지
2. **Eurekiidae 1건으로 PoC** — 테이블 생성, 데이터 2-3건 입력, API/UI 확인
3. **56개 Uncertain Family로 확장** — 기본 opinion 일괄 생성
4. **필요에 따라 방안 B로 발전** — provenance 컬럼 추가는 나중에 결정
5. **synonyms 통합은 별도 Phase** — 기존 fide 데이터가 잘 작동하므로 급하지 않음
