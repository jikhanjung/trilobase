# P89 — Paleobase Meta-Package 설계

**날짜:** 2026-03-18
**유형:** Plan
**상태:** Draft (scoda-engine 미구현)
**이전 문서:** P88 (통합 패키지 아이디어), design/paleobase_design.md v0.1~v0.2 (삭제됨)

---

## 1. 배경

P88에서 `-base` 명명의 억지스러움과 통합 패키지 필요성을 제기했고, 3가지 옵션(번들/메타패키지/단일DB) 중 **옵션 2(메타패키지)**를 채택하기로 했다.

이 문서는 P88의 아이디어를 구체적인 설계로 발전시킨 것이다. 패키지명은 133번 작업에서 라틴화 분류군명으로 전환 완료.

## 2. 개요

Paleobase는 복수의 도메인별 SCODA 패키지(trilobita, brachiopoda 등)를 하나의 통합 탐색 공간으로 엮는 **meta-package / orchestration layer**이다.

데이터를 복제하지 않는다. 대신 다음을 제공한다:

- **Meta Tree** — 패키지 간 상위 분류 계층(Life → Metazoa → Phylum)
- **Package Bindings** — meta tree 노드와 개별 패키지의 taxon을 연결
- **Dependency Graph** — 패키지 의존성 선언 및 해석
- **Unified Entry Point** — 통합 탐색 시작점
- **Cross-Package Query** — 패키지 경계를 넘는 통계/검색(향후)

## 3. 설계 원칙

| 원칙 | 설명 |
|------|------|
| No data duplication | 각 패키지 DB에 데이터가 1벌만 존재 |
| Package independence | 개별 패키지는 paleobase 없이도 독립 작동 |
| Lazy loading | 노드 확장 시점에 해당 패키지를 로드 |
| Source-aware | 각 바인딩에 출처(Treatise edition 등)를 명시 |
| Assertion-compatible | 현행 assertion 모델(PLACED_IN/SYNONYM_OF/SPELLING_OF)과 호환 |
| Incremental adoption | 기존 패키지를 수정하지 않고도 meta-package에 편입 가능 |

## 4. 아키텍처

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

### 4.1 현재 패키지 현황

| 패키지 | 버전 | 최상위 Rank | 주 분류군 | Genera |
|--------|------|------------|----------|--------|
| trilobita | 0.3.3 | Class | Trilobita | 5,627 |
| brachiopoda | 0.2.6 | Phylum | Brachiopoda | 4,664 |
| graptolithina | 0.1.2 | Phylum | Graptolithina | 539 |
| chelicerata | 0.1.2 | Phylum | Chelicerata | 262 |
| ostracoda | 0.1.2 | Phylum | Ostracoda | 782 |

> trilobita는 현재 Class부터 시작하므로, Phylum Arthropoda 노드를 DB에 추가하여 다른 Arthropoda 패키지(chelicerata, ostracoda)와 계층 구조를 맞춰야 한다.

### 4.2 PaleoCore (공유 인프라, v0.1.3)

| 테이블 | 내용 |
|--------|------|
| countries | 국가 목록 + CoW 매핑 |
| geographic_regions | 계층적 지역 구조 |
| formations | 지층 목록 (정규화) |
| ics_chronostrat | ICS 국제 층서 연대표 (GTS 2020) |
| temporal_code_mya | temporal_code → FAD/LAD Mya (73건) |

## 5. Manifest 설계

현행 SCODA manifest를 확장하여 `kind: "meta-package"` 유형을 추가한다.

