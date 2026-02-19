# Phase 46 계획: Runtime Purification — 도메인 코드 완전 분리

**날짜**: 2026-02-14
**선행 작업**: Phase 45 (디렉토리 구조 정리)

## 배경

Phase 45에서 `scoda_desktop/` 패키지를 물리적으로 분리했으나, 내부 코드에
Trilobase 도메인 전용 로직이 대량 잔존. 런타임이 특정 `.scoda` 패키지에
종속되어 있어 **범용 SCODA 뷰어**로서 기능하지 못함.

### 현황 진단

| 파일 | Generic | Domain | 비고 |
|------|---------|--------|------|
| `gui.py` | 100% | 0% | 이미 깨끗 |
| `serve.py` | 98% | 2% | 문자열 2곳 |
| `static/js/app.js` | 95% | 5% | fallback 텍스트만 |
| `static/css/style.css` | 100% | 0% | 이미 깨끗 |
| `templates/index.html` | 90% | 10% | placeholder 텍스트 |
| **`app.py`** | **40%** | **60%** | legacy 엔드포인트 15개 |
| **`mcp_server.py`** | **20%** | **80%** | domain 함수/도구 11개 |
| **`scoda_package.py`** | **75%** | **25%** | hardcoded fallback |

### 문제의 핵심

1. **app.py**: manifest-driven generic API가 이미 있지만, legacy 엔드포인트
   (`/api/genus/<id>`, `/api/tree` 등 15개)가 `taxonomic_ranks`, `synonyms`,
   `bibliography`, `pc.*` 테이블을 직접 쿼리

2. **mcp_server.py**: 14개 MCP 도구 중 11개가 Trilobase 전용. `search_genera`,
   `get_genus_detail`, `get_taxonomy_tree` 등이 특정 테이블/컬럼 하드코딩

3. **scoda_package.py**: `_resolve_paths()`에 `'trilobase.scoda'`, `'trilobase.db'`
   하드코딩. `create()` 메서드에 Trilobase 저자 하드코딩

## 목표

`scoda_desktop/` 패키지가 **어떤 `.scoda` 패키지든** 동일하게 서빙할 수 있도록
모든 도메인 전용 코드를 제거하거나 데이터 기반(manifest/query/mcp_tools)으로 전환.

---

## Step 1: Generic Composite Detail Endpoint

### 문제

현재 legacy detail 엔드포인트(`/api/genus/<id>` 등)는 **여러 쿼리를 조합**하여
복합 JSON을 반환. 예를 들어 `/api/genus/<id>` 는:
- genus 기본 정보 (taxonomic_ranks)
- 상위 계층 (parent walk)
- 동의어 목록 (synonyms)
- 지층 목록 (genus_formations + pc.formations)
- 산지 목록 (genus_locations + pc.geographic_regions)
- ICS 매핑 (pc.temporal_ics_mapping + pc.ics_chronostrat)

기존 generic `/api/detail/<query>` 는 **단일 쿼리의 첫 행**만 반환하므로
이런 복합 결과를 대체할 수 없음.

### 해결: Composite Detail Definition

`ui_manifest`의 detail view에 `source_query` + `sub_queries` 정의를 추가:

```json
{
  "genus_detail": {
    "type": "detail",
    "source_query": "genus_detail",
    "source_param": "genus_id",
    "sub_queries": {
      "synonyms": {"query": "genus_synonyms", "param": "genus_id"},
      "formations": {"query": "genus_formations", "param": "genus_id"},
      "locations": {"query": "genus_locations", "param": "genus_id"}
    },
    "sections": [ ... ]
  }
}
```

새 generic 엔드포인트:

```
GET /api/composite/<view_name>?id=<entity_id>
```

동작:
1. `ui_manifest`에서 `<view_name>` detail view 정의를 읽음
2. `source_query` 실행 → 메인 결과 (단일 행)
3. `sub_queries` 각각 실행 → 결과를 키별로 병합
4. 조합된 복합 JSON 반환

이렇게 하면 **어떤 `.scoda` 패키지든** manifest에 detail view를 정의하면
런타임이 복합 데이터를 자동 조립.

### 작업 항목

1. `app.py`에 `/api/composite/<view_name>` 엔드포인트 추가 (~40줄)
2. `ui_manifest`의 detail view 정의 확장:
   - `source` (legacy URL) → `source_query` + `source_param` + `sub_queries`
3. 기존 7개 detail view manifest 업데이트:
   - `genus_detail`, `rank_detail`, `formation_detail`, `country_detail`,
     `region_detail`, `bibliography_detail`, `chronostrat_detail`
