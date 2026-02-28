# P74 — Assertion-Centric Test DB

**Date:** 2026-02-28

## Summary

P52 수준의 canonical DB를 변경하지 않고, assertion-centric 모델을 별도 테스트 DB로 구현하여 P53 비전을 실험.

## 산출물

| 파일 | 역할 |
|------|------|
| `scripts/create_assertion_db.py` | 메인 변환 스크립트 |
| `scripts/validate_assertion_db.py` | 검증 스크립트 (12 checks) |
| `dist/assertion_test/trilobase_assertion.db` | 테스트 DB (gitignored) |

## Schema 변경

| 현재 (P52) | P74 테스트 DB |
|------------|---------------|
| `taxonomic_ranks` (parent_id 저장) | `taxon` (parent_id **없음**) |
| `taxonomic_opinions` (1,139건) | `assertion` (6,142건) |
| `bibliography` (2,131건) | `reference` (2,132건 = 2,131 + JA2002) |
| 없음 | `classification_profile` (2 프로필) |
| 없음 | `classification_edge_cache` (5,083 edges) |
| 트리 = parent_id 직접 조회 | 트리 = assertion 필터 → recursive CTE 파생 |

## 데이터 변환 결과

```
taxon:          5,341
reference:      2,132 (bibliography 2,131 + Jell & Adrain 2002)
assertion:      6,142
  PLACED_IN:    5,085 (82 from opinions + 5,003 from parent_id)
    accepted:   5,083
  SYNONYM_OF:   1,055
  SPELLING_OF:  2
edge_cache:     5,083 (default profile)
```

## Assertion에서 파생한 트리

- **v_taxonomy_tree**: recursive CTE로 Class 루트부터 전체 트리 파생
- **v_taxonomic_ranks**: 기존 parent_id 호환 뷰 (assertion에서 역산)
- **synonyms**: 기존 synonyms 뷰 호환

### 트리 동치성: 100% (원본 parent_id = 파생 parent_id)

### CTE 트리 도달:
- 4,895/5,341 taxa 도달 (Class 루트 기준)
- 12/13 Order 도달
- Agnostida (189 taxa) 제외: Adrain(2011)이 Trilobita sensu stricto에서 제외 처리
- 유효 속: 4,158/4,259 도달 (101건 = Agnostida 하위)

## Classification Profiles

| Profile | 설명 | Rule |
|---------|------|------|
| `default` | 모든 accepted PLACED_IN | `{"predicate": "PLACED_IN", "is_accepted": 1}` |
| `ja2002_strict` | JA2002 PLACED_IN만 | `{"predicate": "PLACED_IN", "is_accepted": 1, "reference_id": 0}` |

## 실행 방법

```bash
python scripts/create_assertion_db.py
python scripts/validate_assertion_db.py
# → 12/12 checks passed
```

## 핵심 설계 결정

1. **Jell & Adrain 2002**: bibliography에 없으므로 reference id=0으로 삽입 (provenance에만 존재)
2. **Adrain 2011**: bibliography id=2131 그대로 사용
3. **Agnostida 제외**: accepted PLACED_IN의 object_taxon_id=NULL → CTE 트리에서 자연 제외
4. **parent_id → PLACED_IN 생성 시**: 기존 opinion에서 이미 PLACED_IN 변환된 taxon은 중복 방지
5. **hierarchy ranks → Adrain 2011 reference**, **genera → JA2002 reference** 할당
