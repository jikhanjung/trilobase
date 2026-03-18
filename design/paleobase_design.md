# Paleobase Meta-Package Design v0.3

> **Status:** Concept / Draft (scoda-engine 미구현)
> **Last updated:** 2026-03-18
> **Previous versions:** v0.1 (초안), v0.2 (binding schema 추가) — 이 문서로 통합

---

## 1. Overview

Paleobase는 복수의 도메인별 SCODA 패키지(trilobita, brachiopoda 등)를 하나의 통합 탐색 공간으로 엮는 **meta-package / orchestration layer**이다.

Paleobase는 데이터를 복제하지 않는다. 대신 다음을 제공한다:

- **Meta Tree** — 패키지 간 상위 분류 계층(Life → Metazoa → Phylum)
- **Package Bindings** — meta tree 노드와 개별 패키지의 taxon을 연결
- **Dependency Graph** — 패키지 의존성 선언 및 해석
- **Unified Entry Point** — 통합 탐색 시작점
- **Cross-Package Query** — 패키지 경계를 넘는 통계/검색(향후)

---

## 2. Design Principles

| 원칙 | 설명 |
|------|------|
| **No data duplication** | 각 패키지 DB에 데이터가 1벌만 존재 |
| **Package independence** | 개별 패키지는 paleobase 없이도 독립 작동 |
| **Lazy loading** | 노드 확장 시점에 해당 패키지를 로드 |
| **Source-aware** | 각 바인딩에 출처(Treatise edition 등)를 명시 |
| **Assertion-compatible** | 현행 assertion 모델(PLACED_IN/SYNONYM_OF/SPELLING_OF)과 호환 |
| **Incremental adoption** | 기존 패키지를 수정하지 않고도 meta-package에 편입 가능 |

---

## 3. Architecture Layers

```
┌─────────────────────────────────────────────┐
│              Paleobase (meta-package)        │
│  meta_tree · bindings · entry_points        │
├─────────────────────────────────────────────┤
│              PaleoCore (shared infra)        │
│  geography · chronostrat · formations       │
│  temporal_code_mya · ICS mapping            │
├──────┬──────┬──────┬──────┬──────┬──────────┤
│trilo-│brach-│grap- │cheli-│ostra-│ future   │
│bita  │iopoda│tolit-│cerata│coda  │ packages │
│      │      │hina  │      │      │          │
└──────┴──────┴──────┴──────┴──────┴──────────┘
```

### 3.1 Package Layer

각 도메인별 SCODA 패키지. 실제 분류 데이터(taxon, assertion, reference)를 보유.

| 패키지 | 버전 | 최상위 Rank | 주 분류군 | Genera |
|--------|------|------------|----------|--------|
| trilobita | 0.3.3 | Class | Trilobita | 5,627 |
| brachiopoda | 0.2.6 | Phylum | Brachiopoda | 4,664 |
| graptolithina | 0.1.2 | Phylum | Graptolithina | 539 |
| chelicerata | 0.1.2 | Phylum | Chelicerata | 262 |
| ostracoda | 0.1.2 | Phylum | Ostracoda | 782 |

> **참고:** trilobita는 현재 Class부터 시작. Phylum Arthropoda 노드가 없으므로 paleobase meta tree에서 상위 연결을 제공한다.

### 3.2 PaleoCore Layer

패키지 간 공유 인프라. 현재 v0.1.3.

| 테이블 | 내용 |
|--------|------|
| countries | 국가 목록 + CoW 매핑 |
| geographic_regions | 계층적 지역 구조 |
| cow_states | Correlates of War 국가 체계 |
| country_cow_mapping | country ↔ CoW 매핑 |
| formations | 지층 목록 (정규화) |
| ics_chronostrat | ICS 국제 층서 연대표 (GTS 2020) |
| temporal_ics_mapping | temporal_code → ICS 매핑 |
| temporal_code_mya | temporal_code → FAD/LAD Mya (73건) |

### 3.3 Paleobase Layer (이 문서의 설계 대상)

meta_tree, package_bindings, dependency graph, entry_points를 관리.
자체 데이터는 갖지 않으며, 다른 패키지의 데이터를 참조만 한다.

---

## 4. Paleobase Manifest

현행 SCODA manifest 스키마를 확장하여 `kind: "meta-package"` 유형을 추가한다.