4. 부족한 named query 추가 (현재 8개 → 필요 ~20개):
   - `rank_children`, `genus_hierarchy`, `genus_ics_mapping`
   - `country_regions`, `country_genera`, `region_genera`
   - `formation_genera`, `bibliography_genera`, `chronostrat_children`,
     `chronostrat_genera`, `chronostrat_mappings`
5. SPA 프론트엔드 수정: detail view의 `source` URL → `/api/composite/<view>`
   - `spa/app.js`: `renderDetailFromManifest()` 수정
   - `scoda_desktop/static/js/app.js`: 동일 수정
6. 테스트 추가: composite endpoint 검증

### 관련 named query 목록

| Query Name | 용도 | SQL 개요 | 현재 존재 |
|-----------|------|---------|----------|
| `genus_detail` | genus 기본 정보 | `SELECT tr.*, parent.name ...` | O |
| `genus_synonyms` | genus의 동의어 | `SELECT s.* FROM synonyms s WHERE ...` | O |
| `genus_formations` | genus의 지층 | `SELECT f.* FROM genus_formations JOIN pc.formations ...` | O |
| `genus_locations` | genus의 산지 | `SELECT ... FROM genus_locations JOIN pc.geographic_regions ...` | O |
| `genus_ics_mapping` | genus의 ICS 매핑 | `SELECT ... FROM pc.temporal_ics_mapping ... WHERE temporal_code = :code` | X (추가) |
| `rank_detail` | rank 기본 정보 | `SELECT tr.*, parent.name ...` | O |
| `rank_children` | rank의 하위 분류 | `SELECT id, name, rank, genera_count FROM taxonomic_ranks WHERE parent_id = :rank_id` | X (추가) |
| `country_detail` | country 기본 | `SELECT ... FROM pc.geographic_regions WHERE id = :id` | X (추가) |
| `country_regions` | country의 하위 지역 | `SELECT ... FROM pc.geographic_regions WHERE parent_id = :id` | X (추가) |
| `country_genera` | country의 genera | `SELECT ... FROM genus_locations JOIN taxonomic_ranks ...` | X (추가) |
| `region_detail` | region 기본 | `SELECT ... FROM pc.geographic_regions WHERE id = :id` | X (추가) |
| `region_genera` | region의 genera | `SELECT ... FROM genus_locations JOIN taxonomic_ranks WHERE region_id = :id` | X (추가) |
| `formation_detail` | formation 기본 | `SELECT ... FROM pc.formations WHERE id = :id` | X (추가) |
| `formation_genera` | formation의 genera | `SELECT ... FROM genus_formations JOIN taxonomic_ranks ...` | X (추가) |
| `bibliography_detail` | bibliography 기본 | `SELECT ... FROM bibliography WHERE id = :id` | X (추가) |
| `bibliography_genera` | bibliography와 관련된 genera | `SELECT ... FROM taxonomic_ranks WHERE author LIKE ...` | X (추가) |
| `chronostrat_detail` | ICS unit 기본 | `SELECT ... FROM pc.ics_chronostrat WHERE id = :id` | X (추가) |
| `chronostrat_children` | ICS unit 하위 | `SELECT ... FROM pc.ics_chronostrat WHERE parent_id = :id` | X (추가) |
| `chronostrat_genera` | ICS 관련 genera | `SELECT ... FROM pc.temporal_ics_mapping JOIN taxonomic_ranks ...` | X (추가) |
| `chronostrat_mappings` | ICS-temporal code 매핑 | `SELECT ... FROM pc.temporal_ics_mapping WHERE ics_id = :id` | X (추가) |

---

## Step 2: Dynamic MCP Tool Loading from `.scoda` Packages

### 설계: `mcp_tools.json`

`.scoda` ZIP 아카이브에 `mcp_tools.json` 파일을 포함:

```
package.scoda (ZIP)
├── manifest.json
├── data.db
├── mcp_tools.json        ← NEW
└── assets/
```

### `mcp_tools.json` 포맷

```json
{
  "format_version": "1.0",
  "tools": [
    {
      "name": "search_genera",
      "description": "Search for trilobite genera by name pattern.",
      "input_schema": {
        "type": "object",
        "properties": {
          "name_pattern": {
            "type": "string",
            "description": "SQL LIKE pattern (e.g., '%ites')"
          },
          "valid_only": {
            "type": "boolean",
            "default": false
          },
          "limit": {
            "type": "integer",
            "default": 50
          }
        },
        "required": ["name_pattern"]
      },
      "query_type": "single",
      "sql": "SELECT id, name, author, year, is_valid, family FROM taxonomic_ranks WHERE rank = 'Genus' AND name LIKE :name_pattern AND (:valid_only = 0 OR is_valid = 1) ORDER BY name LIMIT :limit"
    },
    {
      "name": "get_genus_detail",
      "description": "Get full evidence pack for a trilobite genus.",
      "input_schema": {
        "type": "object",
        "properties": {
          "genus_id": {"type": "integer", "description": "Genus ID"}
        },
        "required": ["genus_id"]
      },
      "query_type": "composite",
      "queries": {
        "genus": {"named_query": "genus_detail", "single_row": true},
        "synonyms": {"named_query": "genus_synonyms"},
        "formations": {"named_query": "genus_formations"},
        "locations": {"named_query": "genus_locations"},
        "ics_mapping": {"named_query": "genus_ics_mapping"}
      },
      "param_mapping": {"genus_id": "genus_id"}
    }
  ]
}
```

