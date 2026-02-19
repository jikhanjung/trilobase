# Plan: Phase 35 — PaleoCore .scoda 패키지 + Dependency 반영

**날짜:** 2026-02-13
**상태:** 계획

## 배경

Phase 31에서 paleocore.db를 생성하고, Phase 34에서 trilobase.db에서 PaleoCore 테이블 8개를 DROP했다. 이제 paleocore.db를 `.scoda` 포맷으로 패키징하고, trilobase.scoda에 dependency를 선언해야 한다.

## 현황

| 항목 | 상태 |
|---|---|
| `paleocore.db` | ✅ 존재 (14개 테이블, 3,340 데이터 + SCODA 메타) |
| `paleocore.scoda` | ❌ 아직 없음 |
| `trilobase.scoda` | 생성 가능 (create_scoda.py) — dependency 없음 |
| `ScodaPackage.create()` | ⚠️ `taxonomic_ranks` COUNT 하드코딩 |
| `create_paleocore.py` | ⚠️ trilobase.db에서 추출 (Phase 34에서 테이블 DROP됨) |
| `.scoda` 로딩 | ⚠️ paleocore.scoda 미지원 |

## 수정 작업

### 1. `ScodaPackage.create()` 범용화

**현재 문제:** `taxonomic_ranks` 테이블이 없으면 record_count 계산 실패.

```python
# 현재 (하드코딩)
cursor.execute("SELECT COUNT(*) as cnt FROM taxonomic_ranks")
record_count = cursor.fetchone()['cnt']
```

**해결:** 총 레코드 수를 모든 데이터 테이블에서 합산하는 방식 + metadata 오버라이드 지원.

```python
# 변경: 모든 non-SCODA 테이블의 합계
scoda_meta_tables = {'artifact_metadata', 'provenance', 'schema_descriptions',
                     'ui_display_intent', 'ui_queries', 'ui_manifest'}
tables = cursor.execute(
    "SELECT name FROM sqlite_master WHERE type='table'"
).fetchall()
record_count = 0
for (table_name,) in tables:
    if table_name not in scoda_meta_tables and not table_name.startswith('sqlite_'):
        count = cursor.execute(f"SELECT COUNT(*) FROM [{table_name}]").fetchone()[0]
        record_count += count
```

또는 더 간단하게: `metadata` dict로 `record_count`를 외부에서 전달 가능 (이미 `metadata` param 존재).

### 2. `scripts/create_paleocore_scoda.py` 신규

paleocore.db → paleocore.scoda 패키징 스크립트:

```bash
python scripts/create_paleocore_scoda.py              # create paleocore.scoda
python scripts/create_paleocore_scoda.py --dry-run    # preview
```

`ScodaPackage.create(paleocore_db, output, metadata={...})` 호출.

### 3. `scripts/create_scoda.py` — dependency 추가

trilobase.scoda manifest에 dependency 선언:

```json
{
  "format": "scoda",
  "format_version": "1.0",
  "name": "trilobase",
  "version": "1.0.0",
  ...
  "dependencies": [
    {
      "name": "paleocore",
      "version": "0.3.0",
      "file": "paleocore.scoda",
      "description": "Shared paleontological infrastructure (geography, stratigraphy)"
    }
  ]
}
```

### 4. `scoda_package.py` — paleocore.scoda 지원

`_resolve_paths()`에서 paleocore.scoda 탐색 추가:

```python
# 현재: paleocore.db만 탐색
_paleocore_db = os.path.join(base_dir, 'paleocore.db')

# 변경: paleocore.scoda 우선, 없으면 paleocore.db 폴백
paleocore_scoda = os.path.join(base_dir, 'paleocore.scoda')
if os.path.exists(paleocore_scoda):
    _paleocore_pkg = ScodaPackage(paleocore_scoda)
    _paleocore_db = _paleocore_pkg.db_path
else:
    _paleocore_db = os.path.join(base_dir, 'paleocore.db')
```

### 5. `scripts/create_paleocore.py` — SOURCE_DB 경고 추가

Phase 34에서 trilobase.db의 PaleoCore 테이블을 DROP했으므로, 스크립트 실행 시 소스 테이블이 없으면 안내 메시지 출력. `--source paleocore.db` 옵션으로 기존 paleocore.db에서 재생성 지원 (또는 별도 백업에서).

### 6. 테스트

- `ScodaPackage.create()` 범용 record_count 테스트
- paleocore.scoda 생성/열기/검증 테스트
- dependency manifest 테스트
- paleocore.scoda → ATTACH 경로 해석 테스트

## 수정 파일

| 파일 | 변경 |
|---|---|
| `scoda_package.py` | `create()` 범용화 + paleocore.scoda 탐색 |
| `scripts/create_paleocore_scoda.py` | 신규: paleocore.db → paleocore.scoda |
| `scripts/create_scoda.py` | dependency 정보 추가 |
| `scripts/create_paleocore.py` | 소스 테이블 부재 경고 |
| `test_app.py` | ScodaPackage + paleocore.scoda 테스트 |

## 검증

```bash
# paleocore.scoda 생성
python scripts/create_paleocore_scoda.py --dry-run
python scripts/create_paleocore_scoda.py

# trilobase.scoda 재생성 (dependency 포함)
python scripts/create_scoda.py

# 테스트
pytest test_app.py -v
pytest test_mcp.py -v
```

## 산출물

```
trilobase/
├── paleocore.scoda          # 신규: PaleoCore .scoda 패키지
├── trilobase.scoda          # 갱신: dependency 선언 포함
├── scoda_package.py         # 수정: 범용 create() + paleocore.scoda 로딩
├── scripts/
│   ├── create_paleocore_scoda.py  # 신규
│   └── create_scoda.py            # 수정
└── test_app.py              # 수정: 새 테스트 추가
```