```json
{
  "format": "scoda",
  "format_version": "1.0",
  "name": "paleobase",
  "version": "0.3.0",
  "title": "Paleobase — Treatise-derived invertebrate paleontology bundle",
  "description": "Meta-package integrating trilobita, brachiopoda, graptolithina, chelicerata, ostracoda into a unified taxonomy space",
  "kind": "meta-package",
  "created_at": "2026-03-18T00:00:00+00:00",
  "license": "CC-BY-4.0",
  "authors": [],
  "scoda_schema_version": "1.0",

  "dependencies": [
    {"name": "paleocore",     "alias": "pc",  "version": ">=0.1.3,<0.2.0", "required": true},
    {"name": "trilobita",     "alias": "tri", "version": ">=0.3.0,<0.4.0", "required": true},
    {"name": "brachiopoda",   "alias": "bra", "version": ">=0.2.0,<0.3.0", "required": true},
    {"name": "graptolithina",    "alias": "gra", "version": ">=0.1.0,<0.2.0", "required": true},
    {"name": "chelicerata", "alias": "che", "version": ">=0.1.0,<0.2.0", "required": true},
    {"name": "ostracoda",   "alias": "ost", "version": ">=0.1.0,<0.2.0", "required": true}
  ],

  "entry_points": [
    {"node_id": "node:metazoa", "label": "Metazoa", "default_view": "tree"}
  ],

  "metadata": {
    "primary_source": "Treatise on Invertebrate Paleontology",
    "mode": "bootstrap",
    "extensible": true
  },

  "meta_tree_file": "meta_tree.json",
  "package_bindings_file": "package_bindings.json"
}
```

### 4.1 현행 SCODA manifest와의 차이

| 필드 | 일반 패키지 | meta-package |
|------|-----------|-------------|
| `kind` | (없음, 암묵적 "package") | `"meta-package"` |
| `data_file` | `"data.db"` (필수) | (없음 — 자체 DB 없음) |
| `meta_tree_file` | (없음) | `"meta_tree.json"` |
| `package_bindings_file` | (없음) | `"package_bindings.json"` |
| `dependencies` | 0~1개 (보통 paleocore만) | N개 (모든 하위 패키지) |

### 4.2 scoda-engine 구현 요구사항

현재 `ScodaPackage` 클래스는 단일 DB 패키지만 지원한다. meta-package 지원을 위해:

1. `kind` 필드 인식 — `"meta-package"`이면 `data_file` 불필요
2. `meta_tree.json` / `package_bindings.json` 로딩
3. 복수 패키지 동시 ATTACH 지원 (현재 1:1 ATTACH만)
4. binding 기반 subtree 동적 합성

---

## 5. Meta Tree Schema

meta_tree는 개별 패키지보다 상위의 분류 계층을 정의한다.
각 패키지의 root taxon이 이 트리의 leaf에 바인딩된다.

```json
{
  "schema_version": "1.0",
  "nodes": [
    {
      "id": "node:life",
      "label": "Life",
      "rank": "root"
    },
    {
      "id": "node:eukaryota",
      "parent": "node:life",
      "label": "Eukaryota",
      "rank": "domain"
    },
    {
      "id": "node:metazoa",
      "parent": "node:eukaryota",
      "label": "Metazoa",
      "rank": "kingdom"
    },

    {
      "id": "node:arthropoda",
      "parent": "node:metazoa",
      "label": "Arthropoda",
      "rank": "phylum"
    },
    {
      "id": "node:brachiopoda",
      "parent": "node:metazoa",
      "label": "Brachiopoda",
      "rank": "phylum"
    },
    {
      "id": "node:hemichordata",
      "parent": "node:metazoa",
      "label": "Hemichordata",
      "rank": "phylum"
    },
    {
      "id": "node:echinodermata",
      "parent": "node:metazoa",
      "label": "Echinodermata",
      "rank": "phylum"
    },
    {
      "id": "node:mollusca",
      "parent": "node:metazoa",
      "label": "Mollusca",
      "rank": "phylum"
    },
    {
      "id": "node:cnidaria",
      "parent": "node:metazoa",
      "label": "Cnidaria",
      "rank": "phylum"
    },
    {
      "id": "node:bryozoa",
      "parent": "node:metazoa",
      "label": "Bryozoa",
      "rank": "phylum"
    },
    {
      "id": "node:porifera",
      "parent": "node:metazoa",
      "label": "Porifera",
      "rank": "phylum"
    }
  ]
}
```

### 5.1 설계 결정

