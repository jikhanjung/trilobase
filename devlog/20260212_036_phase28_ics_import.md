# Phase 28: ICS Chronostratigraphic Chart 임포트 + temporal_ranges 매핑

**날짜:** 2026-02-12
**상태:** 완료

## 작업 내용

ICS 국제 지층 연대표(GTS 2020)를 DB에 임포트하고, 기존 `temporal_ranges` 28개 코드와 ICS 공식 지질시대를 매핑.

### 새 테이블

1. **`ics_chronostrat`** — ICS 지질시대 (자기 참조 계층)
   - 178개 concept (Super-Eon 1, Eon 4, Era 10, Period 22, Sub-Period 2, Epoch 37, Age 102)
   - URI, 이름, rank, parent_id (계층), start/end Ma + 불확실성, CCGM 코드, 색상, 정렬 순서, GSSP 비준 여부

2. **`temporal_ics_mapping`** — temporal_ranges ↔ ICS 매핑
   - 40행 (27개 코드 매핑, INDET는 unmappable)
   - 매핑 타입: exact(18), aggregate(17), partial(5)

### 매핑 타입 설명

| 타입 | 설명 | 예시 |
|------|------|------|
| exact | 1:1 대응 | MCAM → Miaolingian |
| partial | 1:many (코드가 ICS 단위의 부분집합) | LCAM → Terreneuvian + CambrianSeries2 |
| aggregate | 복합 코드 (여러 ICS 단위의 합) | MUCAM → Miaolingian + Furongian |
| unmappable | 대응 불가 | INDET |

### 파일 변경

| 파일 | 변경 |
|------|------|
| `vendor/ics/gts2020/chart.ttl` | 프로젝트 루트에서 이동 |
| `vendor/ics/gts2020/README.md` | 신규 (출처/라이선스 정보) |
| `scripts/import_ics.py` | 신규 (~310줄, rdflib 파싱) |
| `trilobase.db` | +2 테이블 (ics_chronostrat 178행, temporal_ics_mapping 40행) |
| `test_app.py` | +9 테스트 (ICS 계층, 매핑 검증) |

### DB 변경

- `ics_chronostrat`: 178행 삽입
- `temporal_ics_mapping`: 40행 삽입
- `provenance`: ICS 출처 1행 추가 (total 5)
- `schema_descriptions`: 20행 추가 (total 143 → 확인 필요)

## 기술적 세부사항

### rdflib 파싱

- `skos:Concept` 타입만 추출 (Collection 제외)
- `gts:rank` → rank 컬럼 (7종: Super-Eon, Eon, Era, Period, Sub-Period, Epoch, Age)
- `skos:prefLabel` (en) → name
- `skos:broader` → parent URI (2-pass: 1차 데이터 삽입, 2차 parent_id 업데이트)
- `time:hasBeginning/hasEnd` → blank node에서 `ischart:inMYA` + `sdo:marginOfError` 추출
- `skos:notation` (ccgmShortCode) → short_code
- `sdo:color` → color (hex)
- `sh:order` → display_order
- `gts:ratifiedGSSP` → ratified_gssp

### 계층 구조 검증

```
Phanerozoic (Eon)
  └── Paleozoic (Era)
        └── Cambrian (Period)
              ├── Terreneuvian (Epoch)
              │     ├── Fortunian (Age)
              │     └── Stage 2 (Age)
              ├── Series 2 (Epoch)
              │     ├── Stage 3 (Age)
              │     └── Stage 4 (Age)
              ├── Miaolingian (Epoch)
              │     ├── Wuliuan (Age)
              │     ├── Drumian (Age)
              │     └── Guzhangian (Age)
              └── Furongian (Epoch)
                    ├── Paibian (Age)
                    ├── Jiangshanian (Age)
                    └── Stage 10 (Age)
```

Root concepts (no parent): Phanerozoic (Eon), Precambrian (Super-Eon)

## 테스트

- 기존 120개 + 신규 9개 = **129개** (test_app.py)
- MCP 17개 변경 없음
- 총 **146개** 전부 통과

## 검증 기준

- [x] 178개 ICS concept 임포트 완료 (계획의 179는 추정치, 실제 TTL에 178개)
- [x] 계층 관계 정확 (parent_id 체인: Age → Epoch → Period → Era → Eon)
- [x] 28개 temporal_ranges 코드 전부 매핑 (INDET = unmappable)
- [x] 매핑 40행 (계획의 ~45는 추정치)
- [x] provenance 기록
- [x] schema_descriptions 갱신 (20항목)
- [x] 기존 테스트 + 신규 테스트 전부 통과
