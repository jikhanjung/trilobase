# Phase 22: MCP Server Implementation

**작성일:** 2026-02-09
**상태:** Plan
**이전 Phase:** Phase 21 (GUI 로그 뷰어)

---

## 1. 개요

### 1.1 목적

Trilobase Flask API를 **Model Context Protocol (MCP)** 서버로 래핑하여 Claude나 다른 LLM이 자연어로 삼엽충 데이터베이스를 쿼리하고 탐색할 수 있게 합니다.

**MCP란?**
- Anthropic이 개발한 프로토콜로, LLM이 외부 데이터 소스와 도구에 접근할 수 있게 하는 표준
- Server-Client 아키텍처: MCP 서버가 도구(tools)를 제공하고, LLM 클라이언트가 이를 호출
- JSON-RPC 2.0 기반, stdio/SSE 전송 지원
- Python SDK: `mcp` 패키지 제공

**사용 예시:**
- "중국에서 발견된 삼엽충 속을 보여줘"
- "Paradoxides의 동의어를 알려줘"
- "Family Paradoxididae에 속한 속들을 나열해줘"
- "Agnostus에 메모 추가: 'Check formation data'"

### 1.2 SCODA 철학과의 일치

이 통합은 SCODA(Self-Contained Data Artifact)의 핵심 원칙을 따릅니다:

**핵심 원칙:**
- **DB is truth**: 데이터베이스가 유일한 진실의 원천
- **MCP is access**: MCP는 접근 수단일 뿐, 데이터를 변경하지 않음
- **LLM is narration**: LLM은 증거 기반 서술만 수행, 판단/정의 금지
- **Snapshots are exports**: 생성된 내러티브는 파생물

**Non-Goals (LLM이 해서는 안 되는 것):**
- ❌ 분류학적 판단이나 정의
- ❌ 자율적 의사결정이나 계획
- ❌ 데이터베이스 쓰기 (주석 제외)

### 1.3 아키텍처 비전

```
┌─────────────────┐
│   Claude/LLM    │ (자연어 쿼리)
└────────┬────────┘
         │ JSON-RPC (stdio)
         ▼
┌──────────────────────────┐
│    MCP Server            │
│  - Tool registry         │
│  - Evidence Pack builder │
│  - DB connector          │
└────────┬─────────────────┘
         │ Direct DB access
         ▼
┌──────────────────────────┐
│  SQLite Databases        │
│  - Canonical (read-only) │
│  - Overlay (read/write)  │
└──────────────────────────┘
```

**기존 시스템과의 관계:**
```
                  ┌─ SPA (Human) → REST API
[Trilobase System]┤
                  └─ MCP Server (LLM) → Direct DB
```

- Flask API는 웹 UI용으로 계속 유지
- MCP 서버는 프로그래매틱 접근용 (DB 직접 연결)
- 같은 데이터, 다른 접근 방식

---

## 2. 개념 설계

### 2.1 Evidence Pack 패턴

LLM은 raw DB 출력을 받지 않습니다. 대신 **구조화되고 경계가 명확한 Evidence Pack**을 받습니다.

**설계 원칙:**
- 증거는 충분하되 최소한으로 (sufficient but minimal)
- 모든 주장은 reference ID와 연결
- 불확실성은 데이터 레벨에서 명시적으로 인코딩

**Trilobase Evidence Pack 예시:**

```json
{
  "genus": {
    "id": 42,
    "name": "Paradoxides",
    "author": "BRONGNIART",
    "year": 1822,
    "is_valid": true,
    "family": "Paradoxididae",
    "type_species": "Paradoxides paradoxissimus",
    "raw_entry": "Paradoxides BRONGNIART, 1822..."
  },
  "synonyms": [
    {
      "junior_name": "Paradoxus",
      "type": "objective",
      "senior_taxon": "Paradoxides",
      "fide": "WHITTINGTON, 1997"
    }
  ],
  "localities": [
    {
      "country": "Czech Republic",
      "region": "Bohemia",
      "formation": "Jince Formation",
      "is_type_locality": true
    }
  ],
  "references": [
    "BRONGNIART, 1822",
    "WHITTINGTON, 1997"
  ],
  "provenance": {
    "source": "Jell & Adrain, 2002",
    "extraction_date": "2026-02-04",
    "canonical_version": "1.0.0"
  }
}
```

**주요 특징:**
- `raw_entry`: 원본 데이터 보존 (추적성)
- `fide`: 정보의 출처 명시
- `provenance`: 데이터 계보 추적
- 구조화된 관계 (synonyms, localities)

### 2.2 도구 책임 분리