- **coarse-grained**: meta tree는 Phylum 수준까지만 정의. 그 아래는 패키지 내부 트리에 위임.
- **확장 가능**: TSF 소스가 추가되면 노드를 추가하면 됨 (Echinodermata, Mollusca 등은 향후 패키지화 대비 선언).
- **바인딩 없는 노드 허용**: 아직 패키지가 없는 Phylum도 구조적 위치 표시용으로 포함 가능. UI에서 비활성 표시.

### 5.2 Graptolithina의 분류학적 위치

Graptolithina는 현재 학계에서 Hemichordata 문(Phylum)의 일부로 분류된다.
Treatise 2023 개정판 제목도 "Hemichordata (Graptolithina)"이다.

```
Metazoa → Hemichordata → Pterobranchia → Graptolithina
```

따라서 `node:hemichordata` 아래에 graptolithina를 바인딩한다.

---

## 6. Package Binding Schema

meta tree 노드와 개별 패키지의 root taxon을 연결하는 선언.

```json
{
  "schema_version": "1.0",
  "bindings": [
    {
      "node_id": "node:arthropoda",
      "package_id": "trilobita",
      "root_taxon": {
        "name": "Trilobita",
        "rank": "Class",
        "id_hint": 1
      },
      "binding_type": "subtree",
      "source": "Treatise Part O (1959/1997) + Jell & Adrain (2002)",
      "priority": 1,
      "notes": "trilobita 최상위가 Class이므로, meta tree Arthropoda 아래에 직접 연결"
    },
    {
      "node_id": "node:arthropoda",
      "package_id": "chelicerata",
      "root_taxon": {
        "name": "Chelicerata",
        "rank": "Subphylum",
        "id_hint": 1
      },
      "binding_type": "subtree",
      "source": "Treatise Part P (1955)",
      "priority": 2
    },
    {
      "node_id": "node:arthropoda",
      "package_id": "ostracoda",
      "root_taxon": {
        "name": "Ostracoda",
        "rank": "Class",
        "id_hint": 1
      },
      "binding_type": "subtree",
      "source": "Treatise Part Q (1961)",
      "priority": 3
    },
    {
      "node_id": "node:brachiopoda",
      "package_id": "brachiopoda",
      "root_taxon": {
        "name": "Brachiopoda",
        "rank": "Phylum",
        "id_hint": 1
      },
      "binding_type": "subtree",
      "source": "Treatise Part H (1965, 2000–2006)",
      "priority": 1
    },
    {
      "node_id": "node:hemichordata",
      "package_id": "graptolithina",
      "root_taxon": {
        "name": "Graptolithina",
        "rank": "Phylum",
        "id_hint": 1
      },
      "binding_type": "subtree",
      "source": "Treatise Part V (1955/1970/2023)",
      "priority": 1,
      "notes": "graptolithina는 Graptolithina를 Phylum으로 취급 (Treatise 관행). meta tree에서는 Hemichordata 아래 배치"
    }
  ]
}
```

### 6.1 Binding Fields

| 필드 | 필수 | 설명 |
|------|------|------|
| `node_id` | ✅ | meta_tree 노드 ID |
| `package_id` | ✅ | 대상 SCODA 패키지 이름 |
| `root_taxon` | ✅ | 패키지 내 바인딩 시작 taxon (name, rank, id_hint) |
| `binding_type` | ✅ | `subtree` (하위 트리 전체) 또는 `leaf` (단일 노드) |
| `source` | | 데이터 출처 |
| `priority` | | 같은 node_id에 복수 바인딩 시 표시 순서 (낮을수록 우선) |
| `notes` | | 자유 형식 비고 |

### 6.2 Multi-Binding Resolution

하나의 meta tree 노드에 복수 패키지가 바인딩될 수 있다.
예: `node:arthropoda`에 trilobita, chelicerata, ostracoda 3개가 연결됨.

**런타임 동작:**

1. 사용자가 "Arthropoda" 노드를 확장
2. 엔진이 해당 node_id의 모든 바인딩을 조회
3. priority 순으로 각 패키지의 root taxon subtree를 로드
4. 합성된 자식 노드 목록을 표시:
   ```
   Arthropoda (meta)
   ├── Trilobita [trilobita] ← Class
   ├── Chelicerata [chelicerata] ← Subphylum
   └── Ostracoda [ostracoda] ← Class
   ```

### 6.3 Rank 정렬 이슈

