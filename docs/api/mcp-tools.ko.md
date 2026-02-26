# MCP 도구

Trilobase는 [Model Context Protocol (MCP)](https://modelcontextprotocol.io/)을 통해 **7개 도구**를 제공합니다. Claude Desktop이나 기타 MCP 호환 LLM 클라이언트에서 자연어로 데이터베이스에 접근할 수 있습니다.

---

## 도구 레퍼런스

### get_taxonomy_tree

Class에서 Family까지의 전체 분류 계층 트리를 조회합니다.

| 속성 | 값 |
|------|-----|
| 쿼리 유형 | named_query (`taxonomy_tree`) |
| 파라미터 | *없음* |

---

### search_genera

이름 패턴(SQL LIKE)으로 삼엽충 속을 검색합니다.

| 파라미터 | 타입 | 필수 | 기본값 | 설명 |
|----------|------|------|--------|------|
| name_pattern | string | 예 | — | SQL LIKE 패턴 (예: `Paradoxides%`) |
| valid_only | boolean | 아니오 | false | true이면 유효 속만 반환 |
| limit | integer | 아니오 | 50 | 최대 결과 수 |

---

### get_genus_detail

동의어, 지층, 산지, 계층 구조를 포함한 삼엽충 속의 전체 상세 정보를 조회합니다. 복합 증거 팩을 반환합니다.

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| genus_id | integer | 예 | 속의 ID |

**반환:** 속 정보, 동의어, 지층, 산지, 참고문헌, 출처를 포함한 복합 뷰.

---

### get_rank_detail

특정 분류 계급(Class, Order, Family 등)의 상세 정보를 ID로 조회합니다.

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| rank_id | integer | 예 | 분류 계급의 ID |

**반환:** 하위 분류군 수와 목록을 포함한 계급 정보.

---

### get_family_genera

특정 과에 속하는 모든 속을 조회합니다.

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| family_id | integer | 예 | 과의 ID |

---

### get_genera_by_country

특정 국가에서 발견된 속을 조회합니다.

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| country_name | string | 예 | 국가명 (예: `China`, `Germany`) |

---

### get_genera_by_formation

특정 지질학적 지층에서 발견된 속을 조회합니다.

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| formation_name | string | 예 | 지층명 |
| limit | integer | 아니오 | 최대 결과 수 (기본값: 50) |

---

### get_taxon_opinions

분류군의 분류학적 의견을 조회합니다. 다양한 문헌에서의 분류 관점을 보여줍니다.

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| taxon_id | integer | 예 | 분류군의 ID |

**반환:** 참고문헌과 함께 채택된/대안적 PLACED_IN, VALID_AS, SYNONYM_OF 의견.

---

## 증거 팩 패턴

모든 MCP 응답은 SCODA 증거 팩 패턴을 따릅니다 — 모든 응답에 출처 데이터와 출처 정보가 포함됩니다:

```json
{
  "genus": {
    "name": "Paradoxides",
    "author": "BRONGNIART",
    "year": 1822,
    "raw_entry": "원본 텍스트..."
  },
  "synonyms": ["..."],
  "provenance": {
    "source": "Jell & Adrain, 2002",
    "canonical_version": "0.2.3"
  }
}
```

**핵심 원칙:**

- **DB is truth** — 데이터베이스가 유일한 진실의 원천
- **MCP is access** — MCP는 접근 수단일 뿐
- **LLM is narration** — LLM은 증거 기반 서술만 수행

---

## 설정

MCP 서버 설정 방법은 [시작하기](../getting-started.md#옵션-3-mcp-서버-llm-연동)를 참조하세요.
