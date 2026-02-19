# P47: Formations Country/Period 데이터 채우기

**날짜**: 2026-02-15
**상태**: 계획

## Context

paleocore.db `formations` 테이블 2,004건 전부 country/period가 NULL. Phase 5에서 formation 이름/타입만 추출하고 country/period는 파싱 안 함. DB 내 기존 관계를 활용해 역추출.

## 현황

| 항목 | 값 |
|------|-----|
| 총 formations | 2,004 |
| country 채울 수 있는 formations | 1,997 (99.65%) — 7건은 genus_locations 데이터 없음 |
| period 채울 수 있는 formations | 1,976 (98.6%) — 28건은 temporal_code 없는 genera만 연결 |
| 단일 country formations | 1,957 / 다수 country: 40건 |
| 단일 period formations | 1,802 / 다수 period: 174건 |

## 접근

`scripts/populate_formation_metadata.py` 신규 스크립트 작성.

### 로직

1. trilobase.db 열고 paleocore.db ATTACH
2. **Country**: `genus_formations` → `genus_locations.region_id` → `pc.geographic_regions` → 부모 country명
   - formation당 genus 빈도 최다 country 선택
3. **Period**: `genus_formations` → `taxonomic_ranks.temporal_code` → `pc.temporal_ranges.name`
   - formation당 genus 빈도 최다 temporal_code 선택
   - temporal_code를 사람 읽기 좋은 period명으로 변환 (LCAM → "Lower Cambrian")
4. paleocore.db `formations` 테이블 UPDATE
5. `--dry-run` / `--report` 모드 지원

### 변경 파일

| 파일 | 변경 |
|------|------|
| `scripts/populate_formation_metadata.py` | **신규** |
| `paleocore.db` | formations.country/period UPDATE |

### 테스트 fixture 변경 불필요

`tests/conftest.py`의 formations 테스트 데이터는 이미 country/period 값 있음 (Büdesheimer Sh → Germany/Devonian 등). 기존 226개 테스트 영향 없음.

## 검증

```bash
python scripts/populate_formation_metadata.py --report   # dry-run 확인
python scripts/populate_formation_metadata.py             # 실행
sqlite3 paleocore.db "SELECT name, country, period FROM formations WHERE country IS NOT NULL LIMIT 20;"
pytest tests/ -x -q                                       # 226 통과 확인
```
