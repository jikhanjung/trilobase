# 089. opinion_type별 동적 컬럼 label 지원 (label_map)

**날짜**: 2026-02-23

## 배경

rank_detail의 "Taxonomic Opinions" 섹션에서 첫 컬럼 label이 `"Proposed Parent"`로 하드코딩되어 있었음.
- PLACED_IN (82건)에는 적절하지만
- SPELLING_OF (2건)에는 `"Correct Spelling"`이 맞고
- 향후 추가될 SYNONYM_OF에는 `"Valid Name"`이 적절

## 변경 내용

### 새 기능: `label_map` 속성

컬럼 정의에 `label_map` 속성을 추가하여 행 데이터의 특정 필드 값에 따라 헤더 label을 동적으로 결정.

```json
{
  "key": "related_taxon_name",
  "label": "Related Taxon",
  "label_map": {
    "key": "opinion_type",
    "map": {
      "PLACED_IN": "Proposed Parent",
      "SPELLING_OF": "Correct Spelling",
      "SYNONYM_OF": "Valid Name"
    }
  }
}
```

**동작 규칙:**
- 모든 행의 `opinion_type`이 동일 → 매핑된 label 사용
- 혼합 → `col.label` ("Related Taxon") fallback
- `label_map`을 모르는 뷰어는 `col.label`을 그대로 사용 (하위 호환)

### 수정 파일

| 파일 | 변경 |
|------|------|
| `scripts/add_scoda_manifest.py` | opinions 컬럼에 `label_map` 추가 |
| `spa/index.html` | `renderLinkedTable()` 헤더에 label_map 해석 로직 |
| `tests/conftest.py` | 테스트 manifest fixture 업데이트 |
| `tests/test_trilobase.py` | `test_opinions_column_has_label_map` 테스트 추가 |
| `db/trilobase.db` | manifest 재빌드 |

### scoda-engine 수정

| 파일 | 변경 |
|------|------|
| `scoda_engine/static/js/app.js` | `renderLinkedTable()` 헤더에 동일 label_map 로직 추가 |

## 테스트 결과

- trilobase: 101 passed
- scoda-engine: 225 passed