```json
{
  "format": "scoda",
  "format_version": "1.0",
  "name": "paleobase",
  "version": "0.3.0",
  "title": "Paleobase — Treatise-derived invertebrate paleontology bundle",
  "kind": "meta-package",
  "dependencies": [
    {"name": "paleocore",     "alias": "pc",  "version": ">=0.1.3,<0.2.0", "required": true},
    {"name": "trilobita",     "alias": "tri", "version": ">=0.3.0,<0.4.0", "required": true},
    {"name": "brachiopoda",   "alias": "bra", "version": ">=0.2.0,<0.3.0", "required": true},
    {"name": "graptolithina", "alias": "gra", "version": ">=0.1.0,<0.2.0", "required": true},
    {"name": "chelicerata",   "alias": "che", "version": ">=0.1.0,<0.2.0", "required": true},
    {"name": "ostracoda",     "alias": "ost", "version": ">=0.1.0,<0.2.0", "required": true}
  ],
  "entry_points": [
    {"node_id": "node:metazoa", "label": "Metazoa", "default_view": "tree"}
  ],
  "meta_tree_file": "meta_tree.json",
  "package_bindings_file": "package_bindings.json"
}
```

일반 패키지와의 차이:

| 필드 | 일반 패키지 | meta-package |
|------|-----------|-------------|
| `kind` | (없음) | `"meta-package"` |
| `data_file` | `"data.db"` (필수) | (없음) |
| `meta_tree_file` | (없음) | `"meta_tree.json"` |
| `package_bindings_file` | (없음) | `"package_bindings.json"` |
| `dependencies` | 0~1개 | N개 (모든 하위 패키지) |

## 6. Meta Tree

개별 패키지보다 상위의 분류 계층을 정의. 각 패키지의 root taxon이 이 트리의 leaf에 바인딩된다.

```json
{
  "schema_version": "1.0",
  "nodes": [
    {"id": "node:life",          "label": "Life",          "rank": "root"},
    {"id": "node:eukaryota",     "label": "Eukaryota",     "rank": "domain",  "parent": "node:life"},
    {"id": "node:metazoa",       "label": "Metazoa",       "rank": "kingdom", "parent": "node:eukaryota"},
    {"id": "node:arthropoda",    "label": "Arthropoda",    "rank": "phylum",  "parent": "node:metazoa"},
    {"id": "node:brachiopoda",   "label": "Brachiopoda",   "rank": "phylum",  "parent": "node:metazoa"},
    {"id": "node:hemichordata",  "label": "Hemichordata",  "rank": "phylum",  "parent": "node:metazoa"},
    {"id": "node:echinodermata", "label": "Echinodermata", "rank": "phylum",  "parent": "node:metazoa"},
    {"id": "node:mollusca",      "label": "Mollusca",      "rank": "phylum",  "parent": "node:metazoa"},
    {"id": "node:cnidaria",      "label": "Cnidaria",      "rank": "phylum",  "parent": "node:metazoa"},
    {"id": "node:bryozoa",       "label": "Bryozoa",       "rank": "phylum",  "parent": "node:metazoa"},
    {"id": "node:porifera",      "label": "Porifera",      "rank": "phylum",  "parent": "node:metazoa"}
  ]
}
```

설계 결정:
- **coarse-grained**: Phylum 수준까지만. 그 아래는 패키지 내부 트리에 위임.
- **바인딩 없는 노드 허용**: 아직 패키지가 없는 Phylum도 구조적 위치 표시용으로 포함. UI에서 비활성 표시.
- **Graptolithina**: Hemichordata 문의 일부 (Treatise 2023 "Hemichordata (Graptolithina)"). `node:hemichordata` 아래에 바인딩.

## 7. Package Bindings

meta tree 노드와 개별 패키지의 root taxon을 연결.