**MCP 서버의 역할:**
1. **Tool Registry**: 도메인 특화 쿼리 도구 노출
2. **Execution Control**: 도구 실행은 서버가 수행
3. **Evidence Pack Construction**: DB 결과를 구조화된 입력으로 변환
4. **Context Boundary Enforcement**: 제공된 증거 외 정보 사용 방지

**LLM의 역할:**
- 사용자 의도 파악 → 적절한 도구 선택
- Evidence Pack 해석 → 자연어 서술 생성
- 출처 인용 (references 필드 사용)

**사용자의 역할:**
- 자연어 질문 제공
- LLM 생성 결과의 타당성 판단
- 필요 시 주석 추가 (Overlay DB)

---

## 3. 구현 계획

### 3.1 프로젝트 구조

```
trilobase/
├── mcp_server.py              # 새 파일: MCP 서버 메인 (500-600 lines)
├── requirements.txt            # mcp>=1.0.0 추가
├── scripts/
│   └── launch_mcp.py          # 새 파일: MCP 서버 런처 (50 lines)
└── test_mcp.py                # 새 파일: MCP 서버 테스트 (300-400 lines)
```

### 3.2 MCP 도구 정의 (14개)

#### 3.2.1 Taxonomy Exploration Tools (4개)

| 도구 이름 | 설명 | 파라미터 | 대응 API/로직 |
|---------|------|---------|--------------|
| `get_taxonomy_tree` | 전체 분류 계층 트리 조회 | - | `GET /api/tree` (app.py build_tree()) |
| `get_rank_detail` | 특정 분류 계급 상세정보 | `rank_id: int` | `GET /api/rank/<id>` |
| `get_family_genera` | Family에 속한 Genus 목록 | `family_id: int` | `GET /api/family/<id>/genera` |
| `get_genus_detail` | Genus 상세정보 (synonyms, formations, locations) | `genus_id: int` | `GET /api/genus/<id>` + Evidence Pack |

**Evidence Pack 예시:**
- `get_genus_detail` → 위 섹션 2.1의 JSON 구조 반환
- `provenance` 필드 자동 추가
- `raw_entry` 보존으로 추적성 보장

#### 3.2.2 Search & Query Tools (4개)

| 도구 이름 | 설명 | 파라미터 | 구현 |
|---------|------|---------|------|
| `search_genera` | 이름으로 Genus 검색 | `name_pattern: str`, `valid_only: bool`, `limit: int` | 신규 구현 (LIKE 쿼리) |
| `get_genera_by_country` | 특정 국가의 Genus 목록 | `country: str`, `limit: int` | 신규 (genus_locations JOIN) |
| `get_genera_by_formation` | 특정 지층의 Genus 목록 | `formation: str`, `limit: int` | 신규 (genus_formations JOIN) |
| `execute_named_query` | ui_queries 테이블의 쿼리 실행 | `query_name: str`, `params: dict` | `GET /api/queries/<name>/execute` |

#### 3.2.3 Metadata & Discovery Tools (3개)

| 도구 이름 | 설명 | 파라미터 | 대응 API |
|---------|------|---------|---------|
| `get_metadata` | 데이터베이스 메타데이터 + 통계 | - | `GET /api/metadata` |
| `get_provenance` | 데이터 출처 정보 | - | `GET /api/provenance` |
| `list_available_queries` | 사용 가능한 named query 목록 | - | `GET /api/queries` |

#### 3.2.4 Annotation Tools (3개, Overlay DB)

| 도구 이름 | 설명 | 파라미터 | 대응 API |
|---------|------|---------|---------|
| `get_annotations` | Entity의 사용자 주석 조회 | `entity_type: str`, `entity_id: int` | `GET /api/annotations/<type>/<id>` |
| `add_annotation` | 새 주석 추가 | `entity_type: str`, `entity_id: int`, `annotation_type: str`, `content: str`, `author: str?` | `POST /api/annotations` |
| `delete_annotation` | 주석 삭제 | `annotation_id: int` | `DELETE /api/annotations/<id>` |

**Annotation 특수성:**
- Overlay DB에 쓰기 (유일하게 쓰기 가능)
- SCODA 원칙: canonical 데이터 불변, 사용자 의견은 별도 레이어

### 3.3 핵심 구현 패턴

#### 3.3.1 DB 연결 (app.py 패턴 재사용)

