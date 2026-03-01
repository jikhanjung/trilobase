# P77: Canonical DB 파일명에 버전 포함

**날짜**: 2026-03-01
**상태**: ✅ 완료

## 목적

`db/trilobase.db` → `db/trilobase-{version}.db` 패턴으로 변경하여, 파일명만으로 DB 버전을 식별할 수 있게 한다. assertion DB(`trilobase_assertion-{version}.db`)와 동일한 패턴.

## 설계

### DB 파일 탐색 헬퍼 (`scripts/db_path.py` 신규)

```python
def find_trilobase_db() -> str:
    """db/trilobase-*.db glob → 최신 버전 경로 반환."""
```

- `db/trilobase-*.db` glob으로 탐색
- 여러 버전이 있으면 semver 기준 최신 반환
- 0개면 에러

### 버전 범프 시 동작 (`bump_version.py`)

- 기존 파일을 **복사**(copy)하여 새 버전 파일 생성
- 과거 버전 파일은 `db/` 디렉토리에 보존
- 예: `db/trilobase-0.2.6.db` → (copy) → `db/trilobase-0.2.7.db`

### .scoda 패키지 영향

- 없음. 패키지 내부에서는 `data.db`로 저장되므로 외부 파일명 무관.

## 수정 대상

### 신규 생성
- `scripts/db_path.py` — DB 탐색 헬퍼

### 활성 스크립트 (DB_PATH → find_trilobase_db())
| 파일 | 비고 |
|------|------|
| `scripts/add_scoda_ui_tables.py` | DEFAULT DB |
| `scripts/add_scoda_manifest.py` | DEFAULT DB |
| `scripts/add_scoda_tables.py` | DEFAULT DB |
| `scripts/create_scoda.py` | DEFAULT_DB |
| `scripts/create_assertion_db.py` | SRC_DB |
| `scripts/validate_assertion_db.py` | SRC_DB |
| `scripts/link_bibliography.py` | DB_PATH |
| `scripts/bump_version.py` | DB_PATHS dict + rename→copy 로직 |

### 테스트
- `tests/test_trilobase.py` — 5개 클래스의 DB_PATH

### 문서
- CLAUDE.md, HANDOFF.md — 파일명 패턴 갱신

### 레거시 스크립트
- 변경하지 않음 (이미 실행 완료된 마이그레이션 스크립트)

## 초기 파일 변환

```bash
# 현재 trilobase.db (v0.2.6) → 버전 포함 파일명으로 복사
cp db/trilobase.db db/trilobase-0.2.6.db
# 원본 삭제 (git rm)
git rm db/trilobase.db
```

## 검증

1. `find_trilobase_db()` → `db/trilobase-0.2.6.db` 반환
2. `python scripts/add_scoda_ui_tables.py` — 자동 탐색 성공
3. `python scripts/create_scoda.py --no-assertion` — 빌드 성공
4. `python scripts/bump_version.py trilobase 0.2.7 --dry-run` — 복사 미리보기
5. `pytest tests/` — 전체 통과
