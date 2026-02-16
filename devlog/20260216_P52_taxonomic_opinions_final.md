# P52: Taxonomic Opinions — 최종 설계 문서

**작성일:** 2026-02-16
**유형:** Plan (최종판)
**상태:** 확정 대기
**선행 문서:** P50 (설계 방안), P51 (리뷰)
**장기 비전:** P53 (assertion-centric 모델) — 이 문서의 Phase 3 이후 도달점
**구현 브랜치:** `feature/taxonomic-opinions` (main 안정화 후 시작)

---

## 1. 전제: 현재 상태 안정화 우선

Taxonomic Opinions는 데이터 모델의 근본을 건드리는 변화다.
현재 구현(Phase 46, FastAPI, MCP 통합, UID 100%)이 **충분히 안정적이고 유용하다**는
확인이 먼저 이루어져야 한다.

확인 항목:
- .scoda 패키지 빌드 → 실행 → 데이터 탐색이 매끄러운가
- MCP 서버를 통한 자연어 쿼리가 정상 작동하는가
- 외부 사용자가 README/문서만 보고 시작할 수 있는가
- 229개 테스트가 안정적으로 통과하는가

**안정화가 확인된 후**, `feature/taxonomic-opinions` 브랜치에서 작업을 시작한다.
main은 현재 상태로 유지.

---

## 2. 문제 정의

### 2.1 현재 상태: 모든 행이 하나의 암묵적 opinion

`taxonomic_ranks`의 모든 행은 하나의 분류학적 의견을 암묵적으로 표현한다.

**Opinion인 필드:**

| 필드 | 의미 | 현재 근거 |
|------|------|----------|
| `parent_id` | "이 taxon은 X에 속한다" (배치) | Family+: Adrain 2011, Genus: Jell & Adrain 2002 |
| `is_valid` | "이 이름은 유효/무효하다" (유효성) | Jell & Adrain 2002 |
| `synonyms` 행 | "A는 B의 동의어다" (동의어) | `fide_author/fide_year`로 근거 명시 |

**Opinion이 아닌 필드 (사실/관찰):**
- `author`, `year` — 최초 기재자 (누가 처음 명명했는가)
- `type_species`, `formation`, `location`, `temporal_code` — 기재 시점의 관찰
- `raw_entry` — 원본 텍스트

### 2.2 한계

1. **행 단위 provenance 없음** — "이 parent_id는 어떤 문헌을 따른 것인가?"에 답할 수 없음
2. **bibliography ↔ taxonomy 링크 없음** — 2,130개 참고문헌과 5,340개 taxon 사이에 FK 없음
3. **대안적 견해 저장 불가** — `parent_id`가 하나뿐이라 복수 의견 표현 불가

### 2.3 규모

| 대상 | 수량 | 설명 |
|------|------|------|
| "Uncertain" Order 소속 Family | 56개 | 전체 191개의 29%, Order 배치 미결 |
| `?FAMILY` 불확실 배치 genus | 21개 | Family 배치에 `?` 표시 |
| INDET (완전 미정) genus | 25개 | Family 배치 자체 불가 |
| parent_id NULL genus | 342개 | Family 필드 자체가 없음 (대부분 무효) |

---

## 3. 중심 사례: Eurekiidae

### 3.1 현재 DB 구조

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

9개 genus 전부 유효, 전부 Upper Cambrian, 동의어 없음.

### 3.2 표현해야 할 의견들

**질문: "Eurekiidae는 어떤 Order에 속하는가?"**

| # | 의견 | 근거 | parent_id |
|---|------|------|-----------|
| 1 | Order 미정 (incertae sedis) | Adrain, 2011 | 144 (Uncertain) |
| 2 | Asaphida 소속 | Fortey, 1990 (예시) | 115 (Asaphida) |
| 3 | Ptychopariida 계통 | 다른 저자 (예시) | 99 (Aulacopleurida) |

의견 1만 DB에 존재. 의견 2, 3을 추가할 구조가 없음.

