# Phase 46 Step 2: Dynamic MCP Tool Loading from .scoda Packages

**날짜:** 2026-02-14
**Phase:** 46 Step 2
**상태:** 완료

## 목표

MCP 서버의 14개 하드코딩 도구 중 7개 도메인 도구를 `.scoda` 패키지 내 `mcp_tools.json`에서 동적 로드하도록 전환. 이를 통해 패키지마다 다른 MCP 도구를 제공할 수 있는 구조 확립.

## 설계

### Query Types

| `query_type` | 동작 | 용도 |
|-------------|------|------|
| `single` | SQL 직접 실행 (SELECT only, 파라미터 바인딩) | 단순 검색/목록 |
| `named_query` | `ui_queries` 테이블 named query 실행 | SQL 중복 방지 |
| `composite` | manifest detail view 기반 복합 실행 (Step 1 로직 재사용) | 복합 detail |

### Built-in vs Dynamic

**Built-in (항상 제공, 7개):**
- `execute_named_query`, `list_available_queries`
- `get_metadata` (generic: artifact_metadata만), `get_provenance`
- `get_annotations`, `add_annotation`, `delete_annotation`

**Dynamic (mcp_tools.json에서 로드, Trilobase: 7개):**
- `get_taxonomy_tree` (named_query)
- `search_genera` (single)
- `get_genus_detail` (composite)
- `get_rank_detail` (composite)
- `get_family_genera` (named_query)
- `get_genera_by_country` (named_query)
- `get_genera_by_formation` (single)

### 보안

- `_validate_sql()`: SELECT/WITH로 시작 필수 + INSERT/UPDATE/DELETE/DROP/ALTER/CREATE/REPLACE/ATTACH/DETACH/PRAGMA/VACUUM/REINDEX 금지
- 파라미터 바인딩 필수 (`:param`)

## 변경 파일

### `scoda_desktop/scoda_package.py`

- `ScodaPackage.mcp_tools` property: ZIP 내 `mcp_tools.json` 읽기 (없으면 None)
- `ScodaPackage.create()`: `mcp_tools_path` 파라미터 추가 → ZIP에 포함
- `PackageRegistry.get_mcp_tools(name)`: 패키지의 mcp_tools 반환
- 모듈 레벨 `get_mcp_tools()`: active package 또는 legacy _scoda_pkg 경유

### `scoda_desktop/mcp_server.py` (주요 리팩터)

- `_FORBIDDEN_SQL` regex + `_validate_sql()`: SQL 인젝션 방지
- `_execute_named_query_internal(conn, ...)`: conn 기반 내부 헬퍼 (중복 제거)
- `_execute_composite_for_mcp(conn, view_name, entity_id)`: manifest 기반 복합 쿼리
- `_execute_dynamic_tool(tool_def, arguments)`: query_type별 분기 실행
- `_get_builtin_tools()`: 7개 built-in Tool 정의
- `_get_dynamic_tools()` / `_get_dynamic_tool_defs()`: mcp_tools.json에서 로드
- `_get_legacy_domain_tools()`: 7개 레거시 하드코딩 도구 (fallback)
- `list_tools()`: builtin + dynamic (없으면 legacy fallback)
- `call_tool()`: builtin → dynamic → legacy 디스패치 체인
- `get_metadata()`: generic 전환 (artifact_metadata만, 도메인 통계 제거)
- `execute_named_query()`: 내부 헬퍼 `_execute_named_query_internal()` 위임

### `data/mcp_tools_trilobase.json` (신규)

7개 도메인 MCP 도구 정의 (format_version: 1.0)

### `scripts/create_scoda.py`

- `--mcp-tools` CLI 인자 추가 (기본: `data/mcp_tools_trilobase.json`)
- `ScodaPackage.create()` 호출 시 `mcp_tools_path` 전달
- 검증 출력에 MCP tools 정보 추가

### `tests/conftest.py`

- `mcp_tools_data` fixture: 테스트용 JSON (3개 도구: single/named_query/composite)
- `scoda_with_mcp_tools` fixture: mcp_tools.json 포함 .scoda 생성

### `tests/test_runtime.py` — `TestDynamicMcpTools` (24개)

- ScodaPackage mcp_tools property (3개)
- SQL validation (6개)
- Dynamic tool execution (6개: single, named_query, named_query+params, composite, defaults, unknown)
- Built-in/dynamic/legacy tools (4개)
- Registry/module-level get_mcp_tools (3개)
- get_metadata generic (1개)
- test_validate_sql_non_select_rejected (1개 추가)

### `tests/test_mcp.py`

- `test_get_metadata`: statistics 검증 제거, generic metadata 검증으로 변경
- `test_get_genera_by_formation`: metadata.statistics 의존 제거

## Backward Compatibility

- `mcp_tools.json` 없으면 기존 14개 하드코딩 도구 그대로 제공 (legacy fallback)
- 레거시 도메인 함수 (build_tree, search_genera 등) 이 단계에서 삭제 안 함
- Step 3에서 레거시 도메인 함수 및 fallback 제거 예정

## 테스트

```
pytest tests/ — 278개 전부 통과 (254 기존 + 24 신규)
```

| 파일 | 테스트 수 | 상태 |
|------|---------|------|
| `tests/test_runtime.py` | 142개 | 통과 |
| `tests/test_trilobase.py` | 117개 | 통과 |
| `tests/test_mcp.py` | 16개 | 통과 |
| `tests/test_mcp_basic.py` | 1개 | 통과 |
| `tests/conftest.py` | 2 fixtures 추가 | - |
| **합계** | **278개** | **전부 통과** |

## 다음 단계

Phase 46 Step 3: 레거시 도메인 함수 제거 + legacy fallback 삭제
