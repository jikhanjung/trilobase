# Formation Country/Period 데이터 채우기

**날짜:** 2026-02-15
**계획:** `devlog/20260215_P47_formation_metadata_backfill.md`

## 요약

paleocore.db `formations` 테이블 2,004건 전부 country/period가 NULL이던 것을
DB 내 기존 관계를 역추출하여 채움.

## 접근

`genus_formations` → `genus_locations.region_id` → `pc.geographic_regions` 경로로
formation에 연결된 genera의 국가/시대를 집계하여 최다 빈도 값을 선택.

### 주의: country_id vs region_id

- `genus_locations.country_id`는 레거시 `countries` 테이블 FK (비정규화된 이름: "USA", "England")
- `genus_locations.region_id`는 `geographic_regions` 테이블 FK (정규화된 이름: "United States of America", "United Kingdom")
- **region_id 사용** → 정확한 국가명 도출

## 결과

| 항목 | 값 |
|------|-----|
| 총 formations | 2,004 |
| country 채움 | 1,997 (99.65%) |
| period 채움 | 1,976 (98.6%) |
| country NULL 잔존 | 7 (genus_locations 데이터 없는 formations) |
| period NULL 잔존 | 28 (temporal_code 없는 genera만 연결된 formations) |
| 다수 country formations | 40건 (최다 빈도 선택) |
| 다수 period formations | 173건 (최다 빈도 선택) |

## 변경 파일

| 파일 | 변경 |
|------|------|
| `scripts/populate_formation_metadata.py` | **신규** — backfill 스크립트 |
| `paleocore.db` | formations.country/period UPDATE |

## 검증

```bash
python scripts/populate_formation_metadata.py --report   # dry-run 확인
python scripts/populate_formation_metadata.py             # 실행
sqlite3 paleocore.db "SELECT name, country, period FROM formations WHERE country IS NOT NULL LIMIT 20;"
pytest tests/ -x -q                                       # 226 통과 ✅
```

## 테스트

기존 226개 테스트 영향 없음. conftest.py의 formations 테스트 데이터는 이미 country/period 값 포함.