### 3.3 기타 실제 사례

**Bronteus/Goldius/Scutellum — 동의어 체인:**
```
Brontes → (preocc.) → Goldius → (replacement) → Goldfussia
Bronteus → (j.o.s.) → Goldius, (j.s.s.) → Scutellum (fide RICHTER & RICHTER, 1926)
```
같은 속에 대해 이름 변경 이력 + 동의어가 복잡하게 얽힌 경우.

**Metagnostus — 복수 fide:**
```
출처: "originates from Scandinavia" (fide FORTEY, 1980)
동의어: j.s.s. of Arthrorhachis (fide SHERGOLD et al., 1990)
```
하나의 genus에 대해 서로 다른 저자의 서로 다른 주장.

---

## 4. 결정 사항

P50 방안 A/B/C 비교 및 P51 리뷰를 거쳐 **방안 A'**로 확정.

### 4.1 채택: 방안 A' (Option A + Integrity Safeguards)

기존 `taxonomic_ranks`는 변경하지 않고, `taxonomic_opinions` 테이블을 추가.
P51 리뷰의 무결성 보강 4가지를 포함.

**기각된 방안:**
- **방안 B** (컬럼 추가): PaleoCore 스키마 불일치, .scoda 재생성 필요 — 현 단계에서 과도
- **방안 C** (완전 분리): 5,340건 마이그레이션, 전 쿼리 변경 — 과도

### 4.2 핵심 설계 원칙 (P51에서 채택)

> **tree structure는 선택된 assertion의 materialized result다.**
> truth를 tree에 하드코딩하지 말 것.

즉:
- `taxonomic_ranks.parent_id` = 현재 수용된 배치의 캐시
- `taxonomic_opinions` = 모든 주장의 기록 (accepted 포함)
- trigger로 동기화하여 일관성 보장

---

## 5. 스키마

### 5.1 taxonomic_opinions 테이블

```sql
CREATE TABLE taxonomic_opinions (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    taxon_id            INTEGER NOT NULL REFERENCES taxonomic_ranks(id),
    opinion_type        TEXT NOT NULL
                        CHECK(opinion_type IN ('PLACED_IN', 'VALID_AS', 'SYNONYM_OF')),

    -- 대상 taxon (PLACED_IN: 상위 taxon, SYNONYM_OF: senior taxon)
    related_taxon_id    INTEGER REFERENCES taxonomic_ranks(id),

    -- 유효성 (VALID_AS용)
    proposed_valid      INTEGER,  -- 1=valid, 0=invalid

    -- 근거 문헌
    bibliography_id     INTEGER REFERENCES bibliography(id),

    -- 저자의 주장 상태 vs 큐레이터 확신도 (분리)
    assertion_status    TEXT DEFAULT 'asserted'
                        CHECK(assertion_status IN (
                            'asserted',         -- 저자가 명확히 주장
                            'incertae_sedis',   -- 저자가 불확실하다고 명시
                            'questionable',     -- 저자가 ?로 표시
                            'indet'             -- 저자가 판단 불가로 명시
                        )),
    curation_confidence TEXT DEFAULT 'high'
                        CHECK(curation_confidence IN ('high', 'medium', 'low')),

    -- 수용 상태
    is_accepted         INTEGER DEFAULT 0,

    notes               TEXT,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**P50 대비 변경점:**
- `opinion_type`: free text → CHECK enum (`PLACED_IN`, `VALID_AS`, `SYNONYM_OF`)
- `proposed_parent_id` → `related_taxon_id` (PLACED_IN과 SYNONYM_OF에 공용)
- `confidence` 단일 필드 → `assertion_status` + `curation_confidence` 분리
- `bibliography_id`만 유지, `provenance_id`/`author`/`year` 제거 (근거는 bibliography에)
- `provenance`는 SCODA 패키지 레벨 메타데이터로 별도 유지

### 5.2 인덱스

```sql
-- 기본 조회
CREATE INDEX idx_opinions_taxon ON taxonomic_opinions(taxon_id);
CREATE INDEX idx_opinions_type ON taxonomic_opinions(opinion_type);