바인딩된 root taxon들의 rank가 다를 수 있다 (Subphylum vs Class).
meta tree 수준에서는 rank 정렬을 강제하지 않고, 패키지의 원래 구조를 존중한다.
UI에서 `[package_id]` 태그로 출처를 표시하여 사용자가 구분할 수 있게 한다.

---

## 7. Assertion Model 호환

현행 assertion 테이블 스키마:

```sql
CREATE TABLE assertion (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_taxon_id INTEGER NOT NULL REFERENCES taxon(id),
    predicate TEXT NOT NULL
        CHECK(predicate IN ('PLACED_IN','SYNONYM_OF','SPELLING_OF','RANK_AS','VALID_AS')),
    object_taxon_id INTEGER REFERENCES taxon(id),
    value_text TEXT,
    reference_id INTEGER REFERENCES reference(id),
    assertion_status TEXT DEFAULT 'asserted'
        CHECK(assertion_status IN ('asserted','incertae_sedis','questionable','indet')),
    curation_confidence TEXT DEFAULT 'high',
    synonym_type TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 7.1 Paleobase에서의 Assertion 활용

Paleobase 자체는 assertion을 생성하지 않는다.
각 패키지 내부의 assertion을 cross-package 뷰로 조회할 수 있게 하는 것이 목표.

**예시 쿼리 — 전 패키지 synonym 통계:**

```sql
-- 각 패키지 DB를 ATTACH한 상태에서
SELECT 'trilobita' AS package, COUNT(*) AS synonyms
  FROM tri.assertion WHERE predicate = 'SYNONYM_OF'
UNION ALL
SELECT 'brachiopoda', COUNT(*)
  FROM bra.assertion WHERE predicate = 'SYNONYM_OF'
UNION ALL
SELECT 'graptolithina', COUNT(*)
  FROM gra.assertion WHERE predicate = 'SYNONYM_OF'
-- ...
```

### 7.2 Cross-Package Assertion (향후)

패키지 경계를 넘는 assertion이 필요한 경우 (예: "Trilobita는 Arthropoda에 속한다"):

- 이러한 assertion은 paleobase의 meta tree 바인딩으로 이미 표현됨
- 별도의 cross-package assertion 테이블은 현 단계에서 불필요
- 향후 필요시 paleobase에 경량 assertion 테이블 추가 가능

---

## 8. Classification Profile 통합

현재 trilobita에만 복수 profile이 존재 (default, treatise1959, treatise1997).
다른 패키지는 단일 profile.

### 8.1 Cross-Package Profile (향후)

향후 paleobase 수준의 "합성 profile"을 정의할 수 있다:

```json
{
  "profile_name": "treatise_latest",
  "description": "각 패키지의 최신 Treatise 기준 분류",
  "package_profiles": {
    "trilobita": "treatise1997",
    "brachiopoda": "default",
    "graptolithina": "default",
    "chelicerata": "default",
    "ostracoda": "default"
  }
}
```

이 정보는 `package_bindings.json`에 profile 매핑으로 추가하거나,
별도의 `profiles.json` 파일로 관리할 수 있다.

---

## 9. Runtime Behavior

### 9.1 초기화 시퀀스

```
1. paleobase.scoda 로드
2. manifest 읽기 → kind: "meta-package" 확인
3. dependencies 해석 → 각 패키지 .scoda 파일 탐색
4. meta_tree.json 로드 → 상위 분류 트리 구성
5. package_bindings.json 로드 → 바인딩 맵 구성
6. entry_point 노드를 UI에 표시
```

### 9.2 노드 확장 (Lazy Loading)

```
사용자: "Arthropoda" 클릭
  → 엔진: bindings에서 node:arthropoda 조회
  → 3개 바인딩 발견 (trilobita, chelicerata, ostracoda)
  → 각 패키지의 .scoda 로드 (아직 안 된 경우)
  → SQLite ATTACH로 각 DB 연결
  → 각 root_taxon의 직계 자식 조회
  → 합성 자식 목록 반환
