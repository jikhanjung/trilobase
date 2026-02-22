# P66: SPELLING_OF Opinion Type for Orthographic Variants

**날짜:** 2026-02-22

## Context

이전 작업(086)에서 Group A 철자 변형 중복을 해소하며 Dokimocephalidae(id=210), Chengkouaspidae(id=205)를 삭제했다. 이 이름들은 각각 Dokimokephalidae(id=134), Chengkouaspididae(id=36)의 **orthographic variant**이므로, placeholder 엔트리 + `SPELLING_OF` opinion으로 정식 이름과 연결하여 검색 가능성을 보존한다.

(Shirakiellidae id=196은 동일 철자 빈 중복이므로 대상 아님)

---

## Step 1: 마이그레이션 스크립트

**파일**: `scripts/add_spelling_of_opinions.py` (신규, `--dry-run`, idempotent)

### 1-1. CHECK 제약조건 변경

SQLite는 ALTER TABLE로 CHECK 변경 불가 → 테이블 재생성:

1. `taxonomic_opinions_new` 생성 — CHECK에 `'SPELLING_OF'` 추가
2. 기존 12건 데이터 복사
3. 기존 테이블 DROP
4. RENAME → `taxonomic_opinions`
5. 인덱스 3개 재생성 (`idx_opinions_taxon`, `idx_opinions_type`, `idx_unique_accepted_opinion`)
6. 트리거 4개 재생성 (PLACED_IN 전용, 변경 없음)

idempotent: CHECK에 이미 SPELLING_OF 포함되어 있으면 skip.

### 1-2. Placeholder 엔트리 재삽입

```sql
INSERT INTO taxonomic_ranks (name, rank, parent_id, genera_count, is_placeholder,
    uid, uid_method, uid_confidence, notes)
VALUES ('Dokimocephalidae', 'Family', NULL, 0, 1,
    'scoda:taxon:family:Dokimocephalidae', 'name', 'high',
    'Orthographic variant of Dokimokephalidae. Jell & Adrain (2002) spelling.');

INSERT INTO taxonomic_ranks (name, rank, parent_id, genera_count, is_placeholder,
    uid, uid_method, uid_confidence, notes)
VALUES ('Chengkouaspidae', 'Family', NULL, 0, 1,
    'scoda:taxon:family:Chengkouaspidae', 'name', 'high',
    'Orthographic variant of Chengkouaspididae. Jell & Adrain (2002) spelling.');
```

- `parent_id = NULL`: 트리에 표시하지 않음 (검색으로만 접근)
- `is_placeholder = 1`, `genera_count = 0`

### 1-3. SPELLING_OF Opinion 삽입

```sql
INSERT INTO taxonomic_opinions
    (taxon_id, opinion_type, related_taxon_id, bibliography_id,
     assertion_status, curation_confidence, is_accepted, notes)
VALUES
    (<dokimocephalidae_id>, 'SPELLING_OF', 134, NULL,
     'asserted', 'high', 1,
     'Dokimocephalidae is an orthographic variant of Dokimokephalidae (C→K). Jell & Adrain (2002) used Dokimocephalidae; Adrain (2011) corrected to Dokimokephalidae.');

INSERT INTO taxonomic_opinions
    (<chengkouaspidae_id>, 'SPELLING_OF', 36, NULL,
     'asserted', 'high', 1,
     'Chengkouaspidae is an orthographic variant of Chengkouaspididae (-idae→-ididae). Jell & Adrain (2002) used Chengkouaspidae; Adrain (2011) corrected to Chengkouaspididae.');
```

- `curation_confidence='high'`: 철자 차이가 명확
- 기존 트리거 영향 없음 (PLACED_IN 전용)

---

## Step 2: conftest.py 수정

`tests/conftest.py`의 `taxonomic_opinions` CREATE TABLE CHECK에 `'SPELLING_OF'` 추가:

```
CHECK(opinion_type IN ('PLACED_IN', 'VALID_AS', 'SYNONYM_OF', 'SPELLING_OF'))
```

---

## Step 3: 테스트 추가

`tests/test_trilobase.py`에 `TestSpellingOfOpinions` 클래스 (4개):

- `test_spelling_of_type_allowed`: test_db에서 SPELLING_OF INSERT 성공
- `test_dokimocephalidae_placeholder`: production DB에서 placeholder 존재, is_placeholder=1
- `test_dokimocephalidae_opinion`: production DB에서 SPELLING_OF opinion → Dokimokephalidae(134)
- `test_chengkouaspidae_opinion`: production DB에서 SPELLING_OF opinion → Chengkouaspididae(36)

---

## 수정 파일

| 파일 | 작업 |
|------|------|
| `scripts/add_spelling_of_opinions.py` | **신규** |
| `db/trilobase.db` | 수정 |
| `tests/conftest.py` | 수정 — CHECK에 SPELLING_OF 추가 |
| `tests/test_trilobase.py` | 수정 — 테스트 4개 추가 |

---

## 검증

```bash
python scripts/add_spelling_of_opinions.py --dry-run
python scripts/add_spelling_of_opinions.py
sqlite3 db/trilobase.db "SELECT * FROM taxonomic_opinions WHERE opinion_type = 'SPELLING_OF';"
sqlite3 db/trilobase.db "SELECT id, name, is_placeholder FROM taxonomic_ranks WHERE name IN ('Dokimocephalidae', 'Chengkouaspidae');"
pytest tests/test_trilobase.py -v
```
