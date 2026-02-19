# Phase 35: PaleoCore .scoda 패키지 + Dependency 반영

**날짜:** 2026-02-13
**상태:** ✅ 완료

## 작업 내용

paleocore.db를 `.scoda` 포맷으로 패키징하고, trilobase.scoda에 dependency를 선언하여 두 패키지 간 관계를 명시화.

### 1. ScodaPackage.create() 범용화

기존 `taxonomic_ranks` COUNT 하드코딩을 제거하고, 모든 데이터 테이블 합산 방식으로 변경:

```python
# 변경 전
cursor.execute("SELECT COUNT(*) as cnt FROM taxonomic_ranks")
record_count = cursor.fetchone()['cnt']

# 변경 후
scoda_meta_tables = {'artifact_metadata', 'provenance', 'schema_descriptions',
                     'ui_display_intent', 'ui_queries', 'ui_manifest'}
record_count = sum of all non-SCODA-metadata tables
```

이제 어떤 DB에서든 `.scoda` 패키지 생성 가능.

### 2. scripts/create_paleocore_scoda.py (신규)

paleocore.db → paleocore.scoda 패키징 스크립트:
- `--dry-run` 지원
- PaleoCore 전용 authors 메타데이터
- 생성 후 자동 검증 (checksum)

```bash
python scripts/create_paleocore_scoda.py --dry-run
python scripts/create_paleocore_scoda.py
# → paleocore.scoda (93 KB, 3,340 records)
```

### 3. scripts/create_scoda.py — dependency 추가

trilobase.scoda manifest에 paleocore dependency 선언:

```json
{
  "dependencies": [{
    "name": "paleocore",
    "version": "0.3.0",
    "file": "paleocore.scoda",
    "description": "Shared paleontological infrastructure (geography, stratigraphy)"
  }]
}
```

### 4. scoda_package.py — paleocore.scoda 지원

- `_paleocore_pkg` 모듈 변수 추가
- `_resolve_paleocore()` 함수: paleocore.scoda 우선 → paleocore.db 폴백
- `_set_paths_for_testing()` / `_reset_paths()`: paleocore_pkg 라이프사이클 관리
- `get_scoda_info()`: paleocore_source_type 필드 추가

### 5. scripts/create_paleocore.py — 소스 경고

trilobase.db에서 PaleoCore 테이블이 DROP된 후 실행 시:
```
Error: Source database is missing 8 required tables:
  - countries, geographic_regions, ...
Phase 34 dropped PaleoCore tables from trilobase.db.
If paleocore.db already exists, use it directly.
```

### 6. 테스트 (5개 신규)

| 테스트 | 내용 |
|---|---|
| test_create_paleocore_scoda | paleocore DB로 .scoda 생성 |
| test_paleocore_scoda_manifest | manifest 메타데이터 검증 |
| test_paleocore_scoda_record_count | SCODA 메타 테이블 제외 카운트 |
| test_trilobase_scoda_with_dependency | dependency manifest 검증 |
| test_paleocore_scoda_db_accessible | 추출 DB 쿼리 가능 검증 |

## 수정/신규 파일

| 파일 | 변경 |
|---|---|
| `scoda_package.py` | create() 범용화 + paleocore.scoda 탐색 |
| `scripts/create_paleocore_scoda.py` | **신규**: paleocore.db → paleocore.scoda |
| `scripts/create_scoda.py` | dependency metadata 추가 |
| `scripts/create_paleocore.py` | 소스 테이블 부재 경고 |
| `test_app.py` | TestPaleocoreScoda 5개 테스트 |

## 테스트 결과

```
pytest test_app.py -v         # 152 passed (기존 147 + 신규 5)
pytest test_mcp.py -v          # 16 passed
pytest test_mcp_basic.py -v    # 1 passed
합계: 169 passed
```

## 산출물

```
paleocore.scoda: 94,766 bytes (93 KB)
  Name: paleocore
  Version: 0.3.0
  Records: 3,340
  Checksum: OK
```