```

### 9.3 SQLite ATTACH 전략

현행 scoda-engine은 최대 3-DB ATTACH를 사용한다 (main + overlay + paleocore).
meta-package는 동시에 더 많은 DB를 ATTACH해야 한다.

**SQLite 제한:** ATTACH 최대 10개 (기본값, 컴파일 시 변경 가능).

**전략:**
- paleocore는 항상 ATTACH (공유 인프라)
- 나머지 패키지는 접근 시점에 on-demand ATTACH
- 동시 ATTACH 수 제한 (LRU 기반 detach)
- 최악의 경우: paleocore + 5개 패키지 = 6 ATTACH (한도 내)

---

## 10. View Integration

### 10.1 통합 Dashboard

paleobase 전용 ui_queries로 cross-package 통계 제공:

| 쿼리 이름 | 내용 |
|----------|------|
| `pb_package_summary` | 패키지별 taxa/assertion/reference 건수 |
| `pb_temporal_coverage` | 전 패키지 시대별 genus 분포 (temporal_code_mya 활용) |
| `pb_diversity_total` | 전체 다양성 차트 (지질 시대 × 패키지) |

### 10.2 통합 검색

```sql
-- 전 패키지에서 genus 검색 (예: "Agnostus")
SELECT 'trilobita' AS package, id, name, rank, year
  FROM tri.taxon WHERE name LIKE '%Agnostus%'
UNION ALL
SELECT 'brachiopoda', id, name, rank, year
  FROM bra.taxon WHERE name LIKE '%Agnostus%'
