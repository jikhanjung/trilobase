# Phase 36 계획: trilobase.scoda + paleocore.scoda 조합 배포 테스트

**날짜:** 2026-02-13
**상태:** 📋 계획

## 배경

Phase 35에서 trilobase.scoda와 paleocore.scoda 패키지를 모두 생성 완료했으나, 두 .scoda 파일만으로 Flask 앱이 정상 동작하는지 통합 테스트가 없다. 현재 테스트는 모두 `_set_paths_for_testing()`으로 직접 .db 경로를 지정하므로, 실제 .scoda 자동 탐색 (`_resolve_paleocore()`)이나 .scoda에서 추출한 DB로 3-DB ATTACH가 되는 시나리오가 검증되지 않는 상태.

## 테스트 대상 시나리오

1. **`_resolve_paleocore()`**: .scoda 자동 발견 vs .db 폴백
2. **Combined .scoda deployment**: 두 .scoda에서 추출한 DB로 `get_db()` → 3-DB ATTACH
3. **Cross-DB JOIN**: genus_locations ↔ pc.countries 쿼리
4. **Flask API 통합**: `/api/paleocore/status` 엔드포인트 (기존 테스트 없음)
5. **`get_scoda_info()`**: 두 패키지 모두 scoda 소스일 때 정보 확인

## 수정 작업

### 1. TestCombinedScodaDeployment 클래스 (~6개 테스트)

`test_app.py`에 TestPaleocoreScoda 뒤에 추가.

| 테스트 | 내용 |
|---|---|
| `test_resolve_paleocore_finds_scoda` | `_resolve_paleocore(dir)` → .scoda 발견 시 `_paleocore_pkg` 세팅 |
| `test_resolve_paleocore_falls_back_to_db` | .scoda 없을 때 .db 경로 폴백 |
| `test_combined_scoda_get_db` | 두 .scoda에서 추출한 DB로 3-DB ATTACH + Cross-DB JOIN |
| `test_combined_scoda_flask_api` | Flask client로 `/api/paleocore/status` 호출, attached=True |
| `test_combined_scoda_info` | `get_scoda_info()` → source_type='scoda', paleocore_source_type='scoda' |
| `test_combined_scoda_genus_detail` | genus detail API가 pc.formations/pc.countries 정상 JOIN |

### 2. TestApiPaleocoreStatus 클래스 (~3개 테스트)

기존 client fixture 사용 (직접 .db 경로 기반). `/api/paleocore/status` 엔드포인트 기본 검증.

| 테스트 | 내용 |
|---|---|
| `test_paleocore_status_200` | 200 응답 |
| `test_paleocore_status_attached` | attached=True, tables dict 존재 |
| `test_paleocore_status_cross_db_join` | cross_db_join_test.status='OK' |

## 수정 파일

| 파일 | 변경 |
|---|---|
| `test_app.py` | TestCombinedScodaDeployment (~6개) + TestApiPaleocoreStatus (~3개) 추가 |

## 검증

```bash
pytest test_app.py -v        # 기존 152 + 신규 ~9 = ~161개
pytest test_mcp.py test_mcp_basic.py -v  # 17개 (변경 없음)
```
