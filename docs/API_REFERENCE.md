# Trilobase REST API Reference

**버전:** 1.0.0
**Base URL:** `http://localhost:8080`

---

## 목차

- [개요](#개요)
- [Taxonomy API](#taxonomy-api)
- [Search & Query API](#search--query-api)
- [Metadata API](#metadata-api)
- [Annotations API](#annotations-api)
- [에러 코드](#에러-코드)

---

## 개요

Trilobase REST API는 삼엽충 분류학 데이터베이스에 대한 프로그래매틱 접근을 제공합니다. 모든 응답은 JSON 형식이며, HTTP 상태 코드로 성공/실패를 나타냅니다.

### 기본 원칙

- **Read-Only (Canonical DB)**: 분류학 데이터는 읽기 전용
- **Read/Write (Overlay DB)**: 사용자 주석만 쓰기 가능
- **CORS**: 모든 origin 허용 (로컬 개발용)

---

## Taxonomy API

### GET /api/tree

전체 분류 계층 트리를 조회합니다 (Class → Order → Suborder → Superfamily → Family).

**Parameters:** 없음

**Response:**
```json
[
  {
    "id": 1,
    "name": "Trilobita",
    "rank": "Class",
    "author": "WALCH, 1771",
    "genera_count": 5113,
    "children": [
      {
        "id": 2,
        "name": "Agnostida",
        "rank": "Order",
        "author": "SALTER, 1864",
        "genera_count": 543,
        "children": [...]
      }
    ]
  }
]
```

**특징:**
- 재귀적 구조 (children 배열)
- Genus는 포함되지 않음 (Family까지만)
- `genera_count`: 실제 하위 Genus 개수

---

### GET /api/rank/:id

특정 분류 계급(Rank)의 상세 정보를 조회합니다.

**Parameters:**
- `id` (path, required): taxonomic_ranks.id

**Response:**
```json
{
  "id": 42,
  "name": "Paradoxididae",
  "rank": "Family",
  "author": "HAWLE & CORDA, 1847",
  "year": 1847,
  "genera_count": 89,
  "notes": null,
  "parent_name": "Paradoxidoidea",
  "parent_rank": "Superfamily",
  "children_counts": [
    {"rank": "Genus", "count": 89}
  ],
  "children": [
    {
      "id": 100,
      "name": "Paradoxides",
      "rank": "Genus",
      "author": "BRONGNIART"
    }
  ]
}
```

**Error:**
- `404`: Rank not found

---

### GET /api/family/:family_id/genera

특정 Family에 속한 Genus 목록을 조회합니다.

**Parameters:**
- `family_id` (path, required): Family의 taxonomic_ranks.id

**Response:**
```json
{
  "family": {
    "id": 42,
    "name": "Paradoxididae",
    "author": "HAWLE & CORDA, 1847",
    "genera_count": 89
  },
  "genera": [
    {
      "id": 100,
      "name": "Paradoxides",
      "author": "BRONGNIART",
      "year": 1822,
      "type_species": "Paradoxides paradoxissimus",
      "location": "Czech Republic",
      "is_valid": 1
    }
  ]
}
```

**Error:**
- `404`: Family not found

---

### GET /api/genus/:genus_id

특정 Genus의 상세 정보를 조회합니다.

**Parameters:**
- `genus_id` (path, required): Genus의 taxonomic_ranks.id

**Response:**
```json
{
  "id": 100,
  "name": "Paradoxides",
  "author": "BRONGNIART",
  "year": 1822,
  "year_suffix": null,
  "type_species": "Paradoxides paradoxissimus",
  "type_species_author": "LINNAEUS, 1758",
  "formation": "Jince Formation",
  "location": "Czech Republic",
  "family": "Paradoxididae",
  "family_name": "Paradoxididae",
  "temporal_code": "MCAM",
  "is_valid": 1,
  "notes": null,
  "raw_entry": "Paradoxides BRONGNIART, 1822...",
  "synonyms": [
    {
      "id": 1,
      "senior_taxon_id": 100,
      "senior_name": "Paradoxides",
      "synonym_type": "j.o.s.",
      "fide_author": "WHITTINGTON",
      "fide_year": 1997
    }
  ],
  "formations": [
    {
      "id": 10,
      "name": "Jince Formation",
      "type": "Fm",
      "country": "Czech Republic",
      "period": "MCAM"
    }
  ],
  "locations": [
    {
      "id": 5,
      "country": "Czech Republic",
      "region": "Bohemia"
    }
  ]
}
```

**필드 설명:**
- `is_valid`: 1=유효, 0=무효 (synonym)
- `year_suffix`: 같은 저자/연도가 여러 개일 때 구분 (a, b, c)
- `raw_entry`: 원본 텍스트 (추적성)
- `synonyms`: 동의어 관계
- `formations`: 발견 지층 (다대다)
- `locations`: 발견 지역 (다대다)

**Error:**
- `404`: Genus not found

---

## Search & Query API

### GET /api/queries

사용 가능한 Named Query 목록을 조회합니다.

**Parameters:** 없음

**Response:**
```json
[
  {
    "id": 1,
    "name": "taxonomy_tree",
    "description": "Get full taxonomy tree from Class to Family",
    "params": "{}",
    "created_at": "2026-02-05 10:00:00"
  },
  {
    "id": 2,
    "name": "family_genera",
    "description": "Get all genera in a family",
    "params": "{\"family_id\": null}",
    "created_at": "2026-02-05 10:00:00"
  }
]
```

---

### GET /api/queries/:name/execute

Named Query를 실행합니다.

**Parameters:**
- `name` (path, required): Query 이름
- Query별 파라미터 (query string)

**예시:**
```
GET /api/queries/family_genera/execute?family_id=42
```

**Response:**
```json
{
  "query": "family_genera",
  "columns": ["id", "name", "author", "year"],
  "row_count": 89,
  "rows": [
    {"id": 100, "name": "Paradoxides", "author": "BRONGNIART", "year": 1822}
  ]
}
```

**Error:**
- `404`: Query not found
- `400`: SQL execution error

---

## Metadata API

### GET /api/metadata

데이터베이스 메타데이터와 통계를 조회합니다.

**Parameters:** 없음

**Response:**
```json
{
  "name": "Trilobase",
  "version": "1.0.0",
  "description": "A taxonomic database of trilobite genera",
  "license": "CC-BY-4.0",
  "created": "2026-02-04",
  "statistics": {
    "class": 1,
    "order": 12,
    "suborder": 8,
    "superfamily": 13,
    "family": 191,
    "genus": 5113,
    "valid_genera": 4258,
    "synonyms": 1055,
    "bibliography": 2130,
    "formations": 2009,
    "countries": 151
  }
}
```

---

### GET /api/provenance

데이터 출처 정보를 조회합니다.

**Parameters:** 없음

**Response:**
```json
[
  {
    "id": 1,
    "source_type": "primary",
    "citation": "Jell, P.A. & Adrain, J.M. 2002",
    "description": "Available Generic Names for Trilobites",
    "year": 2002,
    "url": null
  },
  {
    "id": 2,
    "source_type": "supplementary",
    "citation": "Adrain, J.M. 2011",
    "description": "Class Trilobita Walch, 1771",
    "year": 2011,
    "url": null
  }
]
```

---

### GET /api/display-intent

SCODA Display Intent 힌트를 조회합니다.

**Parameters:** 없음

**Response:**
```json
[
  {
    "id": 1,
    "entity": "genera",
    "default_view": "tree",
    "description": "Hierarchical taxonomy browser",
    "source_query": "taxonomy_tree",
    "priority": 1
  }
]
```

---

### GET /api/manifest

UI Manifest (선언적 뷰 정의)를 조회합니다.

**Parameters:** 없음

**Response:**
```json
{
  "name": "default",
  "description": "Default UI manifest for Trilobase",
  "manifest": {
    "views": [
      {
        "id": "taxonomy_tree",
        "type": "tree",
        "title": "Taxonomy Tree",
        "query": "taxonomy_tree"
      }
    ]
  },
  "created_at": "2026-02-05 10:00:00"
}
```

---

## Annotations API

### GET /api/annotations/:entity_type/:entity_id

특정 Entity의 사용자 주석을 조회합니다.

**Parameters:**
- `entity_type` (path, required): `genus`, `family`, `order`, `suborder`, `superfamily`, `class`
- `entity_id` (path, required): taxonomic_ranks.id

**Response:**
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

**Annotation Types:**
- `note`: 일반 메모
- `correction`: 수정 제안
- `alternative`: 대안 해석
- `link`: 외부 리소스 링크

---

### POST /api/annotations

새로운 주석을 생성합니다.

**Request Body:**
```json
{
  "entity_type": "genus",
  "entity_id": 100,
  "annotation_type": "note",
  "content": "Check formation data for accuracy",
  "author": "researcher_1"
}
```

**Required Fields:**
- `entity_type`
- `entity_id`
- `annotation_type`
- `content`

**Optional Fields:**
- `author`

**Response:**
```json
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
```

**Error:**
- `400`: Invalid entity_type or annotation_type
- `400`: Missing required field

---

### DELETE /api/annotations/:annotation_id

주석을 삭제합니다.

**Parameters:**
- `annotation_id` (path, required): user_annotations.id

**Response:**
```json
{
  "message": "Annotation deleted successfully"
}
```

**Error:**
- `404`: Annotation not found

---

## 에러 코드

### HTTP 상태 코드

| 코드 | 의미 | 설명 |
|-----|------|------|
| 200 | OK | 요청 성공 |
| 400 | Bad Request | 잘못된 요청 파라미터 |
| 404 | Not Found | 리소스를 찾을 수 없음 |
| 500 | Internal Server Error | 서버 내부 오류 |

### 에러 응답 형식

```json
{
  "error": "Error message describing what went wrong"
}
```

---

## 예제 코드

### Python (requests)

```python
import requests

# Get taxonomy tree
response = requests.get('http://localhost:8080/api/tree')
tree = response.json()

# Get genus detail
response = requests.get('http://localhost:8080/api/genus/100')
genus = response.json()
print(f"{genus['name']} {genus['author']}, {genus['year']}")

# Create annotation
annotation = {
    "entity_type": "genus",
    "entity_id": 100,
    "annotation_type": "note",
    "content": "Interesting specimen from Jince Formation"
}
response = requests.post('http://localhost:8080/api/annotations', json=annotation)
result = response.json()
```

### JavaScript (fetch)

```javascript
// Get taxonomy tree
const response = await fetch('http://localhost:8080/api/tree');
const tree = await response.json();

// Search genera by country (via named query)
const response2 = await fetch(
  'http://localhost:8080/api/queries/country_genera/execute?country=China'
);
const genera = await response2.json();

// Create annotation
const annotation = {
  entity_type: 'genus',
  entity_id: 100,
  annotation_type: 'note',
  content: 'Check this later'
};
const response3 = await fetch('http://localhost:8080/api/annotations', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify(annotation)
});
```

### cURL

```bash
# Get metadata
curl http://localhost:8080/api/metadata

# Get genus detail
curl http://localhost:8080/api/genus/100

# Create annotation
curl -X POST http://localhost:8080/api/annotations \
  -H "Content-Type: application/json" \
  -d '{
    "entity_type": "genus",
    "entity_id": 100,
    "annotation_type": "note",
    "content": "Interesting specimen"
  }'

# Delete annotation
curl -X DELETE http://localhost:8080/api/annotations/1
```

---

## 주의사항

### SCODA 원칙

- **Canonical Data는 불변**: taxonomic_ranks, synonyms, formations 등의 데이터는 읽기 전용
- **User Annotations만 수정 가능**: Overlay DB (trilobase_overlay.db)에만 쓰기 허용
- **원본 데이터 추적**: `raw_entry` 필드로 원본 텍스트 보존

### 성능 최적화

- **페이지네이션**: Genus 목록 API는 자동으로 정렬되어 반환됨
- **인덱스**: name, rank, parent_id, is_valid 등에 인덱스 적용
- **캐싱**: 프론트엔드에서 taxonomy tree 결과를 캐싱 권장

### 데이터 일관성

- `genera_count`는 실제 하위 Genus를 COUNT한 값 (denormalized)
- `is_valid=0`인 Genus는 동의어로, `synonyms` 테이블에서 senior taxon 확인 가능
- Formation/Location은 다대다 관계 (한 Genus가 여러 지역에서 발견 가능)

---

## 버전 히스토리

- **v1.0.0** (2026-02-09): Initial API release with Phase 22
  - 14 API endpoints
  - SCODA metadata support
  - User annotations (Overlay DB)

---

## 참고 문서

- [MCP Guide](MCP_GUIDE.md) - MCP 서버 사용 가이드
- [SCODA Concept](SCODA_CONCEPT.md) - SCODA 개념 설명
- [HANDOVER](HANDOVER.md) - 프로젝트 현황

---

**Last Updated:** 2026-02-09
