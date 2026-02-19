# Bugfix: taxa_count 컬럼 참조 제거 (country/region/formation detail API)

**날짜:** 2026-02-13

## 문제

Phase 34에서 PaleoCore 테이블(`geographic_regions`, `formations`)을 `trilobase.db`에서 DROP하면서 `taxa_count` 컬럼도 함께 제거됨 (Phase 31 `create_paleocore.py`에서 의도적으로 제외한 컬럼).

그러나 `app.py`의 3개 API 엔드포인트에서 여전히 `taxa_count` 컬럼을 직접 참조하고 있어 500 에러 발생:

```
sqlite3.OperationalError: no such column: gr.taxa_count
```

## 영향 받은 엔드포인트

| 엔드포인트 | 쿼리 위치 |
|---|---|
| `GET /api/country/<id>` | country 조회 + child regions 조회 |
| `GET /api/region/<id>` | region 조회 |
| `GET /api/formation/<id>` | formation 조회 |

## 수정 방법

`taxa_count` 컬럼 직접 참조를 `COUNT(DISTINCT) ... LEFT JOIN` 실시간 계산으로 대체:

- `/api/country/<id>`: `COUNT(DISTINCT gl.genus_id)` via `LEFT JOIN genus_locations`
- `/api/region/<id>`: `COUNT(DISTINCT gl.genus_id)` via `LEFT JOIN genus_locations`
- `/api/formation/<id>`: `COUNT(DISTINCT gf2.genus_id)` via `LEFT JOIN genus_formations`

## 테스트

- `pytest test_app.py -v` → 161개 전부 통과

## 참고

- 이 수정은 소스 코드(`app.py`)에만 적용됨
- PyInstaller EXE에 반영하려면 `python scripts/build.py`로 재빌드 필요
