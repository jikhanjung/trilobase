# 087 — SPELLING_OF Opinion Type + Agnostida Restructure + Temporal Code Fill

**날짜:** 2026-02-22

## 작업 내용

### 1. SPELLING_OF Opinion Type 추가

- `taxonomic_opinions` CHECK 제약조건에 `SPELLING_OF` 추가 (테이블 재구축)
- Placeholder 엔트리 2건 생성:
  - Dokimocephalidae (id=5342): `SPELLING_OF` → Dokimokephalidae (id=134)
  - Chengkouaspidae (id=5343): `SPELLING_OF` → Chengkouaspididae (id=36)
- `is_placeholder=1`, `parent_id=NULL`, `genera_count=0`
- 스크립트: `scripts/add_spelling_of_opinions.py` (idempotent, `--dry-run`)

### 2. Agnostida Opinion 재구조화

사용자 분석에 따른 구조 변경:
- **핵심 인사이트**: Agnostida families는 항상 Agnostida에 속함 (논란 없음). 논란은 Agnostida 자체의 Trilobita 귀속 여부
- Family-level PLACED_IN opinion 10건 삭제 (불필요)
- Order-level opinion 2건 추가:
  - JA2002: Agnostida `PLACED_IN` Trilobita (`is_accepted=0`)
  - A2011: Agnostida `PLACED_IN` NULL = excluded (`is_accepted=1`)
- 트리거가 자동으로 Agnostida `parent_id=NULL` 설정
- 스크립트: `scripts/restructure_agnostida_opinions.py` (idempotent, `--dry-run`)

### 3. T-3a: Temporal Code 자동 채우기

85건 valid genus의 temporal_code가 NULL이었으나, 84건은 raw_entry에서 추출 가능:
- 표준 패턴: `; UCAM.` (대부분)
- 엣지 케이스: `INDET. LCAM.`, `?MDEV.`, `UCAM,`, `LCAM [replacement name...]`
- 1건 (Dignagnostus)만 원본에 코드 없음 — 정상 skip
- 스크립트: `scripts/fill_temporal_codes.py` (idempotent, `--dry-run`)

## 결과

| 항목 | 변경 전 | 변경 후 |
|------|---------|---------|
| taxonomic_opinions | 12 | 6 (PLACED_IN 4 + SPELLING_OF 2) |
| taxonomic_ranks | 5,338 | 5,340 (placeholder +2) |
| temporal_code NULL (valid) | 85 | 1 (Dignagnostus) |
| 테스트 | 92 | 100 |

## 신규/수정 파일

- `scripts/add_spelling_of_opinions.py` — 신규
- `scripts/restructure_agnostida_opinions.py` — 신규
- `scripts/fill_temporal_codes.py` — 신규
- `tests/conftest.py` — CHECK에 SPELLING_OF 추가
- `tests/test_trilobase.py` — TestSpellingOfOpinions(4) + TestAgnostidaOrder 수정 + TestTemporalCodeFill(3)
- `db/trilobase.db` — 마이그레이션 적용
