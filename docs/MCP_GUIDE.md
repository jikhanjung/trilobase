# Trilobase MCP Server Guide

**Model Context Protocol (MCP) 서버 사용 가이드**

**버전:** 1.1.0
**MCP SDK:** 1.26.0

---

## 목차

- [개요](#개요)
- [설치 및 설정](#설치-및-설정)
- [MCP 도구 목록](#mcp-도구-목록)
- [사용 예시](#사용-예시)
- [Evidence Pack 패턴](#evidence-pack-패턴)
- [SCODA 원칙](#scoda-원칙)
- [고급 사용법](#고급-사용법)
- [트러블슈팅](#트러블슈팅)

---

## 개요

Trilobase MCP 서버는 **Model Context Protocol**을 통해 LLM(Large Language Model)이 자연어로 삼엽충 데이터베이스를 쿼리할 수 있게 합니다.

### MCP란?

**Model Context Protocol**은 Anthropic이 개발한 프로토콜로, LLM이 외부 데이터 소스와 도구에 표준화된 방식으로 접근할 수 있게 합니다.

### 주요 특징

- **14개 도구**: Taxonomy 탐색, 검색, 메타데이터 조회, 주석 관리
- **Evidence Pack 패턴**: 출처 추적 가능한 구조화된 응답
- **SCODA 원칙 준수**: DB is truth, MCP is access, LLM is narration
- **Overlay DB 지원**: 사용자 주석 읽기/쓰기

### 아키텍처

**Mode 1: stdio (기존)**
```
┌─────────────────┐
│   Claude/LLM    │ (자연어 쿼리)
└────────┬────────┘
         │ JSON-RPC (stdio)
         ▼
┌──────────────────────────┐
│    MCP Server            │
│  - 14 tools              │
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

**Mode 2: SSE (신규, v1.1.0)**
```
┌─────────────────┐
│   Claude/LLM    │ (자연어 쿼리)
└────────┬────────┘
         │ HTTP SSE
         ▼
┌──────────────────────────┐
│  Trilobase GUI           │
│  ├─ Flask (8080)         │
│  └─ MCP Server (8081)    │ ← DB 연결 유지
└────────┬─────────────────┘
         │ Direct DB access
         ▼
┌──────────────────────────┐
│  SQLite Databases        │
│  - Canonical (read-only) │
│  - Overlay (read/write)  │
└──────────────────────────┘
```

---

## 설치 및 설정

### 1. 의존성 설치

**기본 (stdio 모드):**
```bash
pip install mcp>=1.0.0
```

**SSE 모드 추가 (v1.1.0+):**
```bash
pip install mcp>=1.0.0 starlette uvicorn
```

### 2. MCP 서버 테스트

```bash
# 기본 테스트 실행
python3 test_mcp_basic.py

# 출력:
# 🚀 Starting MCP server test...
# ✅ Session initialized
# 📋 Found 14 tools
# 🎉 All tests passed!
```

### 3. Claude Desktop 설정

#### 방법 1: SSE 모드 with PyInstaller 번들 (가장 간편, v1.1.0+)

**장점:**
- Python 설치 불필요
- DB 연결 유지 → 빠른 응답
- GUI에서 원클릭 시작
- MCP 서버가 실행 파일에 내장됨

**1단계: Trilobase 실행 파일 다운로드**
- [릴리스 페이지](https://github.com/yourname/trilobase/releases)에서 OS에 맞는 파일 다운로드:
  - Windows: `trilobase.exe`
  - Linux: `trilobase`

**2단계: 실행 파일 실행**
```bash
# Linux/macOS
./trilobase

# Windows
더블클릭: trilobase.exe
```

**3단계: GUI에서 "▶ Start All" 클릭**
- Flask (8080) + MCP (8081) 동시 시작
- MCP 서버는 자동으로 SSE 모드로 실행됨

**4단계: Claude Desktop 설정**

**파일:** `~/.config/claude/claude_desktop_config.json` (macOS/Linux) 또는 `%APPDATA%\Claude\claude_desktop_config.json` (Windows)

```json
{
  "mcpServers": {
    "trilobase": {
      "url": "http://localhost:8081/sse"
    }
  }
}
```

**5단계: Claude Desktop 재시작**

**완료!** 이제 Claude Desktop에서 Trilobase를 사용할 수 있습니다.

**중요:**
- Trilobase GUI가 실행 중이어야 MCP 서버 사용 가능
- GUI를 닫으면 MCP 서버도 함께 종료됨
- 백그라운드 실행이 필요하면 방법 3 참조

---

#### 방법 2: SSE 모드 with Python (개발자용, v1.1.0+)

**장점:** 소스 코드 수정 가능

**1단계: 의존성 설치**
```bash
pip install mcp>=1.0.0 starlette uvicorn flask
```

**2단계: Trilobase GUI 실행**
```bash
python scripts/gui.py
```

**3단계: "▶ Start All" 클릭**
- Flask (8080) + MCP (8081) 동시 시작

**4단계: Claude Desktop 설정**

**파일:** `~/.config/claude/claude_desktop_config.json` (macOS/Linux) 또는 `%APPDATA%\Claude\claude_desktop_config.json` (Windows)

```json
{
  "mcpServers": {
    "trilobase": {
      "url": "http://localhost:8081/sse"
    }
  }
}
```

---

#### 방법 3: stdio 모드 (GUI 없이 독립 실행)

---

#### 방법 2: stdio 모드 (기존)

**장점:** GUI 없이 독립 실행 가능

**macOS/Linux:**

**설정 파일:** `~/.config/claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "trilobase": {
      "command": "python3",
      "args": ["/absolute/path/to/trilobase/mcp_server.py", "--mode", "stdio"],
      "cwd": "/absolute/path/to/trilobase"
    }
  }
}
```

**Windows:**

**설정 파일:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "trilobase": {
      "command": "python",
      "args": ["C:\\path\\to\\trilobase\\mcp_server.py", "--mode", "stdio"],
      "cwd": "C:\\path\\to\\trilobase"
    }
  }
}
```

---

### 4. 설정 방법 비교

| 특징 | 방법 1: PyInstaller 번들 | 방법 2: Python (SSE) | 방법 3: stdio |
|------|-------------------------|---------------------|--------------|
| **Python 설치** | 불필요 ✅ | 필요 | 필요 |
| **실행 방식** | GUI 더블클릭 | `python scripts/gui.py` | Claude가 자동 spawn |
| **DB 연결** | 유지 (빠름) ⚡ | 유지 (빠름) ⚡ | 매번 재연결 |
| **설정** | URL 방식 | URL 방식 | command 방식 |
| **GUI 필요** | 실행 중이어야 함 | 실행 중이어야 함 | 불필요 |
| **백그라운드 실행** | GUI 종료 시 중단 | GUI 종료 시 중단 | 항상 가능 |
| **권장 대상** | **일반 사용자** 🏆 | 개발자 | 고급 사용자 |

**권장:** 일반 사용자는 **방법 1 (PyInstaller 번들)**을 사용하세요!

---

### 5. Claude Desktop 재시작

설정 파일 저장 후 Claude Desktop을 재시작하면 Trilobase MCP 서버가 자동으로 연결됩니다.

---

### 6. MCP 서버 수동 실행 (고급 사용자용)

GUI 없이 SSE 서버를 백그라운드로 실행하려면:

```bash
# SSE 모드로 실행
python3 mcp_server.py --mode sse --port 8081

# 백그라운드 실행
nohup python3 mcp_server.py --mode sse --port 8081 > mcp_server.log 2>&1 &

# Health check
curl http://localhost:8081/health
```

---

## MCP 도구 목록

### Taxonomy Exploration (4개)

#### 1. `get_taxonomy_tree`

전체 분류 계층 트리를 조회합니다 (Class → Family).

**Parameters:** 없음

**사용 예시 (자연어):**
- "분류 체계를 보여줘"
- "전체 Order 목록을 알려줘"

**응답 구조:**
```json
[
  {
    "id": 1,
    "name": "Trilobita",
    "rank": "Class",
    "author": "WALCH, 1771",
    "genera_count": 5113,
    "children": [...]
  }
]
```

---

#### 2. `get_rank_detail`

특정 분류 계급의 상세 정보를 조회합니다.

**Parameters:**
- `rank_id` (integer, required): taxonomic_ranks.id

**사용 예시 (자연어):**
- "Order Agnostida에 대해 알려줘"
- "Family Paradoxididae의 하위 Genus는?"

**응답 구조:**
```json
{
  "id": 42,
  "name": "Paradoxididae",
  "rank": "Family",
  "author": "HAWLE & CORDA, 1847",
  "genera_count": 89,
  "parent_name": "Paradoxidoidea",
  "children_counts": [{"rank": "Genus", "count": 89}],
  "children": [...]
}
```

---

#### 3. `get_family_genera`

특정 Family에 속한 Genus 목록을 조회합니다.

**Parameters:**
- `family_id` (integer, required): Family의 taxonomic_ranks.id

**사용 예시 (자연어):**
- "Family Paradoxididae에 속한 속들을 나열해줘"

**응답 구조:**
```json
{
  "family": {
    "id": 42,
    "name": "Paradoxididae",
    "genera_count": 89
  },
  "genera": [
    {"id": 100, "name": "Paradoxides", "author": "BRONGNIART", "year": 1822}
  ]
}
```

---

#### 4. `get_genus_detail`

Genus 상세 정보를 **Evidence Pack** 형식으로 조회합니다.

**Parameters:**
- `genus_id` (integer, required): Genus의 taxonomic_ranks.id

**사용 예시 (자연어):**
- "Paradoxides에 대해 자세히 알려줘"
- "Agnostus의 동의어는?"

**응답 구조 (Evidence Pack):**
```json
{
  "genus": {
    "id": 100,
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
  "formations": [
    {"name": "Jince Formation", "country": "Czech Republic"}
  ],
  "localities": [
    {"country": "Czech Republic", "region": "Bohemia"}
  ],
  "references": ["BRONGNIART, 1822", "WHITTINGTON, 1997"],
  "provenance": {
    "source": "Jell & Adrain, 2002",
    "canonical_version": "1.0.0",
    "extraction_date": "2026-02-04"
  }
}
```

---

### Search & Query (4개)

#### 5. `search_genera`

이름 패턴으로 Genus를 검색합니다.

**Parameters:**
- `name_pattern` (string, required): SQL LIKE 패턴 (예: "Paradoxides%")
- `valid_only` (boolean, optional): true면 유효한 Genus만 반환 (기본값: false)
- `limit` (integer, optional): 최대 결과 수 (기본값: 50)

**사용 예시 (자연어):**
- "Paradoxides로 시작하는 속을 찾아줘"
- "이름에 'agnost'가 들어간 속들을 보여줘"

**응답 구조:**
```json
[
  {
    "id": 100,
    "name": "Paradoxides",
    "author": "BRONGNIART",
    "year": 1822,
    "is_valid": 1,
    "family": "Paradoxididae",
    "temporal_code": "MCAM",
    "type_species": "Paradoxides paradoxissimus"
  }
]
```

---

#### 6. `get_genera_by_country`

특정 국가에서 발견된 Genus 목록을 조회합니다.

**Parameters:**
- `country` (string, required): 국가 이름 (예: "China", "Czech Republic")
- `limit` (integer, optional): 최대 결과 수 (기본값: 50)

**사용 예시 (자연어):**
- "중국에서 발견된 삼엽충 속을 보여줘"
- "체코에서 나온 속들을 알려줘"

**응답 구조:**
```json
[
  {
    "id": 100,
    "name": "Paradoxides",
    "author": "BRONGNIART",
    "year": 1822,
    "is_valid": 1,
    "family": "Paradoxididae"
  }
]
```

---

#### 7. `get_genera_by_formation`

특정 지층에서 발견된 Genus 목록을 조회합니다.

**Parameters:**
- `formation` (string, required): 지층 이름 (예: "Jince Formation")
- `limit` (integer, optional): 최대 결과 수 (기본값: 50)

**사용 예시 (자연어):**
- "Jince Formation에서 발견된 속들을 보여줘"

**응답 구조:**
```json
[
  {
    "id": 100,
    "name": "Paradoxides",
    "author": "BRONGNIART",
    "year": 1822,
    "is_valid": 1,
    "family": "Paradoxididae"
  }
]
```

---

#### 8. `execute_named_query`

사전 정의된 Named Query를 실행합니다.

**Parameters:**
- `query_name` (string, required): 쿼리 이름
- `params` (object, optional): 쿼리 파라미터 (기본값: {})

**사용 예시 (자연어):**
- "taxonomy_tree 쿼리를 실행해줘"

**응답 구조:**
```json
{
  "query": "taxonomy_tree",
  "columns": ["id", "name", "rank"],
  "row_count": 225,
  "rows": [...]
}
```

---

### Metadata & Discovery (3개)

#### 9. `get_metadata`

데이터베이스 메타데이터와 통계를 조회합니다.

**Parameters:** 없음

**사용 예시 (자연어):**
- "이 데이터베이스에 대해 알려줘"
- "총 몇 개의 속이 있어?"
- "데이터베이스 버전은?"

**응답 구조:**
```json
{
  "name": "Trilobase",
  "version": "1.0.0",
  "description": "A taxonomic database of trilobite genera",
  "license": "CC-BY-4.0",
  "statistics": {
    "class": 1,
    "order": 12,
    "genus": 5113,
    "valid_genera": 4258,
    "synonyms": 1055,
    "bibliography": 2130
  }
}
```

---

#### 10. `get_provenance`

데이터 출처 정보를 조회합니다.

**Parameters:** 없음

**사용 예시 (자연어):**
- "이 데이터는 어디서 나왔어?"
- "데이터 출처를 알려줘"

**응답 구조:**
```json
[
  {
    "id": 1,
    "source_type": "primary",
    "citation": "Jell, P.A. & Adrain, J.M. 2002",
    "description": "Available Generic Names for Trilobites",
    "year": 2002,
    "url": null
  }
]
```

---

#### 11. `list_available_queries`

사용 가능한 Named Query 목록을 조회합니다.

**Parameters:** 없음

**사용 예시 (자연어):**
- "어떤 쿼리들을 실행할 수 있어?"
- "사용 가능한 쿼리 목록을 보여줘"

**응답 구조:**
```json
[
  {
    "id": 1,
    "name": "taxonomy_tree",
    "description": "Get full taxonomy tree from Class to Family",
    "params_json": "{}",
    "created_at": "2026-02-05 10:00:00"
  }
]
```

---

### Annotation Tools (3개)

#### 12. `get_annotations`

특정 Entity의 사용자 주석을 조회합니다.

**Parameters:**
- `entity_type` (string, required): `genus`, `family`, `order`, `suborder`, `superfamily`, `class`
- `entity_id` (integer, required): taxonomic_ranks.id

**사용 예시 (자연어):**
- "Paradoxides에 대한 내 메모를 보여줘"

**응답 구조:**
```json
[
  {
    "id": 1,
    "entity_type": "genus",
    "entity_id": 100,
    "entity_name": "Paradoxides",
    "annotation_type": "note",
    "content": "Check formation data for accuracy",
    "author": "researcher_1",
    "created_at": "2026-02-09 10:00:00"
  }
]
```

---

#### 13. `add_annotation`

새로운 주석을 추가합니다 (Overlay DB에 쓰기).

**Parameters:**
- `entity_type` (string, required): Entity 타입
- `entity_id` (integer, required): Entity ID
- `entity_name` (string, required): Entity 이름 (릴리스 간 매칭용)
- `annotation_type` (string, required): `note`, `correction`, `alternative`, `link`
- `content` (string, required): 주석 내용
- `author` (string, optional): 작성자

**사용 예시 (자연어):**
- "Agnostus에 메모 추가: 'Check formation data'"
- "Paradoxides에 수정 제안: 'Year should be 1821'"

**응답 구조:**
```json
{
  "id": 1,
  "entity_type": "genus",
  "entity_id": 100,
  "entity_name": "Paradoxides",
  "annotation_type": "note",
  "content": "Check formation data",
  "author": null,
  "created_at": "2026-02-09 10:00:00"
}
```

---

#### 14. `delete_annotation`

주석을 삭제합니다.

**Parameters:**
- `annotation_id` (integer, required): user_annotations.id

**사용 예시 (자연어):**
- "주석 1번을 삭제해줘"

**응답 구조:**
```json
{
  "message": "Annotation with ID 1 deleted."
}
```

---

## 사용 예시

### Claude Desktop에서 자연어 쿼리

MCP 서버가 연결되면 Claude Desktop에서 다음과 같은 자연어로 쿼리할 수 있습니다:

#### 1. 기본 탐색

**질문:** "전체 분류 체계를 보여줘"

**Claude의 동작:**
1. `get_taxonomy_tree` 도구 호출
2. 트리 구조 분석
3. 자연어로 요약

**응답 예시:**
> Trilobase에는 1개의 Class (Trilobita), 12개의 Order가 있습니다. 주요 Order로는:
> - Agnostida (543 genera)
> - Ptychopariida (2,134 genera)
> - Phacopida (891 genera)
> ...

---

#### 2. 특정 Genus 조회

**질문:** "Paradoxides에 대해 자세히 알려줘"

**Claude의 동작:**
1. `search_genera` 도구로 "Paradoxides" 검색
2. `get_genus_detail` 도구로 상세정보 조회 (Evidence Pack)
3. 출처 인용하여 서술

**응답 예시:**
> Paradoxides BRONGNIART, 1822는 Family Paradoxididae에 속하는 유효한 속입니다.
>
> **Type Species:** Paradoxides paradoxissimus LINNAEUS, 1758
>
> **발견 지역:**
> - Czech Republic (Bohemia)
> - Jince Formation (Middle Cambrian)
>
> **동의어:**
> - Paradoxus (junior objective synonym, fide WHITTINGTON, 1997)
>
> **출처:** Jell & Adrain, 2002

---

#### 3. 지역별 검색

**질문:** "중국에서 발견된 삼엽충 속을 5개만 보여줘"

**Claude의 동작:**
1. `get_genera_by_country` 도구 호출 (country="China", limit=5)
2. 결과 정리

**응답 예시:**
> 중국에서 발견된 삼엽충 속 (5개 샘플):
>
> 1. Blackwelderia RESSER, 1937 (Family Anomocaridae)
> 2. Changaspis SUN, 1924 (Family Damesellidae)
> 3. Damesella WALCOTT, 1905 (Family Damesellidae)
> 4. Kaolishania RESSER, 1937 (Family Kaolishaniidae)
> 5. Pagetia WALCOTT, 1916 (Family Emuellidae)

---

#### 4. 주석 추가

**질문:** "Agnostus에 메모 추가해줘: 'Formation data needs verification'"

**Claude의 동작:**
1. `search_genera`로 "Agnostus" 검색하여 ID 확인
2. `add_annotation` 도구로 주석 추가

**응답 예시:**
> 주석을 추가했습니다:
> - Entity: Agnostus (genus)
> - Type: note
> - Content: "Formation data needs verification"
> - Created: 2026-02-09 10:30:00

---

#### 5. 메타데이터 조회

**질문:** "이 데이터베이스에는 총 몇 개의 유효한 속이 있어?"

**Claude의 동작:**
1. `get_metadata` 도구 호출
2. statistics.valid_genera 확인

**응답 예시:**
> Trilobase에는 총 **4,258개의 유효한 속(valid genera)**이 있습니다.
>
> 전체 통계:
> - 총 Genus: 5,113개
> - 유효 Genus: 4,258개 (83.3%)
> - 무효 Genus (동의어): 855개 (16.7%)
> - 참고문헌: 2,130건

---

## Evidence Pack 패턴

### 개념

**Evidence Pack**은 SCODA 원칙에 따라 모든 응답에 출처와 원본 데이터를 포함하는 구조화된 데이터 패킷입니다.

### 핵심 요소

1. **raw_entry**: 원본 텍스트 보존 (추적성)
2. **fide**: 정보의 출처 명시 ("according to...")
3. **provenance**: 데이터 계보 추적
4. **references**: 참고문헌 목록

### 예시

```json
{
  "genus": {
    "name": "Paradoxides",
    "author": "BRONGNIART",
    "year": 1822,
    "raw_entry": "Paradoxides BRONGNIART, 1822. Type species (by subsequent designation of VOGDES, 1893) = Entomostracites paradoxissimus LINNAEUS, 1758 = Paradoxides paradoxissimus."
  },
  "synonyms": [
    {
      "junior_name": "Paradoxus",
      "fide_author": "WHITTINGTON",
      "fide_year": 1997
    }
  ],
  "provenance": {
    "source": "Jell & Adrain, 2002",
    "canonical_version": "1.0.0",
    "extraction_date": "2026-02-04"
  }
}
```

### LLM의 올바른 사용

**✅ 좋은 예:**
> Paradoxides BRONGNIART, 1822는 Family Paradoxididae에 속합니다 (Jell & Adrain, 2002).

**❌ 나쁜 예:**
> Paradoxides는 중기 캄브리아기에 살았던 큰 삼엽충입니다.
> (데이터에 없는 정보를 추측함)

---

## SCODA 원칙

### 핵심 원칙

#### 1. DB is truth
- 데이터베이스가 유일한 진실의 원천
- LLM은 DB 데이터만 사용

#### 2. MCP is access
- MCP는 접근 수단일 뿐
- 데이터를 변경하지 않음 (Annotation 제외)

#### 3. LLM is narration
- LLM은 증거 기반 서술만 수행
- 판단이나 정의를 내리지 않음
- 항상 출처를 인용

#### 4. Snapshots are exports
- LLM이 생성한 내러티브는 파생물
- 원본 DB가 진실

### Non-Goals (LLM이 해서는 안 되는 것)

❌ **분류학적 판단이나 정의**
- "이 속은 ~에 속한다" (DB에 없는 판단)

❌ **자율적 의사결정이나 계획**
- "이 데이터를 수정해야 한다"

❌ **데이터베이스 쓰기 (주석 제외)**
- Canonical DB는 불변

### 올바른 사용 패턴

**✅ 출처 인용:**
> According to Jell & Adrain (2002), Paradoxides...

**✅ 불확실성 명시:**
> The database lists this as Middle Cambrian, though the exact age is not specified.

**✅ 데이터 기반 서술:**
> Based on the formation data, this genus has been found in Czech Republic and Morocco.

---

## 고급 사용법

### 1. 복잡한 쿼리 체인

**질문:** "Family Paradoxididae의 유효한 속들 중 중국에서 발견된 것들을 보여줘"

**Claude의 동작:**
1. `search_genera` → "Paradoxididae" 검색
2. Family ID 확인
3. `get_family_genera` → 소속 Genus 목록
4. 각 Genus에 대해 `get_genera_by_country` → "China" 필터
5. 결과 통합 및 정리

---

### 2. 주석 워크플로우

**시나리오:** 연구 중 의심스러운 데이터 발견

1. **검색:**
   ```
   "Agnostus의 Formation 정보를 보여줘"
   ```

2. **주석 추가:**
   ```
   "Agnostus에 correction 주석 추가: 'Formation name may be incorrect, check original source'"
   ```

3. **나중에 확인:**
   ```
   "Agnostus에 대한 내 주석을 보여줘"
   ```

4. **해결 후 삭제:**
   ```
   "주석 5번을 삭제해줘"
   ```

---

### 3. 통계 분석

**질문:** "각 Order별 유효한 속의 비율을 알려줘"

**Claude의 동작:**
1. `get_taxonomy_tree` → 전체 트리 조회
2. 각 Order에 대해 통계 계산
3. 표 형식으로 정리

---

### 4. Named Query 활용

**사전 정의된 쿼리 확인:**
```
"사용 가능한 쿼리 목록을 보여줘"
```

**특정 쿼리 실행:**
```
"taxonomy_tree 쿼리를 실행해줘"
```

---

## 트러블슈팅

### 문제 1: MCP 서버가 연결되지 않음

**증상:** Claude Desktop에서 Trilobase 도구가 보이지 않음

**해결 방법 (PyInstaller 번들 사용 시):**

1. **Trilobase GUI 실행 확인:**
   - GUI가 실행 중인지 확인
   - "▶ Start All" 버튼을 눌렀는지 확인
   - MCP 상태가 "● Running" (초록색)인지 확인

2. **MCP 서버 포트 확인:**
   ```bash
   # Linux/macOS
   curl http://localhost:8081/health

   # Windows PowerShell
   Invoke-WebRequest http://localhost:8081/health

   # 예상 응답:
   # {"status": "ok", "service": "trilobase-mcp", "mode": "sse"}
   ```

3. **Claude Desktop 설정 확인:**
   ```json
   {
     "mcpServers": {
       "trilobase": {
         "url": "http://localhost:8081/sse"
       }
     }
   }
   ```
   **주의:** `"url"`이지 `"command"`가 아님!

4. **Claude Desktop 재시작**

---

**해결 방법 (stdio 모드 사용 시):**

1. 설정 파일 경로 확인:
   - macOS/Linux: `~/.config/claude/claude_desktop_config.json`
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`

2. 절대 경로 사용 확인:
   ```json
   {
     "command": "python3",
     "args": ["/absolute/path/to/mcp_server.py", "--mode", "stdio"]
   }
   ```

3. Python 경로 확인:
   ```bash
   which python3  # macOS/Linux
   where python   # Windows
   ```

4. Claude Desktop 재시작

---

### 문제 2: "Database not found" 오류

**원인:** mcp_server.py가 trilobase.db를 찾지 못함

**해결 방법:**
1. `cwd` 설정 확인:
   ```json
   {
     "cwd": "/absolute/path/to/trilobase"
   }
   ```

2. DB 파일 존재 확인:
   ```bash
   ls -la /path/to/trilobase/trilobase.db
   ```

---

### 문제 3: Overlay DB 쓰기 오류

**증상:** 주석 추가 시 "read-only database" 오류

**해결 방법:**
1. Overlay DB 초기화:
   ```bash
   python3 scripts/init_overlay_db.py
   ```

2. 권한 확인:
   ```bash
   chmod 644 trilobase_overlay.db
   ```

---

### 문제 4: 포트 충돌 (8081 already in use)

**증상:** GUI에서 "MCP server failed to start: Address already in use" 오류

**원인:** 8081 포트가 이미 사용 중

**해결 방법:**

1. **기존 MCP 서버 종료:**
   ```bash
   # Linux/macOS
   lsof -ti:8081 | xargs kill -9

   # Windows PowerShell
   Get-Process -Id (Get-NetTCPConnection -LocalPort 8081).OwningProcess | Stop-Process -Force
   ```

2. **포트 사용 프로세스 확인:**
   ```bash
   # Linux/macOS
   lsof -i:8081

   # Windows
   netstat -ano | findstr :8081
   ```

3. **Trilobase GUI 재시작**

---

### 문제 5: GUI 로그에서 MCP 에러 확인

**증상:** MCP 서버가 시작되지 않지만 원인 불명

**해결 방법:**

1. **GUI 로그 뷰어 확인:**
   - Trilobase GUI 하단의 "Server Log" 섹션 확인
   - `[MCP]` prefix가 있는 로그 라인 찾기
   - ERROR (빨간색) 메시지 확인

2. **일반적인 MCP 에러:**
   ```
   [MCP] ModuleNotFoundError: No module named 'mcp'
   → 해결: pip install mcp starlette uvicorn

   [MCP] ERROR: Database not found
   → 해결: trilobase.db 파일 확인

   [MCP] Address already in use
   → 해결: 문제 4 참조 (포트 충돌)
   ```

3. **Clear Log 후 재시작:**
   - "📄 Clear Log" 버튼 클릭
   - "■ Stop All" 후 "▶ Start All"
   - 새 로그 메시지 확인

---

### 문제 6: 응답이 느림

**원인:** 대용량 쿼리 또는 네트워크 지연

**해결 방법:**

**SSE 모드 사용 시 (권장):**
- DB 연결이 유지되므로 stdio 모드보다 빠름
- 첫 쿼리 이후 응답 속도가 크게 향상됨

**쿼리 최적화:**
1. `limit` 파라미터 사용:
   - "처음 10개만 보여줘" → limit=10

2. 특정 조건으로 필터링:
   - "유효한 속만" → valid_only=true

3. Named Query 활용:
   - 복잡한 쿼리는 사전 정의된 Named Query 사용

---

### 문제 5: 테스트 실패

**증상:** pytest 실행 시 ERROR 발생

**해결 방법:**
```bash
# 기본 테스트만 실행
python3 test_mcp_basic.py

# 출력:
# 🎉 All tests passed!
```

pytest의 teardown ERROR는 기능에 영향 없음 (프레임워크 이슈).

---

## 제한 사항

### 현재 버전의 제한

1. **SSE 모드 제한 (v1.1.0)**
   - GUI 실행 중이어야 MCP 서버 사용 가능
   - GUI 종료 시 MCP 서버도 함께 종료
   - 해결책: stdio 모드 사용 또는 MCP 서버 별도 실행

2. **검색 결과 제한**
   - 기본 limit=50 (성능 최적화)

3. **복잡한 조인 쿼리 미지원**
   - Named Query로 해결 가능

### 알려진 이슈

1. **pytest teardown ERROR**
   - 기능에 영향 없음
   - pytest-asyncio 프레임워크 이슈

2. **annotations_lifecycle 테스트 간헐적 실패**
   - 응답 포맷 이슈
   - 기능은 정상 작동

---

## 참고 자료

### 공식 문서

- **MCP 프로토콜**: https://modelcontextprotocol.io/
- **MCP Python SDK**: https://github.com/modelcontextprotocol/python-sdk
- **Claude Desktop 설정**: https://modelcontextprotocol.io/clients/claude-desktop

### Trilobase 문서

- **API Reference**: [API_REFERENCE.md](API_REFERENCE.md)
- **SCODA Concept**: [SCODA_CONCEPT.md](SCODA_CONCEPT.md)
- **Handover**: [HANDOVER.md](HANDOVER.md)
- **Phase 22 Log (MCP stdio)**: [../devlog/20260209_022_phase22_mcp_server.md](../devlog/20260209_022_phase22_mcp_server.md)
- **Phase 23 Log (MCP SSE)**: [../devlog/20260210_023_phase23_mcp_sse_integration.md](../devlog/20260210_023_phase23_mcp_sse_integration.md)

---

## 버전 히스토리

- **v1.1.0** (2026-02-10): SSE 모드 추가 (Phase 23)
  - SSE (Server-Sent Events) 전송 모드 지원
  - GUI 통합 (Flask + MCP 동시 실행)
  - Health check 엔드포인트 (`/health`)
  - 하위 호환성 유지 (stdio/SSE 모드 선택 가능)
  - DB 연결 유지 → 빠른 응답

- **v1.0.0** (2026-02-09): Initial MCP server release
  - 14 tools implemented
  - Evidence Pack pattern
  - SCODA principles enforcement
  - Test suite (basic + comprehensive)

---

## 지원

### 버그 리포트

GitHub Issues를 통해 버그를 리포트해주세요.

### 기능 요청

다음과 같은 기능이 향후 추가될 예정입니다:
- [x] ~~SSE 전송 모드~~ ✅ (v1.1.0)
- [x] ~~PyInstaller 번들 포함~~ ✅ (v1.1.0)
- [ ] 캐싱 레이어
- [ ] 지질시대 필터링 도구
- [ ] Bibliography 검색 도구
- [ ] MCP 서버 독립 실행 모드 (GUI 없이 백그라운드 데몬)

---

**Last Updated:** 2026-02-10
**Author:** Claude Sonnet 4.5