```python
import sqlite3
import os
import sys

# DB path resolution (app.py와 동일)
if getattr(sys, 'frozen', False):
    CANONICAL_DB = os.path.join(sys._MEIPASS, 'trilobase.db')
    OVERLAY_DB = os.path.join(os.path.dirname(sys.executable), 'trilobase_overlay.db')
else:
    base_dir = os.path.dirname(__file__)
    CANONICAL_DB = os.path.join(base_dir, 'trilobase.db')
    OVERLAY_DB = os.path.join(base_dir, 'trilobase_overlay.db')

def get_db():
    """Get database connection with overlay attached."""
    conn = sqlite3.connect(CANONICAL_DB)
    conn.row_factory = sqlite3.Row
    conn.execute(f"ATTACH DATABASE '{OVERLAY_DB}' AS overlay")
    return conn
```

#### 3.3.2 Evidence Pack 빌더

```python
def build_genus_evidence_pack(genus_id: int) -> dict:
    """Build evidence pack for a genus (structured, bounded output for LLM)."""
    conn = get_db()
    cursor = conn.cursor()

    # Get genus basic info
    cursor.execute("""
        SELECT tr.*, parent.name as family_name
        FROM taxonomic_ranks tr
        LEFT JOIN taxonomic_ranks parent ON tr.parent_id = parent.id
        WHERE tr.id = ? AND tr.rank = 'Genus'
    """, (genus_id,))
    genus = cursor.fetchone()

    if not genus:
        return None

    # Get synonyms
    cursor.execute("""
        SELECT jr.name as junior_name, s.synonym_type, s.senior_taxon_name,
               s.fide_author, s.fide_year
        FROM synonyms s
        JOIN taxonomic_ranks jr ON s.junior_taxon_id = jr.id
        WHERE jr.id = ? OR s.senior_taxon_id = ?
    """, (genus_id, genus_id))
    synonyms = [dict(row) for row in cursor.fetchall()]

    # Get formations
    cursor.execute("""
        SELECT f.name, f.country, gf.is_type_locality
        FROM genus_formations gf
        JOIN formations f ON gf.formation_id = f.id
        WHERE gf.genus_id = ?
    """, (genus_id,))
    formations = [dict(row) for row in cursor.fetchall()]

    # Get locations
    cursor.execute("""
        SELECT c.name as country, gl.region, gl.is_type_locality
        FROM genus_locations gl
        JOIN countries c ON gl.country_id = c.id
        WHERE gl.genus_id = ?
    """, (genus_id,))
    locations = [dict(row) for row in cursor.fetchall()]

    # Get metadata (provenance)
    cursor.execute("SELECT value FROM artifact_metadata WHERE key = 'version'")
    version = cursor.fetchone()[0] if cursor.fetchone() else '1.0.0'

    conn.close()

    # Build Evidence Pack
    return {
        "genus": {
            "id": genus["id"],
            "name": genus["name"],
            "author": genus["author"],
            "year": genus["year"],
            "is_valid": bool(genus["is_valid"]),
            "family": genus["family_name"],
            "type_species": genus["type_species"],
            "raw_entry": genus["raw_entry"]
        },
        "synonyms": synonyms,
        "formations": formations,
        "localities": locations,
        "provenance": {
            "source": "Jell & Adrain, 2002",
            "canonical_version": version,
            "extraction_date": "2026-02-04"
        }
    }
```

#### 3.3.3 MCP 서버 구조

```python
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
import json

app = Server("trilobase")

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="get_genus_detail",
            description="Get detailed information for a specific genus including synonyms, formations, and locations. Returns an evidence pack with full provenance.",
            inputSchema={
                "type": "object",
                "properties": {
                    "genus_id": {
                        "type": "integer",
                        "description": "The ID of the genus to retrieve"
                    }
                },
                "required": ["genus_id"]
            }
        ),
        # ... 나머지 13개 도구
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls"""

    if name == "get_genus_detail":
        genus_id = arguments["genus_id"]
        evidence_pack = build_genus_evidence_pack(genus_id)

        if not evidence_pack:
            return [TextContent(
                type="text",
                text=f"Error: Genus {genus_id} not found"
            )]

        return [TextContent(
            type="text",
            text=json.dumps(evidence_pack, indent=2)
        )]

    elif name == "search_genera":
        # ... 구현
        pass

    # ... 나머지 도구 핸들러

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

### 3.4 테스트 전략

```python
"""Tests for Trilobase MCP Server"""
import pytest
import json
from mcp.client import ClientSession
from mcp.client.stdio import stdio_client

@pytest.mark.asyncio
async def test_mcp_server_list_tools():
    """Test that MCP server exposes expected tools"""
    async with stdio_client(["python", "mcp_server.py"]) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            tool_names = [tool.name for tool in tools.tools]

            assert "get_taxonomy_tree" in tool_names
            assert "get_genus_detail" in tool_names
            assert "search_genera" in tool_names
            assert len(tool_names) == 14