```json
{
  "schema_version": "1.0",
  "bindings": [
    {
      "node_id": "node:arthropoda",
      "package_id": "trilobita",
      "root_taxon": {"name": "Arthropoda", "rank": "Phylum", "id_hint": null},
      "binding_type": "subtree",
      "source": "Treatise Part O (1959/1997) + Jell & Adrain (2002)",
      "priority": 1,
      "notes": "trilobita DB에 Phylum Arthropoda 추가 후, Arthropoda를 root로 바인딩"
    },
    {
      "node_id": "node:arthropoda",
      "package_id": "chelicerata",
      "root_taxon": {"name": "Chelicerata", "rank": "Subphylum", "id_hint": 1},
      "binding_type": "subtree",
      "source": "Treatise Part P (1955)",
      "priority": 2
    },
    {
      "node_id": "node:arthropoda",
      "package_id": "ostracoda",
      "root_taxon": {"name": "Ostracoda", "rank": "Class", "id_hint": 1},
      "binding_type": "subtree",
      "source": "Treatise Part Q (1961)",
      "priority": 3
    },
    {
      "node_id": "node:brachiopoda",
      "package_id": "brachiopoda",
      "root_taxon": {"name": "Brachiopoda", "rank": "Phylum", "id_hint": 1},
      "binding_type": "subtree",
      "source": "Treatise Part H (1965, 2000-2006)",
      "priority": 1
    },
    {
      "node_id": "node:hemichordata",
      "package_id": "graptolithina",
      "root_taxon": {"name": "Graptolithina", "rank": "Phylum", "id_hint": 1},
      "binding_type": "subtree",
      "source": "Treatise Part V (1955/1970/2023)",
      "priority": 1
    }
  ]
}
```

### Multi-Binding Resolution

하나의 node에 복수 패키지 가능 (예: `node:arthropoda`에 3개):

```
Arthropoda (meta)
├── Trilobita [trilobita] ← Class
├── Chelicerata [chelicerata] ← Subphylum
└── Ostracoda [ostracoda] ← Class
```

바인딩된 root taxon의 rank가 다를 수 있지만, meta tree에서 rank 정렬을 강제하지 않고 패키지 원래 구조를 존중한다. UI에서 `[package_id]` 태그로 출처 표시.

## 8. Assertion / Profile 호환

### Assertion

Paleobase 자체는 assertion을 생성하지 않는다. 각 패키지 내부의 assertion을 cross-package 뷰로 조회할 수 있게 하는 것이 목표.

```sql
SELECT 'trilobita' AS package, COUNT(*) AS synonyms
  FROM tri.assertion WHERE predicate = 'SYNONYM_OF'
UNION ALL
SELECT 'brachiopoda', COUNT(*)
  FROM bra.assertion WHERE predicate = 'SYNONYM_OF'
```

Cross-package assertion(예: "Trilobita는 Arthropoda에 속한다")은 meta tree 바인딩으로 이미 표현됨. 별도 테이블은 현 단계 불필요.

### Classification Profile

현재 trilobita (default, treatise1959, treatise1997)와 brachiopoda (Treatise 1965, Treatise Revised 2000-2006)가 복수 profile을 보유. 향후 paleobase 수준의 합성 profile 가능:

```json
{
  "profile_name": "treatise_latest",
  "package_profiles": {
    "trilobita": "treatise1997",
    "brachiopoda": "treatise_revised_2000_2006",
    "graptolithina": "default",
    "chelicerata": "default",
    "ostracoda": "default"
  }
}
```

## 9. Runtime

### 초기화

1. paleobase.scoda 로드
2. manifest → `kind: "meta-package"` 확인
3. dependencies 해석 → 각 패키지 .scoda 탐색
4. meta_tree.json / package_bindings.json 로드
5. entry_point 노드 UI 표시

### Lazy Loading

```
사용자: "Arthropoda" 클릭
  → bindings에서 node:arthropoda 조회 → 3개 바인딩
  → 각 패키지 .scoda on-demand 로드 → SQLite ATTACH
  → 각 root_taxon 직계 자식 조회 → 합성 목록 반환
```

### SQLite ATTACH 전략

SQLite 제한: ATTACH 최대 10개.
paleocore(항상) + 5개 패키지 = 6 ATTACH — 한도 내.
패키지가 늘어나면 LRU 기반 on-demand attach/detach.

## 10. View Integration

