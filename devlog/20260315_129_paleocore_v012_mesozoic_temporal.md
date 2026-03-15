# 20260315_129 — paleocore v0.1.2: Mesozoic temporal codes 근본 수정

## 작업 배경

20260315_128에서 brachiobase v0.2.4로 Mesozoic temporal codes를 빌드 스크립트에
직접 UNION ALL로 임시 패치했으나, 이는 공통 데이터를 각 DB마다 중복 정의하는 구조.
paleocore가 모든 시대 코드의 단일 소스가 되어야 한다는 원칙에 따라 근본 수정.

## 문제 구조

```
paleocore.temporal_ranges  ─→  각 taxonomy DB.temporal_code_mya
  (LCAM ~ UPERM + INDET만)       + UNION ALL TERT/HOL/REC (수동 패치)
```

- paleocore `temporal_ranges`가 Paleozoic(UPERM)까지만 정의
- 모든 taxonomy 빌드 스크립트가 TERT/HOL/REC를 UNION ALL로 개별 추가
- graptobase는 추가로 CAM/MSIL/LCARB까지 개별 추가

## 수정 내용

### 1. `build_paleocore_db.py` 리팩터링

`temporal_ranges` 테이블을 trilobase 복사 방식에서 **인라인 정의**로 전환:

- `DATA_TABLES`에서 `temporal_ranges` 제거 (trilobase-0.3.1.db에 해당 테이블 없음)
- `insert_temporal_ranges(conn)` 함수 신규 추가
- 전체 70개 코드 정의:

| 그룹 | 코드 수 | 예시 |
|------|---------|------|
| Paleozoic | 32 | LCAM~UPERM, CARB, UCARB, LCARB, MSIL 등 추가 |
| Mesozoic | 18 | LTRI/MTRI/UTRI/TRIAS/TRI, LJUR/MJUR/UJUR/JUR, LCRET/UCRET/CRET |
| Cenozoic | 19 | PALEOCENE/EOC/OLIG/PALEOG, MIO/PLIO/PLEI, HOL/REC/TERT 등 |
| INDET | 1 | |

- VERSION: 0.1.1 → **0.1.2**
- 빌드 시 `--source paleocore-0.1.1.db` 방식으로 geographic/ICS 데이터 계승

### 2. 각 taxonomy 빌드 스크립트 정리

수동 UNION ALL 전부 제거 — paleocore에서 자동으로 오므로:

| 스크립트 | 제거된 수동 코드 |
|---------|----------------|
| build_brachiobase_db.py | Mesozoic 18개 + Cenozoic 15개 + TERT/HOL/REC (v0.2.4 임시 패치 전체) |
| build_ostracobase_db.py | TERT/HOL/REC |
| build_chelicerobase_db.py | TERT/HOL/REC |
| build_graptobase_db.py | TERT/HOL/REC/CAM/MSIL/LCARB |

### 3. 버전 업

| 패키지 | 이전 | 이후 |
|--------|------|------|
| paleocore | 0.1.1 | **0.1.2** |
| brachiobase | 0.2.4 | **0.2.5** |
| ostracobase | 0.1.0 | **0.1.1** |
| chelicerobase | 0.1.0 | **0.1.1** |
| graptobase | 0.1.0 | **0.1.1** |

## 결과

앞으로 새 시대 코드 추가 시 `build_paleocore_db.py`의 `insert_temporal_ranges()`에만
추가하면 모든 taxonomy DB에 자동 반영됨.

## 변경 파일

- `scripts/build_paleocore_db.py` — insert_temporal_ranges() 추가, VERSION→0.1.2
- `db/paleocore-0.1.2.db` — 신규
- `scripts/build_brachiobase_db.py` — UNION ALL 제거, VERSION→0.2.5
- `scripts/build_ostracobase_db.py` — UNION ALL 제거, VERSION→0.1.1
- `scripts/build_chelicerobase_db.py` — UNION ALL 제거, VERSION→0.1.1
- `scripts/build_graptobase_db.py` — UNION ALL 제거, VERSION→0.1.1
- `db/brachiobase-0.2.5.db`, `db/ostracobase-0.1.1.db`, `db/chelicerobase-0.1.1.db`, `db/graptobase-0.1.1.db` — 신규