### Tool Types

| `query_type` | 동작 | 용도 |
|-------------|------|------|
| `single` | SQL 직접 실행, 전체 결과 반환 | 단순 검색/목록 |
| `named_query` | `ui_queries`에 정의된 named query 실행 | SQL 중복 방지 |
| `composite` | 여러 named query를 실행하여 키별로 조합 | 복합 detail |

### 런타임 등록 흐름

```
1. PackageRegistry.scan()
   └─ 각 .scoda에서 mcp_tools.json 읽기 → registry에 저장

2. MCP Server list_tools()
   ├─ Built-in tools (5개, 항상 존재):
   │   execute_named_query, list_available_queries,
   │   get_metadata, get_provenance,
   │   get/add/delete_annotation
   └─ Dynamic tools (패키지별):
       mcp_tools.json에 정의된 도구들

3. MCP Server call_tool(name, args)
   ├─ Built-in → 기존 핸들러
   └─ Dynamic → query_type에 따라:
       ├─ single: SQL 직접 실행
       ├─ named_query: execute_named_query() 위임
       └─ composite: 다중 named query 실행 + 결과 조합
```

### Tool 네이밍

패키지명 prefix로 충돌 방지:
- `trilobase.search_genera`
- `trilobase.get_genus_detail`
- `paleocore.list_countries`

단, 패키지가 하나만 로드된 경우 prefix 없이도 사용 가능 (alias).

### 보안

- **SELECT만 허용**: runtime이 SQL 파싱하여 SELECT 이외 구문 거부
- **Overlay DB 접근 불가**: dynamic tool의 SQL은 canonical + dependency DB만 접근
- **파라미터 바인딩 필수**: named parameter (`:param`) 사용 강제, 문자열 보간 금지

### 작업 항목

1. `scoda_package.py`:
   - `ScodaPackage`에 `mcp_tools` property 추가 (ZIP에서 `mcp_tools.json` 읽기)
   - `PackageRegistry`에 `get_mcp_tools()` 메서드 추가
   - `ScodaPackage.create()`에 `mcp_tools_path` 파라미터 추가
2. `mcp_server.py`:
   - `list_tools()`: registry에서 dynamic tools 로드 → built-in + dynamic 병합
   - `call_tool()`: dynamic tool dispatch 로직 추가
   - `_execute_dynamic_tool()` 신규: query_type별 실행
3. `scripts/create_scoda.py`:
   - `mcp_tools.json` 파일 생성 + `.scoda`에 포함
4. `data/mcp_tools_trilobase.json` 신규:
   - Trilobase 전용 MCP 도구 정의 (11개)
5. `data/mcp_tools_paleocore.json` 신규:
   - PaleoCore 전용 MCP 도구 정의 (필요 시)
6. 테스트: dynamic tool 등록/실행 검증

---

## Step 3: Legacy 코드 제거

Step 1, 2가 완료되면 legacy 코드를 제거.

### app.py 제거 대상 (15개 엔드포인트, ~820줄)

| 엔드포인트 | 대체 수단 | 비고 |
|-----------|----------|------|
| `GET /api/tree` | named query `taxonomy_tree` | SPA fallback only |
| `GET /api/family/<id>/genera` | named query `family_genera` | SPA fallback only |
| `GET /api/rank/<id>` | `/api/composite/rank_detail?id=` | composite detail |
| `GET /api/genus/<id>` | `/api/composite/genus_detail?id=` | composite detail |
| `GET /api/country/<id>` | `/api/composite/country_detail?id=` | composite detail |
| `GET /api/region/<id>` | `/api/composite/region_detail?id=` | composite detail |
| `GET /api/chronostrat/<id>` | `/api/composite/chronostrat_detail?id=` | composite detail |
| `GET /api/formation/<id>` | `/api/composite/formation_detail?id=` | composite detail |
| `GET /api/bibliography/<id>` | `/api/composite/bibliography_detail?id=` | composite detail |
| `GET /api/metadata` | named query or built-in generic | 통계는 패키지별 다름 |
| `GET /api/paleocore/status` | 삭제 | Trilobase 전용 디버깅 |
| `build_tree()` 함수 | 삭제 | `/api/tree` 용 |
| `VALID_ENTITY_TYPES` 상수 | DB에서 동적 로드 | 하드코딩 제거 |