| 쿼리 | 내용 |
|------|------|
| `pb_package_summary` | 패키지별 taxa/assertion/reference 건수 |
| `pb_temporal_coverage` | 전 패키지 시대별 genus 분포 |
| `pb_diversity_total` | 전체 다양성 차트 (지질 시대 x 패키지) |

통합 검색, 통합 Timeline도 cross-package UNION 쿼리로 구현.

## 11. .scoda 파일 구조

```
paleobase-0.3.0.scoda  (ZIP)
├── manifest.json
├── meta_tree.json
├── package_bindings.json
└── (data.db 없음)
```

배포: 독립 배포 기본, 번들 옵션 병행.

## 12. 사전 점검 사항

### Phylum Rank 호환성

| 패키지 | 최상위 Rank | Phylum 노드 | 연결 방식 |
|--------|------------|-------------|---------|
| trilobita | Class | ❌ (추가 필요) | Phylum Arthropoda 추가 후 바인딩 |
| brachiopoda | Phylum | ✅ | root taxon 바인딩 |
| graptolithina | Phylum | ✅ | Hemichordata 아래 |
| chelicerata | Phylum | ✅ | Subphylum Chelicerata 바인딩 |
| ostracoda | Phylum | ✅ | Class Ostracoda 바인딩 |

### PaleoCore 의존성

| 패키지 | 의존 선언 | 실제 사용 |
|--------|----------|----------|
| trilobita | ✅ | ✅ |
| brachiopoda | ❌ 미선언 | ✅ (빌드 시 삽입) |
| graptolithina | ❌ 미선언 | ✅ |
| chelicerata | ❌ 미선언 | ✅ |
| ostracoda | ❌ 미선언 | ✅ |

→ 4개 패키지에 paleocore 의존성 선언 추가 필요.

## 13. 신규 패키지 후보 (TSF 존재, SCODA 미완)

| 패키지 | TSF 소스 | 비고 |
|--------|---------|------|
| porifera | Part E (1955, 1972, 2003, 2004, 2015) | 6개 TSF |
| cnidaria | Part F (1956) | 1개 TSF |
| bryozoa | Part G (1953, 1983) | 2개 TSF |
| mollusca | Part I, K, L, N (1957~1971) | 9개 TSF |
| echinodermata | Part S, T, U (1966~2011) | 5개 TSF |
| hexapoda | Part R (1992) | 1개 TSF |

## 14. Implementation Roadmap

### Stage 0: 사전 준비

- [ ] trilobita DB에 Phylum Arthropoda 노드 추가 (최상위 계층 통일)
- [ ] brachiopoda/graptolithina/chelicerata/ostracoda에 paleocore 의존성 선언
- [ ] 각 패키지 빌드 스크립트 artifact_metadata 포맷 통일

### Stage 1: Meta-Package 기초

- [ ] paleobase manifest, meta_tree.json, package_bindings.json 생성
- [ ] `build_paleobase_scoda.py` 작성
- [ ] scoda-engine에 `kind: "meta-package"` 인식 로직
- [ ] meta_tree + bindings 로딩 및 기본 트리 합성

### Stage 2: UI 통합

- [ ] meta tree 노드 표시 및 확장
- [ ] 패키지 출처 태그 (`[trilobita]` 등)
- [ ] 통합 검색, 통합 Dashboard

### Stage 3: 고급 기능

- [ ] Cross-package Timeline
- [ ] 합성 Classification Profile
- [ ] 신규 패키지 추가 시 자동 바인딩 제안

## 15. 미결 사항

1. **버전 체계** — SemVer vs CalVer (2026.03)?
2. **패키지 내부 Phylum 중복** — chelicerata/ostracoda의 자체 Phylum Arthropoda와 meta tree Arthropoda 중복 처리
3. **독립 사용 보장** — paleobase 없이 개별 패키지 사용 시 기능 제약 없어야 함
4. **TSF 미완 패키지 우선순위** — 어떤 분류군을 먼저 패키지화할 것인가?