-- 핵심: taxon당 opinion_type당 accepted는 최대 1건
CREATE UNIQUE INDEX idx_unique_accepted_opinion
ON taxonomic_opinions(taxon_id, opinion_type)
WHERE is_accepted = 1;
```

### 5.3 Trigger — parent_id 자동 동기화

```sql
-- INSERT: 새 accepted placement opinion → parent_id 업데이트
CREATE TRIGGER trg_sync_parent_insert
AFTER INSERT ON taxonomic_opinions
WHEN NEW.opinion_type = 'PLACED_IN' AND NEW.is_accepted = 1
BEGIN
    -- 이전 accepted를 해제
    UPDATE taxonomic_opinions
    SET is_accepted = 0
    WHERE taxon_id = NEW.taxon_id
      AND opinion_type = 'PLACED_IN'
      AND is_accepted = 1
      AND id != NEW.id;
    -- parent_id 동기화
    UPDATE taxonomic_ranks
    SET parent_id = NEW.related_taxon_id
    WHERE id = NEW.taxon_id;
END;

-- UPDATE: 기존 opinion의 is_accepted 변경 시
CREATE TRIGGER trg_sync_parent_update
AFTER UPDATE OF is_accepted ON taxonomic_opinions
WHEN NEW.opinion_type = 'PLACED_IN' AND NEW.is_accepted = 1 AND OLD.is_accepted = 0
BEGIN
    UPDATE taxonomic_opinions
    SET is_accepted = 0
    WHERE taxon_id = NEW.taxon_id
      AND opinion_type = 'PLACED_IN'
      AND is_accepted = 1
      AND id != NEW.id;
    UPDATE taxonomic_ranks
    SET parent_id = NEW.related_taxon_id
    WHERE id = NEW.taxon_id;
END;
```

### 5.4 Placeholder 표시

```sql
ALTER TABLE taxonomic_ranks ADD COLUMN is_placeholder INTEGER DEFAULT 0;

UPDATE taxonomic_ranks SET is_placeholder = 1
WHERE name IN ('Uncertain', 'UNCERTAIN', 'INDET')
  AND rank IN ('Order', 'Superfamily', 'Family');
```

이렇게 하면 트리 쿼리, 통계, UI에서 placeholder 노드를 명확히 구분 가능.

### 5.5 bibliography 보강

opinions에서 `bibliography_id`로 참조하려면, 현재 누락된 주요 문헌을 추가해야 함.

```sql
-- Adrain 2011 (현재 provenance에만 있고 bibliography에 없음)
INSERT INTO bibliography (authors, year, title, journal, volume, pages, reference_type)
VALUES ('ADRAIN, J.M.', 2011,
        'Class Trilobita Walch, 1771. In: Zhang, Z.-Q. (Ed.) Animal biodiversity: An outline of higher-level classification',
        'Zootaxa', '3148', '104-109', 'article');

-- Jell & Adrain 2002 (이미 bibliography에 존재하는지 확인 후)
```

---

## 6. Eurekiidae에 적용한 예시

### 6.1 데이터

```sql
-- Adrain 2011: incertae sedis (현재 수용)
INSERT INTO taxonomic_opinions
    (taxon_id, opinion_type, related_taxon_id, bibliography_id,
     assertion_status, curation_confidence, is_accepted)
VALUES
    (164, 'PLACED_IN', 144, <adrain_2011_id>,
     'incertae_sedis', 'high', 1);
-- trigger가 taxonomic_ranks.parent_id = 144 유지를 보장

-- Fortey 1990: Asaphida (대안)
INSERT INTO taxonomic_opinions
    (taxon_id, opinion_type, related_taxon_id, bibliography_id,
     assertion_status, curation_confidence, is_accepted)
VALUES
    (164, 'PLACED_IN', 115, <fortey_1990_id>,
     'asserted', 'medium', 0);