### mcp_server.py 제거 대상 (11개 도구, ~450줄)

| 도구 | 대체 수단 |
|------|----------|
| `get_taxonomy_tree` | dynamic tool (composite) |
| `get_rank_detail` | dynamic tool (composite) |
| `get_family_genera` | dynamic tool (named_query) |
| `get_genus_detail` | dynamic tool (composite) |
| `search_genera` | dynamic tool (single) |
| `get_genera_by_country` | dynamic tool (single) |
| `get_genera_by_formation` | dynamic tool (single) |
| `get_metadata` | built-in generic (artifact_metadata 기반) |
| `build_tree()` 함수 | 삭제 |
| `search_genera()` 함수 | 삭제 |
| `build_genus_evidence_pack()` 함수 | 삭제 |
| `get_metadata()` 함수 | generic으로 대체 |
| `get_genera_by_country()` 함수 | 삭제 |
| `get_genera_by_formation()` 함수 | 삭제 |

### scoda_package.py 정리

| 위치 | 변경 |
|------|------|
| `create()` L234 | `"authors": ["Jell, P.A.", ...]` → DB metadata에서 읽기 |
| `PackageRegistry.scan()` L294 | `['trilobase.db', 'paleocore.db']` → 모든 `.db` 파일 스캔 |
| `PackageRegistry.scan()` L306-308 | `if 'trilobase' in ... and 'paleocore' in ...` → dependency manifest 기반 |
| `_resolve_paths()` L526-547 | `'trilobase.scoda'` 등 → CLI `--package` 인자 또는 첫 번째 발견 패키지 |
| `_resolve_paleocore()` L498-508 | `'paleocore.scoda'` → dependency 기반 자동 탐색 |

### SPA 수정

| 파일 | 변경 |
|------|------|
| `spa/app.js` | detail view `source` 참조를 `/api/composite/<view>` 로 전환 |
| `scoda_desktop/static/js/app.js` | 동일 |
| `spa/app.js` | `/api/tree`, `/api/family/.../genera` fallback 코드 제거 |
| `scoda_desktop/static/js/app.js` | 동일 |

### 문서/문자열 정리 (LOW priority)

| 파일 | 변경 |
|------|------|
| `app.py` L1-3 | docstring `"Trilobase"` → `"SCODA Desktop"` |
| `mcp_server.py` L469 | `Server("trilobase")` → `Server("scoda-desktop")` |
| `mcp_server.py` L711,727,735 | `"trilobase"` → `"scoda-desktop"` |
| `serve.py` L3,70 | `"Trilobase"` → `"SCODA Desktop"` |
| `static/js/app.js` L1-3 | `"Trilobase"` → `"SCODA Desktop"` |
| `templates/index.html` L49,54,83 | placeholder 텍스트를 generic으로 |

---

## Step 4: 테스트 갱신

### 신규 테스트

1. **Composite detail endpoint**: 7개 detail view 각각에 대해 composite 결과 검증
2. **Dynamic MCP tool loading**: mcp_tools.json 로드 → 도구 등록 → 실행 → 결과 검증
3. **Unknown package**: mcp_tools.json 없는 .scoda 패키지 → 기본 도구만 제공 확인
4. **Security**: SELECT 이외 SQL 거부 확인

### 기존 테스트 수정

- `tests/test_runtime.py`: legacy 엔드포인트 테스트 → composite 엔드포인트 테스트로 전환
- `tests/test_trilobase.py`: legacy 엔드포인트 사용하는 테스트 수정
- `tests/test_mcp.py`: dynamic tool 호출로 전환
- `tests/conftest.py`: ui_manifest fixture에 sub_queries 추가

---

## 실행 순서

| Step | 내용 | 예상 난이도 |
|------|------|-----------|
| **Step 1** | Generic composite detail endpoint | 중 |
| **Step 2** | Dynamic MCP tool loading | 상 |
| **Step 3** | Legacy 코드 제거 | 중 |
| **Step 4** | 테스트 갱신 | 중 |

Step 1과 Step 2는 독립적으로 진행 가능. Step 3은 Step 1, 2 완료 후에만 가능.

## 검증 방법

1. `pytest tests/` — 전체 통과
2. `python -m scoda_desktop.app --package trilobase` — generic API만으로 정상 동작
3. `python -m scoda_desktop.app --package paleocore` — PaleoCore도 동일하게 동작
4. MCP dynamic tool 호출 — trilobase 전용 도구가 .scoda에서 로드되어 정상 실행
5. `scoda_desktop/` 내부에 `taxonomic_ranks`, `synonyms`, `bibliography` 등 도메인 테이블명 grep → 0건