-- ...
```

### 10.3 통합 Timeline

paleocore의 `temporal_code_mya`를 기준으로 전 패키지의 시대별 다양성을 하나의 Timeline에 표시.

---

## 11. Package Distribution

### 11.1 .scoda 파일 구조 (meta-package)

```
paleobase-0.3.0.scoda  (ZIP)
├── manifest.json           ← 위 §4의 manifest
├── meta_tree.json          ← 위 §5
├── package_bindings.json   ← 위 §6
└── (data.db 없음)
```

### 11.2 Hub Manifest

기존 패키지와 동일한 형식의 hub manifest를 생성:

```json
{
  "hub_manifest_version": "1.0",
  "package_id": "paleobase",
  "version": "0.3.0",
  "title": "Paleobase — Treatise-derived invertebrate paleontology bundle",
  "kind": "meta-package",
  "dependencies": {
    "paleocore": ">=0.1.3,<0.2.0",
    "trilobita": ">=0.3.0,<0.4.0",
    "brachiopoda": ">=0.2.0,<0.3.0",
    "graptolithina": ">=0.1.0,<0.2.0",
    "chelicerata": ">=0.1.0,<0.2.0",
    "ostracoda": ">=0.1.0,<0.2.0"
  },
  "filename": "paleobase-0.3.0.scoda",
  "sha256": "...",
  "size_bytes": 0,
  "scoda_format_version": "1.0",
  "engine_compat": ">=0.2.0"
}
```

### 11.3 독립 배포 vs 번들 배포

| 방식 | 설명 | 장단점 |
|------|------|--------|
| **독립 배포** | paleobase.scoda + 각 패키지 .scoda 별도 다운로드 | 개별 업데이트 가능, 다운로드 관리 복잡 |
| **번들 배포** | paleobase-bundle.zip에 모든 .scoda 포함 | 원클릭 설치, 용량 큼, 버전 고정 |

**권장:** 독립 배포를 기본으로 하되, 편의를 위한 번들 옵션도 제공.

---

## 12. 현재 패키지 상태 점검

### 12.1 Phylum Rank 호환성

| 패키지 | 최상위 Rank | Phylum 노드 | Paleobase 연결 방식 |
|--------|------------|-------------|-------------------|
| trilobita | Class | ❌ 없음 | meta tree Arthropoda 아래 직접 바인딩 |
| brachiopoda | Phylum | ✅ Brachiopoda | root taxon을 바인딩 |
| graptolithina | Phylum | ✅ Graptolithina | Hemichordata 아래 바인딩 |
| chelicerata | Phylum | ✅ Arthropoda | Subphylum Chelicerata를 바인딩 |
| ostracoda | Phylum | ✅ Arthropoda | Class Ostracoda를 바인딩 |

> trilobita의 경우 Phylum을 추가할 필요는 없다. meta tree가 그 역할을 대신한다.
> chelicerata/ostracoda는 자체 Phylum(Arthropoda)이 있지만, meta tree의 `node:arthropoda`가 이를 흡수한다. 바인딩은 각 패키지의 실질적 root taxon(Chelicerata, Ostracoda)을 가리킨다.

### 12.2 PaleoCore 의존성 현황

| 패키지 | paleocore 의존 선언 | temporal_code_mya 사용 |
|--------|-------------------|----------------------|
| trilobita | ✅ `>=0.1.1,<0.2.0` | ✅ |
| brachiopoda | ❌ 미선언 | ✅ (빌드 시 삽입) |
| graptolithina | ❌ 미선언 | ✅ (빌드 시 삽입) |
| chelicerata | ❌ 미선언 | ✅ (빌드 시 삽입) |
| ostracoda | ❌ 미선언 | ✅ (빌드 시 삽입) |

> 4개 패키지가 paleocore를 실질적으로 사용하지만 의존성을 선언하지 않고 있다.
> paleobase 통합 전에 정리하는 것이 바람직하다.

---

## 13. Multi-Source Expansion Strategy

### Phase 1 — Treatise Skeleton (현재)

현재 5개 패키지가 Treatise 기반으로 구축됨.
TSF 소스 39개 중 DB 빌드 완료 13개, 미완 26개.

향후 DB 빌드 후보 (TSF 존재, SCODA 미완):

| 예상 패키지 | TSF 소스 | 비고 |
|------------|---------|------|
| poriferabase | Part E (1955, 1972, 2003, 2004, 2015) | 6개 TSF, ~2,600줄 |
| coelentbase | Part F (1956) | 1개 TSF, 1,256줄 |
| bryozoabase | Part G (1953, 1983) | 2개 TSF, 1,150줄 |
| molluscabase | Part I, K, L, N (1957~1971) | 9개 TSF, ~8,000줄 |
| echinobase | Part S, T, U (1966~2011) | 5개 TSF, ~1,950줄 |
| hexapobase | Part R (1992) | 1개 TSF, 2,827줄 |

### Phase 2 — Canonical Papers

Treatise 이후 분류 개정 논문 통합:
- Jell & Adrain (2002) — 이미 trilobita에 반영
- Adrain (2011) — 이미 trilobita에 반영
- 각 분류군별 주요 개정 논문 추가

### Phase 3 — Automated Extraction

- PaleoBERT 등 NLP 기반 자동 추출
- 대량의 taxonomic literature에서 assertion 자동 생성
- 낮은 confidence로 생성 → 사람 검토 워크플로우

---

## 14. Implementation Roadmap

### Stage 0: 사전 준비 (패키지 정비)

- [ ] brachiopoda/graptolithina/chelicerata/ostracoda에 paleocore 의존성 선언 추가
- [ ] 각 패키지 빌드 스크립트에서 일관된 artifact_metadata 포맷 확인

### Stage 1: Meta-Package 기초 구현

- [ ] paleobase manifest, meta_tree.json, package_bindings.json 파일 생성
- [ ] `build_paleobase_scoda.py` 빌드 스크립트 작성
- [ ] scoda-engine에 `kind: "meta-package"` 인식 로직 추가
- [ ] meta_tree + bindings 로딩 및 기본 트리 합성

### Stage 2: UI 통합

- [ ] meta tree 노드 표시 및 확장
- [ ] 패키지 출처 태그 표시 (`[trilobita]` 등)
- [ ] 통합 검색 (전 패키지 taxon 검색)
- [ ] 통합 Dashboard (패키지별 통계)

### Stage 3: 고급 기능

- [ ] Cross-package Timeline (전 패키지 시대별 다양성)
- [ ] 합성 Classification Profile
- [ ] 신규 패키지 추가 시 자동 바인딩 제안

---

## 15. Open Questions

1. **버전 관리 방식** — paleobase 자체 버전을 SemVer로 할지, CalVer (2026.03)로 할지?
2. **패키지 내부 Phylum 노드 처리** — chelicerata/ostracoda가 자체 Phylum Arthropoda를 갖고 있는데, meta tree의 Arthropoda와 중복. 무시할지, 숨길지?
3. **독립 사용 보장** — paleobase 없이 개별 패키지를 쓸 때 기능 제약이 없어야 한다. 바인딩은 순수 상향(meta → package) 참조여야 한다.
4. **TSF 미완 패키지 우선순위** — 26개 미빌드 TSF 중 어떤 분류군을 먼저 패키지화할 것인가?

---

## 16. Summary

Paleobase v0.3은:

- 5개 기존 패키지 + PaleoCore를 하나의 탐색 공간으로 통합하는 **meta-package 아키텍처**
- 데이터 복제 없이 **binding 기반 lazy subtree 합성**
- 현행 **assertion 모델**(PLACED_IN/SYNONYM_OF/SPELLING_OF)과 **classification profile** 호환
- TSF 확장에 따른 **6개 이상의 신규 패키지** 편입 경로 확보

개별 패키지의 독립성을 유지하면서, 사용자에게는 통합된 고생물학 분류 탐색 경험을 제공하는 것이 핵심 목표이다.