```

### 6.2 UI 표시

```
Eurekiidae (Family, Hupé 1953)
  현재 배치: Order 미정 — incertae sedis (Adrain, 2011)
  대안적 견해:
    ● Asaphida 소속 (Fortey, 1990)
```

### 6.3 수용 의견 변경 시

만약 Fortey의 의견을 수용하기로 결정하면:

```sql
UPDATE taxonomic_opinions SET is_accepted = 1
WHERE taxon_id = 164 AND related_taxon_id = 115;
-- trigger가 자동으로:
--   1) 기존 accepted (Adrain) → is_accepted = 0
--   2) taxonomic_ranks.parent_id = 115 (Asaphida)로 변경
```

기존 트리 쿼리는 parent_id만 보므로 자동 반영.

---

## 7. 결정된 사항 요약

| 항목 | 결정 | 근거 |
|------|------|------|
| 방안 | A' (별도 테이블 + 무결성 보강) | 기존 호환 100%, 최소 위험 |
| opinion_type | CHECK enum 3종 | free text drift 방지 (P51 §3) |
| 일관성 보장 | partial unique index + trigger | 수동 동기화 방지 (P51 §2.1, §2.2) |
| 불확실성 표현 | assertion_status / curation_confidence 분리 | 개념적 불확실성 ≠ 큐레이션 불확실성 (P51 §5) |
| Placeholder | is_placeholder 플래그 | 트리 쿼리 예외 제거 (P51 §6) |
| 근거 참조 | bibliography_id 단일 FK | 삼중 참조 방지 (P51 §4) |
| Synonym | Phase 1에서 분리 유지 | fide 패턴이 이미 작동 (P51 §7) |
| Canonical vs Overlay | Canonical에 생성 (문헌 기반), Overlay 확장은 추후 | SCODA 불변성 원칙 |

---

## 8. 미결정 사항 (구현 시 확정)

1. **초기 데이터 범위** — Eurekiidae만 PoC? 56개 Uncertain Family 전부? 5,340 전 행?
2. **Genus 레벨 적용** — `?FAMILY` 21개, INDET 25개에도 opinion 생성?
3. **API/MCP 인터페이스** — opinions CRUD API, MCP 도구 범위
4. **SPA UI** — opinions 표시 위치, 편집 가능 여부
5. **Predicate 모델 전환 시점** — Phase 2에서 `PLACED_IN` 등을 subject-predicate-object로 확장?
6. **백오피스 연계** — 문헌 검색 → opinion 연결 → 수용 변경 워크플로우

---

## 9. 구현 로드맵

### Phase 1: PoC (feature/taxonomic-opinions 브랜치)

1. `taxonomic_opinions` 테이블 생성 (스키마 §5.1)
2. Partial unique index + trigger (§5.2, §5.3)
3. `is_placeholder` 컬럼 추가 (§5.4)
4. bibliography에 Adrain 2011 추가 (§5.5)
5. Eurekiidae에 2-3건 opinion 입력 (§6.1)
6. API: `GET /api/opinions/{taxon_id}`, composite detail에 opinions 섹션 추가
7. SPA: taxon detail에 "Taxonomic Opinions" 표시
8. 테스트: opinion CRUD, trigger 동기화, partial unique 검증

### Phase 2: 확장 (PoC 검증 후)

1. 56개 Uncertain Family 전부에 기본 opinion 일괄 생성
2. `?FAMILY` genus 21개에 opinion 생성 (assertion_status='questionable')
3. MCP 도구: `get_taxon_opinions`, `add_opinion`
4. 수용 의견 변경 UI (백오피스 기능)

### Phase 3: 심화 (필요 시) → P53 전환 검토

1. Synonym → SYNONYM_OF opinion 마이그레이션 검토
2. Subject-predicate-object 모델로 확장 검토 (→ P53 assertion 모델)
3. Classification Profile 도입 검토 (→ P53 §5)
4. Overlay DB에 사용자 opinion 지원
5. parent_id를 derived view로 전환 가능성 평가 (→ P53 §6)
