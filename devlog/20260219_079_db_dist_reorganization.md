# DB/dist 디렉토리 재구성

**날짜:** 2026-02-19

## 개요

루트에 흩어져 있던 `.db`, `.scoda`, `*_overlay.db` 파일들을 용도별 디렉토리로 정리.

## 변경 사항

### 1. 디렉토리 구조

| 디렉토리 | 용도 | Git 추적 |
|----------|------|----------|
| `db/` | Canonical DB (trilobase.db, paleocore.db) | O (tracked) |
| `dist/` | 생성 산출물 (.scoda, *_overlay.db) | X (gitignored) |

### 2. 파일 이동

| 파일 | From | To |
|------|------|-----|
| `trilobase.db` | 루트 | `db/trilobase.db` |
| `paleocore.db` | 루트 | `db/paleocore.db` |
| `trilobase.scoda` | 루트 | `dist/trilobase.scoda` |
| `paleocore.scoda` | 루트 | `dist/paleocore.scoda` |
| `trilobase_overlay.db` | 루트 | `dist/trilobase_overlay.db` |
| `paleocore_overlay.db` | 루트 | `dist/paleocore_overlay.db` |

### 3. 스크립트 경로 갱신 (23개)

**표준 패턴** (`os.path.join` 기반) — sed 일괄 치환:
- `'..', 'trilobase.db'` → `'..', 'db', 'trilobase.db'`
- `'..', 'paleocore.db'` → `'..', 'db', 'paleocore.db'`

**비표준 패턴** — 수동 수정:

| 파일 | 변경 전 | 변경 후 |
|------|---------|---------|
| `parse_references.py` | `os.path.join(PROJECT_DIR, 'trilobase.db')` | `os.path.join(PROJECT_DIR, 'db', 'trilobase.db')` |
| `populate_taxonomic_ranks.py` | `db_path = 'trilobase.db'` | `os.path.join(os.path.dirname(__file__), '..', 'db', 'trilobase.db')` |
| `normalize_database.py` | `base_dir / 'trilobase.db'` | `base_dir / 'db' / 'trilobase.db'` |
| `normalize_families.py` | `base_path / 'trilobase.db'` | `base_path / 'db' / 'trilobase.db'` |
| `create_geographic_regions.py` | `DB_PATH = 'trilobase.db'` | `os.path.join(os.path.dirname(__file__), '..', 'db', 'trilobase.db')` |
| `create_database.py` | `base_dir / 'trilobase.db'` | `base_dir / 'db' / 'trilobase.db'` |
| `fix_synonyms.py` | `base_dir / 'trilobase.db'` | `base_dir / 'db' / 'trilobase.db'` |

### 4. .scoda 출력 경로 갱신

| 파일 | 변경 전 | 변경 후 |
|------|---------|---------|
| `create_scoda.py` | `'..', 'trilobase.scoda'` | `'..', 'dist', 'trilobase.scoda'` |
| `create_paleocore_scoda.py` | `'..', 'paleocore.scoda'` | `'..', 'dist', 'paleocore.scoda'` |

### 5. 문서 갱신

- `CLAUDE.md`: 파일 구조도에 `db/`, `dist/` 반영
- `GEMINI.md`: 동일
- `docs/HANDOFF.md`: 파일 구조도, SQLite ATTACH 예시, DB 사용법 경로 갱신

## 테스트 결과

- `pytest tests/` — 66 passed

## .gitignore

`dist/`와 `*.scoda`는 이미 gitignore 대상이었으므로 변경 불필요.
