# Phase 36: trilobase.scoda + paleocore.scoda 조합 배포 테스트

**날짜:** 2026-02-13
**상태:** ✅ 완료

## 배경

Phase 35에서 trilobase.scoda와 paleocore.scoda 패키지를 모두 생성 완료했으나, 두 .scoda 파일만으로 Flask 앱이 정상 동작하는지 통합 테스트가 없었다. 기존 테스트는 모두 `_set_paths_for_testing()`으로 직접 .db 경로를 지정하므로, 실제 .scoda 자동 탐색 (`_resolve_paleocore()`)이나 .scoda에서 추출한 DB로 3-DB ATTACH가 되는 시나리오가 검증되지 않은 상태였다.

## 수행 작업

### 1. TestCombinedScodaDeployment 클래스 (6개 테스트)

`test_app.py`에 TestGenusDetailICSMapping 뒤에 추가. 두 .scoda 패키지를 생성하여 실제 배포 시나리오를 시뮬레이션.

| 테스트 | 내용 |
|---|---|
| `test_resolve_paleocore_finds_scoda` | `_resolve_paleocore(dir)` → .scoda 발견 시 `_paleocore_pkg` 세팅 확인 |
| `test_resolve_paleocore_falls_back_to_db` | .scoda 없을 때 .db 경로 폴백 확인 |
| `test_combined_scoda_get_db` | 두 .scoda에서 추출한 DB로 3-DB ATTACH + Cross-DB JOIN 성공 |
| `test_combined_scoda_flask_api` | Flask client로 `/api/paleocore/status` 호출, attached=True |
| `test_combined_scoda_info` | `get_scoda_info()` → source_type='scoda', paleocore_source_type='scoda' |
| `test_combined_scoda_genus_detail` | genus detail API가 pc.formations/pc.geographic_regions 정상 JOIN |

### 2. TestApiPaleocoreStatus 클래스 (3개 테스트)

기존 `client` fixture 사용 (직접 .db 경로 기반). `/api/paleocore/status` 엔드포인트 기본 검증.

| 테스트 | 내용 |
|---|---|
| `test_paleocore_status_200` | 200 응답 |
| `test_paleocore_status_attached` | attached=True, tables dict 존재 |
| `test_paleocore_status_cross_db_join` | cross_db_join_test.status='OK', matched_rows > 0 |

## 테스트 구현 설계

- **`_add_scoda_metadata_to_paleocore()`**: test_db fixture의 paleocore DB에 SCODA 메타데이터 테이블 추가 (artifact_metadata, provenance, schema_descriptions)
- **`_setup_combined_scoda()`**: test_db에서 양쪽 .scoda 패키지 생성, ScodaPackage 열기, 모듈 글로벌 변수 설정
- try/finally 패턴으로 `scoda_package._reset_paths()` 보장

## 수정 파일

| 파일 | 변경 |
|---|---|
| `test_app.py` | TestCombinedScodaDeployment (6개) + TestApiPaleocoreStatus (3개) 추가 |

## 테스트 결과

```
pytest test_app.py -v        → 161 passed (기존 152 + 신규 9)
pytest test_mcp.py test_mcp_basic.py -v  → 17 passed (변경 없음)
총계: 178 passed
```
