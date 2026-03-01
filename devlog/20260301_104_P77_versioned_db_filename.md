# 104: P77 — 모든 Canonical DB 파일명에 버전 포함

**날짜**: 2026-03-01
**상태**: ✅ 완료

## 목적

모든 canonical DB를 `{name}-{version}.db` 패턴으로 통일하여, 파일명만으로 DB 버전을 식별할 수 있게 한다.

- `db/trilobase.db` → `db/trilobase-0.2.6.db`
- `db/paleocore.db` → `db/paleocore-0.1.1.db`
- `dist/assertion_test/trilobase_assertion-*.db` → `db/trilobase-assertion-0.1.0.db`

## 작업 내용

### 1. `scripts/db_path.py` 신규 생성

- `find_trilobase_db()` — `db/trilobase-*.db` glob → semver 최신 반환
- `find_assertion_db()` — `db/trilobase-assertion-*.db` glob → semver 최신 반환
- `find_paleocore_db()` — `db/paleocore-*.db` glob → semver 최신 반환
- 공통 로직 `_find_latest()` 추출, 0개이면 `FileNotFoundError`
- `_SCRIPT_DIR` 기준 상대 경로 → 어디서 실행해도 동작

### 2. 활성 스크립트 8개 DB_PATH 교체

| 파일 | 변경 전 | 변경 후 |
|------|---------|---------|
| `scripts/add_scoda_ui_tables.py` | `os.path.join(..., 'trilobase.db')` | `find_trilobase_db()` |
| `scripts/add_scoda_manifest.py` | 〃 | 〃 |
| `scripts/add_scoda_tables.py` | 〃 | 〃 |
| `scripts/create_scoda.py` | `DEFAULT_DB = os.path.join(...)` | `DEFAULT_DB = find_trilobase_db()` |
| `scripts/create_assertion_db.py` | `SRC_DB = ROOT / "db" / "trilobase.db"` | `SRC_DB = Path(find_trilobase_db())` |
| `scripts/validate_assertion_db.py` | 〃 | 〃 |
| `scripts/link_bibliography.py` | `os.path.join(..., 'trilobase.db')` | `find_trilobase_db()` |
| `scripts/bump_version.py` | `DB_PATHS dict` 하드코딩 | `find_trilobase_db()` + copy 로직 |

### 3. 테스트 DB_PATH 교체 (5개소)

`tests/test_trilobase.py` 내 5개 클래스의 `DB_PATH = 'db/trilobase.db'` → `DB_PATH = find_trilobase_db()`.

`sys.path.insert(0, scripts/)` 추가하여 `db_path` 모듈 임포트.

- `TestGroupAFix`
- `TestAgnostidaOrder`
- `TestSpellingOfOpinions`
- `TestTemporalCodeFill`
- `TestCountryIdConsistency`

### 4. DB 파일 전환

```bash
cp db/trilobase.db db/trilobase-0.2.6.db
git rm -f db/trilobase.db

cp db/paleocore.db db/paleocore-0.1.1.db
git rm -f db/paleocore.db

mv db/trilobase_assertion-0.1.0.db db/trilobase-assertion-0.1.0.db
```

### 5. `bump_version.py` copy 로직

trilobase/paleocore 공통으로 버전 범프 시 `shutil.copy2()`로 복사하여 새 버전 파일 생성. 과거 버전 파일 보존.

```
$ python scripts/bump_version.py trilobase 0.2.7 --dry-run
  Copy: trilobase-0.2.6.db → trilobase-0.2.7.db

$ python scripts/bump_version.py paleocore 0.1.2 --dry-run
  Copy: paleocore-0.1.1.db → paleocore-0.1.2.db
```

### 6. Assertion DB를 `db/` 디렉토리로 이동 + 파일명 통일

- `dist/assertion_test/trilobase_assertion-*.db` → `db/trilobase-assertion-{ver}.db`
  - underscore → hyphen: 다른 DB(`trilobase-{ver}`, `paleocore-{ver}`)와 네이밍 통일
- `create_assertion_db.py`: `DST_DIR` → `ROOT / "db"`, unversioned copy 로직 제거
- `validate_assertion_db.py`: `DST_DIR` → `ROOT / "db"`, glob 패턴 갱신
- `create_assertion_scoda.py`: `DEFAULT_DB` → `find_assertion_db()`, `.scoda` 출력은 `dist/`에 유지

### 7. Paleocore DB 버전 파일명 적용

- `db/paleocore.db` → `db/paleocore-0.1.1.db`
- `create_paleocore_scoda.py`: `DEFAULT_DB` → `find_paleocore_db()`
- `create_paleocore.py`: `SOURCE_DB` → `find_trilobase_db()`
- `bump_version.py`: paleocore도 copy 로직 적용
- `tests/test_trilobase.py`: `PC_DB_PATH` → `find_paleocore_db()`

### 8. CI workflow 정리

- `release.yml`, `manual-release.yml`:
  - 별도 "Build assertion DB" step 제거 (`create_scoda.py`가 이미 assertion까지 빌드)
  - release artifact: `dist/*.scoda` + `dist/*.manifest.json`만 포함

### 9. 문서 갱신

- `CLAUDE.md`: 파일 구조 `{name}-{ver}.db` 패턴 통일
- `HANDOFF.md`: 모든 DB 경로, P77 섹션, 릴리스 방법, SQLite ATTACH 예시 갱신

## .scoda 패키지 영향

없음. 패키지 내부에서는 `data.db`로 저장되므로 외부 파일명 무관.

## 검증

| 항목 | 결과 |
|------|------|
| `find_trilobase_db()` | `db/trilobase-0.2.6.db` ✅ |
| `find_assertion_db()` | `db/trilobase-assertion-0.1.0.db` ✅ |
| `find_paleocore_db()` | `db/paleocore-0.1.1.db` ✅ |
| `bump_version.py trilobase --dry-run` | copy 정상 ✅ |
| `bump_version.py paleocore --dry-run` | copy 정상 ✅ |
| `validate_assertion_db.py` | 15/15 checks passed ✅ |
| `pytest tests/` | 112/112 passed ✅ |

## 수정 파일 목록

- `scripts/db_path.py` (신규)
- `scripts/add_scoda_ui_tables.py`
- `scripts/add_scoda_manifest.py`
- `scripts/add_scoda_tables.py`
- `scripts/create_scoda.py`
- `scripts/create_assertion_db.py`
- `scripts/validate_assertion_db.py`
- `scripts/create_assertion_scoda.py`
- `scripts/create_paleocore.py`
- `scripts/create_paleocore_scoda.py`
- `scripts/link_bibliography.py`
- `scripts/bump_version.py`
- `tests/test_trilobase.py`
- `.github/workflows/release.yml`
- `.github/workflows/manual-release.yml`
- `db/trilobase-0.2.6.db` (← trilobase.db)
- `db/trilobase-assertion-0.1.0.db` (← dist/assertion_test/trilobase_assertion-0.1.0.db)
- `db/paleocore-0.1.1.db` (← paleocore.db)
- `db/trilobase.db` (삭제)
- `db/paleocore.db` (삭제)
- `CLAUDE.md`
- `HANDOFF.md`
