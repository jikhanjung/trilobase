# P88: Timeline Mya 기반 슬라이더 + FAD/LAD 스냅샷 필터링

**Date**: 2026-03-14
**Phase**: P88

## 목표

Timeline Geologic 슬라이더를 시대 코드 기반 누적 방식에서 Mya(million years ago) 기반 시점 스냅샷 방식으로 전환. Research(pubyear) 타임라인은 genus 명명 연도 기반 누적 필터링으로 수정.

## 변경 사항

### 1. 데이터 정리

- `data/sources/jell_adrain_2002.txt`: Cyclagnostus의 `UCAMB` → `UCAM` 오타 수정
- `scripts/build_trilobase_db.py`: `copy_taxon()` 후 `UCAMB` → `UCAM` UPDATE 추가 (canonical DB에서 복사 시 수정)

### 2. `temporal_code_mya` 테이블 신규 생성

빌드 시 PaleoCore DB를 ATTACH하여 `temporal_ranges`에서 code → (fad_mya, lad_mya) 매핑 테이블 생성:
- PaleoCore `temporal_ranges` 27건 (start_mya IS NOT NULL)
- `/` 구분 코드 4건 추가: `USIL/LDEV`, `UCAM/LORD`, `UORD/LSIL`, `PENN/LPERM`
- 총 31건

### 3. Geologic 쿼리 변경 (3개)

| 쿼리 | 변경 내용 |
|------|-----------|
| `timeline_geologic_periods` | 코드 기반 → 16개 Mya step (538.8~251.9) + End Permian |
| `taxonomy_tree_by_geologic` | 누적 필터 → 스냅샷 필터 (`fad_mya >= :timeline_value AND lad_mya <= :timeline_value`) |
| `tree_edges_by_geologic` | 동일 스냅샷 필터 패턴 |
| (param type) | `timeline_value`: `string` → `real` |

### 4. Research(pubyear) 쿼리 변경 (3개)

| 쿼리 | 변경 내용 |
|------|-----------|
| `timeline_publication_years` | reference year → genus 명명 연도(`t.year`) 기반, 현재 프로파일의 edge_cache에 있는 genus만 포함 |
| `taxonomy_tree_by_pubyear` | assertion reference year → `CAST(t.year AS INTEGER) <= :timeline_value` |
| `tree_edges_by_pubyear` | 동일 패턴 |

**문제 해결**: 이전엔 축 쿼리가 모든 genus year를 반환하여 edge_cache에 없는 무효 genus의 연도(예: 1745)가 첫 step이 되면 빈 트리가 표시됨. 축 쿼리에 `JOIN classification_edge_cache` 추가로 해결.

### 5. scoda-engine 수정

| 파일 | 변경 내용 |
|------|-----------|
| `app.js` | `loadStep()`: 빈 트리(fullRoot=null)일 때 캔버스 클리어 + 디버그 로그 추가 |
| `tree_chart.js` | `buildHierarchy()`: 빈 결과 시 `fullRoot = null` 클리어 |

### 6. 축 Step 값

```
538.8 — LCAM      470.0 — MORD      419.2 — LDEV      323.2 — PENN
509.0 — MCAM      458.4 — UORD      393.3 — MDEV      298.9 — LPERM
497.0 — UCAM      443.8 — LSIL      382.7 — UDEV      259.5 — UPERM
485.4 — LORD      433.4 — USIL      358.9 — MISS      251.9 — End Permian
```

## 검증 결과

- Build: 31 temporal_code_mya mappings, 52 ui_queries
- Validate: 17/17 checks passed
- .scoda: 빌드 성공
- Tests: 117 passed

### 스냅샷 필터링 검증

| Mya | 시대 | Genera |
|-----|------|--------|
| 538.8 | LCAM | 688 |
| 509.0 | MCAM | 1,685 |
| 497.0 | UCAM | 2,006 |
| 433.4 | USIL | 277 |
| 251.9 | End Permian | 25 |

- `/` 구분 코드 (USIL/LDEV 3건): 433.4 Mya, 419.2 Mya 모두에서 표시됨

## 수정 파일

### trilobase
- `data/sources/jell_adrain_2002.txt` — UCAMB 오타 수정
- `scripts/build_trilobase_db.py` — temporal_code_mya 테이블 + 쿼리 6개 + 파라미터 타입
- `db/trilobase-0.3.1.db` — 재빌드
- `db/trilobase-0.3.1.manifest.json` — 재빌드

### scoda-engine
- `scoda_engine/static/js/app.js` — 빈 트리 처리 + 디버그 로그
- `scoda_engine/static/js/tree_chart.js` — buildHierarchy 빈 결과 시 fullRoot 클리어
