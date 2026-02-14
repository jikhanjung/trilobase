# Phase 46 Step 3: Legacy Code Removal

**날짜:** 2026-02-14
**브랜치:** `main`

## 목표

Step 1 (Generic Composite Detail Endpoint)과 Step 2 (Dynamic MCP Tool Loading)로
모든 도메인 전용 기능이 manifest/query/mcp_tools.json 기반으로 대체됨.
`scoda_desktop/`에 잔존하는 legacy 도메인 코드를 제거하여 범용 SCODA 뷰어로 완성.

## 변경 내역

### 1. `scoda_desktop/mcp_server.py` — Legacy 함수/도구 제거

- Legacy 도메인 함수 7개 삭제: `build_tree()`, `search_genera()`, `build_genus_evidence_pack()`,
  `get_metadata()`, `get_genera_by_country()`, `get_genera_by_formation()`, `get_rank_detail()`, `get_family_genera()`
- `_get_legacy_domain_tools()` 삭제
- `call_tool()` 내 legacy fallback 블록 삭제
- `list_tools()`: fallback 제거 → dynamic tools 없으면 builtin만 반환
- `get_metadata` handler를 `call_tool()` 내 inline 처리 (artifact_metadata 직접 쿼리)
- `Server("trilobase")` → `Server("scoda-desktop")`
- 문자열/로그: "Trilobase" → "SCODA Desktop"
- ~957줄 → ~550줄 (~400줄 삭제)

### 2. `scoda_desktop/app.py` — Legacy 엔드포인트 제거

- Docstring: "Trilobase Web Interface" → "SCODA Desktop Web Interface"
- `get_paleocore_db_path` import 제거 (미사용)
- `build_tree()` 함수 삭제
- 11개 legacy 엔드포인트 삭제:
  - `/api/tree`, `/api/family/<id>/genera`, `/api/rank/<id>`, `/api/genus/<id>`
  - `/api/metadata`, `/api/country/<id>`, `/api/region/<id>`
  - `/api/chronostrat/<id>`, `/api/formation/<id>`, `/api/bibliography/<id>`
  - `/api/paleocore/status`
- ~750줄 삭제

### 3. `scoda_desktop/scoda_package.py` — Hardcoded 문자열 정리

- `create()`: `'trilobase'` → `'unknown'`, `'Trilobase'` → `'Unknown'`
- `create()`: 하드코딩된 authors `["Jell, P.A.", "Adrain, J.M."]` → `[]`
- `PackageRegistry.scan()`: `['trilobase.db', 'paleocore.db']` → glob `*.db` (overlay 제외)
- 하드코딩된 `trilobase → paleocore` dependency 와이어링 삭제
- `_resolve_paths()`: `'trilobase.scoda'` → glob `*.scoda`/`*.db` 기반 자동 탐색

### 4. SPA 파일 — Legacy API fallback 제거

- `spa/app.js`: `/api/tree` 및 `/api/family/` fallback → `throw new Error()`
- `scoda_desktop/static/js/app.js`: 동일

### 5. 테스트 업데이트

**test_trilobase.py — 삭제된 테스트 클래스 (9개, ~66 테스트):**
- TestApiTree (7), TestApiFamilyGenera (8), TestApiRankDetail (8)
- TestApiGenusDetail (14), TestApiCountryDetail (5), TestApiRegionDetail (4)
- TestApiChronostratDetail (13), TestGenusDetailICSMapping (4), TestApiPaleocoreStatus (3)

**test_trilobase.py — 수정된 테스트:**
- `test_combined_scoda_flask_api`: `/api/paleocore/status` → `/api/manifest`
- `test_combined_scoda_genus_detail`: `/api/genus/<id>` → `/api/composite/genus_detail?id=<id>`

**test_runtime.py — 삭제:**
- TestApiMetadata (5 테스트)
- `test_no_mcp_tools_fallback_to_legacy` (1 테스트)
- `test_get_metadata_generic` (1 테스트)
- CORS 테스트: `/api/tree` → `/api/manifest`

**test_mcp.py — 재작성:**
- Legacy 도구 테스트 8개 삭제 (get_taxonomy_tree, search_genera 등)
- `test_list_tools`: 14개 → 7개 builtin 도구 검증
- `test_annotations_lifecycle`: `search_genera` → `execute_named_query` 기반
- `test_error_handling_invalid_genus` 삭제
- 16개 → 7개 테스트

**test_mcp_basic.py — 업데이트:**
- Expected tools: 14개 → 7개 builtin
- Legacy 도구 호출 테스트 제거

## 테스트 결과

| 파일 | 테스트 수 | 상태 |
|------|---------|------|
| `tests/test_runtime.py` | 135 | 통과 |
| `tests/test_trilobase.py` | 51 | 통과 |
| `tests/test_mcp.py` | 7 | 통과 |
| `tests/test_mcp_basic.py` | 1 | 통과 |
| **합계** | **196** | **전부 통과** |

## 삭제 규모 요약

- `mcp_server.py`: ~400줄 삭제
- `app.py`: ~750줄 삭제
- `scoda_package.py`: ~20줄 변경
- `spa/app.js` + `static/js/app.js`: 각 ~6줄 변경
- 테스트: ~82개 삭제, 수정/재작성 ~10개
- **총 ~1,200줄 legacy 코드 제거**

## 의의

SCODA Desktop이 완전한 범용 뷰어로 전환 완료. 모든 도메인 특화 기능(삼엽충 분류학)은
.scoda 패키지 내부의 manifest, named queries, mcp_tools.json으로만 정의됨.
런타임 코드에는 어떤 도메인 전용 로직도 존재하지 않음.