@pytest.mark.asyncio
async def test_search_genera():
    """Test genus search tool"""
    async with stdio_client(["python", "mcp_server.py"]) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            result = await session.call_tool(
                "search_genera",
                {"name_pattern": "Paradoxides%", "limit": 10}
            )

            content = result.content[0].text
            data = json.loads(content)

            assert len(data) > 0
            assert any(g["name"] == "Paradoxides" for g in data)

@pytest.mark.asyncio
async def test_evidence_pack_structure():
    """Test that genus detail returns proper evidence pack"""
    async with stdio_client(["python", "mcp_server.py"]) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Search for Paradoxides first
            search_result = await session.call_tool(
                "search_genera",
                {"name_pattern": "Paradoxides", "limit": 1}
            )
            genera = json.loads(search_result.content[0].text)
            genus_id = genera[0]["id"]

            # Get detail
            detail_result = await session.call_tool(
                "get_genus_detail",
                {"genus_id": genus_id}
            )
            evidence_pack = json.loads(detail_result.content[0].text)

            # Verify Evidence Pack structure
            assert "genus" in evidence_pack
            assert "synonyms" in evidence_pack
            assert "formations" in evidence_pack
            assert "localities" in evidence_pack
            assert "provenance" in evidence_pack

            # Verify provenance
            assert evidence_pack["provenance"]["source"] == "Jell & Adrain, 2002"
            assert "canonical_version" in evidence_pack["provenance"]

            # Verify raw_entry preservation
            assert evidence_pack["genus"]["raw_entry"] is not None
```

---

## 4. 구현 단계

### Step 1: 의존성 추가
```bash
echo "mcp>=1.0.0" >> requirements.txt
pip install mcp
```

### Step 2: MCP 서버 기본 구조 (mcp_server.py)
- [ ] DB 연결 로직 구현 (app.py 패턴 재사용)
- [ ] 14개 도구 정의 (`list_tools()`)
- [ ] 기본 핸들러 스켈레톤 (`call_tool()`)
- [ ] stdio 서버 실행 (`main()`)

### Step 3: 핵심 도구 구현 (우선순위 높음)
- [ ] `get_taxonomy_tree` (app.py의 build_tree() 재사용)
- [ ] `search_genera` (신규: LIKE 쿼리)
- [ ] `get_genus_detail` + Evidence Pack 빌더
- [ ] `get_metadata` (app.py api_metadata() 재사용)

### Step 4: 검색 도구 구현 (신규)
- [ ] `get_genera_by_country` (genus_locations JOIN)
- [ ] `get_genera_by_formation` (genus_formations JOIN)
- [ ] `execute_named_query` (app.py api_execute_query() 재사용)

### Step 5: Annotation 도구 구현 (Overlay DB)
- [ ] `get_annotations` (app.py api_get_annotations() 재사용)
- [ ] `add_annotation` (app.py api_create_annotation() 재사용)
- [ ] `delete_annotation` (app.py api_delete_annotation() 재사용)

### Step 6: 나머지 도구 구현
- [ ] `get_rank_detail` (app.py api_rank_detail() 재사용)
- [ ] `get_family_genera` (app.py api_family_genera() 재사용)
- [ ] `get_provenance` (app.py api_provenance() 재사용)
- [ ] `list_available_queries` (app.py api_list_queries() 재사용)

### Step 7: 테스트 작성 (test_mcp.py)
- [ ] 도구 목록 테스트 (14개 확인)
- [ ] 각 도구별 단위 테스트
- [ ] Evidence Pack 구조 검증 테스트
- [ ] Overlay DB 읽기/쓰기 테스트

### Step 8: 런처 스크립트 (scripts/launch_mcp.py)
- [ ] MCP 서버 실행 스크립트
- [ ] 에러 처리 및 로깅

### Step 9: 문서화
- [ ] `devlog/20260209_022_phase22_mcp_wrapper.md` 작성
- [ ] `docs/HANDOVER.md` 업데이트 (Phase 22 완료)
- [ ] `README.md` 업데이트 (MCP 사용법 섹션)
- [ ] Claude Desktop 설정 가이드 작성

---

## 5. 검증 계획

### 5.1 단위 테스트
```bash
pytest test_mcp.py -v
```

**검증 항목:**
- [x] 14개 도구 모두 정상 작동
- [x] DB 연결 정상 (Canonical + Overlay)
- [x] Evidence Pack 구조 유효성
- [x] Overlay DB 읽기/쓰기 정상
- [x] SQL injection 방어 (파라미터 바인딩)

### 5.2 수동 테스트 (MCP 클라이언트)
```bash
# MCP 서버 직접 실행
python mcp_server.py

