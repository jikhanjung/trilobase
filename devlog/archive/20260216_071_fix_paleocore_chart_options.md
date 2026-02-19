# PaleoCore Chronostratigraphy Chart 정렬 오류 수정

**날짜:** 2026-02-16

## 문제

PaleoCore에서 Chronostratigraphy nested table이 지질시대 순서가 아닌 DB id 순으로 정렬됨.
(Permian → Cambrian → Silurian 순서로 표시, 올바른 순서는 ... → Permian → Carboniferous → Devonian → Silurian → Ordovician → Cambrian)

## 원인

`scripts/create_paleocore.py`의 `chart_options`가 불완전:

```json
// Before (PaleoCore) — cell_click만 있음
"chart_options": {
    "cell_click": {"detail_view": "chronostrat_detail", "id_key": "id"}
}
```

누락된 키들:
- `order_key` → 기본값 `"id"` 사용 → id 순 정렬 (올바른 값: `"display_order"`)
- `skip_ranks` → 기본값 `[]` → Super-Eon 미제거
- `rank_columns` → 기본 fallback 사용 → 컬럼 라벨 부정확
- `color_key`, `value_column` → 기본 fallback 사용

Trilobase manifest에는 이 옵션들이 모두 있어서 정상 동작.

## 수정

- `scripts/create_paleocore.py`: trilobase와 동일한 전체 `chart_options` 추가
- `paleocore.db`: manifest를 직접 UPDATE (trilobase.db에서 PaleoCore 테이블이 DROP되어 스크립트 재실행 불가)

## 테스트

- `pytest tests/ -x -q` → 231 passed
