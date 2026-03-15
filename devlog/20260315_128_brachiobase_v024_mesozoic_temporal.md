# 20260315_128 — Brachiobase v0.2.4: Mesozoic temporal codes 추가

## 작업 배경

brachiobase Timeline에서 UPERM 이후 바로 Tertiary로 점프하는 현상 보고.
원인 분석: `temporal_code_mya` 테이블에 Triassic·Jurassic·Cretaceous 코드가 누락.

## 원인

`build_brachiobase_db.py`는 paleocore의 `temporal_ranges` 테이블을 ATTACH해서
`temporal_code_mya`를 생성한다. 그런데 paleocore-0.1.1.db의 `temporal_ranges`가
Paleozoic(LCAM~UPERM) + INDET 까지만 있고, 중생대 코드가 전혀 없었음.

TERT·HOL·REC는 이미 UNION ALL로 수동 추가되어 있었으나,
Triassic(251.9–201.4 Ma) / Jurassic(201.4–145.0 Ma) / Cretaceous(145.0–66.0 Ma)는 누락.

brachiobase taxa 중 중생대 코드 사용 현황:
- MJUR: 111건, UTRI: 91건, LJUR: 62건, LCRET: 62건, UCRET: 60건,
  UJUR: 50건, MTRI: 49건, LTRI: 6건 등 총 수백 건

## 임시 수정 (v0.2.4)

`build_brachiobase_db.py`의 UNION ALL에 직접 추가:

**Triassic**: TRIAS, TRI, LTRI, LTRIAS, MTRI, MTRIAS, UTRI, UTRIAS, UTRIA
**Jurassic**: JUR, LJUR, MJUR, UJUR
**Cretaceous**: CRET, LCRET, UCRET
**Cenozoic extras**: PALEOG, PALEOGENE, NEOG, NEOGENE, NEO,
MIO, MIOC, MIOCENE, PLIO, PLIOC, PLEI, PLE, EOC, EOCENE, OLIG, PALEOCENE

→ `temporal_code_mya` 193개 (복합 코드 자동 생성 포함)
→ brachiobase v0.2.4 빌드 완료 (19,330 records, 400KB)

## 근본 문제 (추후 수정 필요)

`temporal_code_mya`는 trilobase, brachiobase, graptobase, chelicerobase,
ostracobase 모두에 있는 공통 테이블이지만, 소스인 paleocore `temporal_ranges`가
Mesozoic을 커버하지 못함.

ostracobase도 동일 문제: LCRET 18건, CRET 10건 등 Mesozoic taxa가 있으나 mya 매핑 없음.

**근본 수정**: paleocore의 `temporal_ranges`에 Mesozoic 코드 추가 →
각 taxonomy DB 빌드 시 자동으로 반영되도록 통일.

## 변경 파일

- `scripts/build_brachiobase_db.py` — UNION ALL Mesozoic 코드 33개 추가, VERSION→0.2.4
- `db/brachiobase-0.2.4.db` — 신규 DB
- `dist/brachiobase-0.2.4.scoda` — 신규 패키지 (400KB, 19,330 records, gitignore)