# 다른 터미널에서 stdio 통신 테스트
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | python mcp_server.py
```

### 5.3 Claude Desktop 통합 테스트

**설정 파일:** `~/.config/claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "trilobase": {
      "command": "python",
      "args": ["/home/jikhanjung/projects/trilobase/mcp_server.py"],
      "cwd": "/home/jikhanjung/projects/trilobase"
    }
  }
}
```

**테스트 시나리오:**

| 자연어 쿼리 | 예상 도구 조합 | 검증 포인트 |
|-----------|--------------|-----------|
| "중국에서 발견된 삼엽충 속을 보여줘" | `get_genera_by_country("China")` | 국가 필터링 정확성 |
| "Paradoxides의 동의어를 알려줘" | `search_genera` → `get_genus_detail` | Evidence Pack 구조 |
| "Family Paradoxididae에 속한 속들을 나열해줘" | `search_genera` (family 검색) → `get_family_genera` | 계층 구조 탐색 |
| "Agnostus에 메모 추가: 'Check formation data'" | `search_genera` → `add_annotation` | Overlay DB 쓰기 |
| "이 데이터베이스의 출처는?" | `get_provenance` | 메타데이터 조회 |

**검증 기준:**
- ✅ LLM이 올바른 도구 조합 선택
- ✅ 결과에 출처 인용 포함 (Evidence Pack의 references/provenance)
- ✅ 불확실한 정보는 명시적으로 표현 ("according to...", "likely...")
- ❌ LLM이 임의로 분류학적 판단하지 않음
- ❌ 제공되지 않은 정보를 "추측"하지 않음

### 5.4 성능 테스트
- 대용량 쿼리 (1000+ genera 검색) 응답 시간 측정
- 복잡한 조인 쿼리 (formations, locations) 성능 확인
- 목표: 모든 쿼리 < 2초

---

## 6. 위험 및 완화 방안

| 위험 | 영향 | 완화 방안 |
|-----|------|----------|
| MCP SDK API 변경 | High | requirements.txt에 버전 고정 (`mcp==1.x.x`) |
| 대용량 결과 처리 | Medium | 모든 검색 도구에 `limit` 파라미터 (기본값 50-100) |
| SQL injection | High | 모든 쿼리에 파라미터 바인딩 사용 (app.py 패턴 유지) |
| Overlay DB 동시성 | Low | SQLite WAL 모드 활성화 고려 (향후) |
| PyInstaller 호환성 | Medium | `sys._MEIPASS` 패턴 재사용 (app.py에서 검증됨) |
| LLM이 판단/정의 시도 | Medium | Evidence Pack에 provenance/fide 명시, 시스템 프롬프트로 제약 |

---

## 7. 향후 확장 계획 (Out of Scope)

- [ ] MCP 서버를 PyInstaller 번들에 포함 (Phase 23)
- [ ] SSE 전송 모드 지원 (현재는 stdio만)
- [ ] 캐싱 레이어 (자주 쓰이는 쿼리 결과 캐싱)
- [ ] 지질시대 필터링 도구 (`get_genera_by_period`)
- [ ] Bibliography 검색 도구 (`search_references`)
- [ ] 통계 집계 도구 (`get_statistics`)
- [ ] Web UI에 MCP 쿼리 히스토리 표시

---

## 8. 성공 기준

- [x] `mcp_server.py` 구현 완료 (14개 도구)
- [x] `test_mcp.py` 모든 테스트 통과
- [x] Claude Desktop에서 자연어 쿼리 정상 작동
- [x] Evidence Pack 구조 일관성 유지
- [x] 기존 Flask API 및 GUI 정상 작동 (영향 없음)
- [x] 문서 3종 세트 완료 (devlog, HANDOVER, README)

---

## 9. 참고 자료

- **MCP 프로토콜**: https://modelcontextprotocol.io/
- **MCP Python SDK**: https://github.com/modelcontextprotocol/python-sdk
- **Claude Desktop MCP 설정**: https://modelcontextprotocol.io/clients/claude-desktop
- **Trilobase SCODA 설계**: `docs/SCODA_CONCEPT.md`
- **기존 API 문서**: `docs/HANDOVER.md` (Line 52-63)
- **ChatGPT 개념 문서**: `devlog/SCODA_MCP_Wrapping_Plan.md`

---

## 10. 핵심 원칙 요약

> **"SCODA wraps its existing local database as an MCP server, enabling language models to generate evidence-grounded narratives from historically explicit taxonomic data without direct access to the underlying canonical database."**

**DB is truth. MCP is access. LLM is narration. Snapshots are exports.**
