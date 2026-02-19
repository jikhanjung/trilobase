# P24. Phase 28: ICS Chronostratigraphic Chart 임포트 + temporal_ranges 매핑

**날짜**: 2026-02-12
**상태**: 계획

## 배경

현재 `temporal_ranges` 테이블(28개 코드: LCAM, UCAM, LORD 등)은 Jell & Adrain (2002) 기반의 비공식 시대 구분.
ICS 국제 지층 연대표(chart.ttl, SKOS 형식, 179개 concept)를 DB에 넣어서 공식 지질시대 체계와 연결하면:
- 정밀한 연대(Ma) + 불확실성 제공
- 계층적 시대 탐색 (Eon → Era → Period → Epoch → Age)
- 국제 표준 URI 기반 상호운용성

이번 Phase는 **DB 임포트 + 매핑만** (API/UI는 다음 Phase).

## 새 테이블

### 1. `ics_chronostrat` — ICS 지질시대 (자기 참조 계층)

```sql
CREATE TABLE ics_chronostrat (
    id INTEGER PRIMARY KEY,
    ics_uri TEXT UNIQUE NOT NULL,     -- 'http://resource.geosciml.org/.../Cambrian'
    name TEXT NOT NULL,                -- 'Cambrian'
    rank TEXT NOT NULL,                -- 'Eon'|'Era'|'Period'|'Sub-Period'|'Epoch'|'Age'
    parent_id INTEGER,                 -- FK → ics_chronostrat.id
    start_mya REAL,                    -- 시작 (Ma)
    start_uncertainty REAL,            -- 시작 불확실성 (Ma)
    end_mya REAL,                      -- 종료 (Ma)
    end_uncertainty REAL,              -- 종료 불확실성 (Ma)
    short_code TEXT,                   -- CCGM 코드: 'Ep', 'O1', 'd3' 등
    color TEXT,                        -- ICS 표준 색상 '#7FA056'
    display_order INTEGER,             -- 정렬 순서 (sh:order)
    ratified_gssp INTEGER DEFAULT 0,   -- GSSP 비준 여부
    FOREIGN KEY (parent_id) REFERENCES ics_chronostrat(id)
);
CREATE INDEX idx_ics_chrono_parent ON ics_chronostrat(parent_id);
CREATE INDEX idx_ics_chrono_rank ON ics_chronostrat(rank);
```

전체 179개 concept 임포트 (COW처럼 완전성 유지).

### 2. `temporal_ics_mapping` — temporal_ranges ↔ ICS 매핑

```sql
CREATE TABLE temporal_ics_mapping (
    id INTEGER PRIMARY KEY,
    temporal_code TEXT NOT NULL,        -- FK → temporal_ranges.code
    ics_id INTEGER NOT NULL,           -- FK → ics_chronostrat.id
    mapping_type TEXT NOT NULL,         -- 'exact'|'partial'|'aggregate'|'unmappable'
    notes TEXT,
    FOREIGN KEY (ics_id) REFERENCES ics_chronostrat(id)
);
CREATE INDEX idx_tim_code ON temporal_ics_mapping(temporal_code);
CREATE INDEX idx_tim_ics ON temporal_ics_mapping(ics_id);
```

**매핑 타입:**
- `exact`: 1:1 대응 (MCAM → Miaolingian)
- `partial`: 1:many, 코드가 여러 ICS epoch의 일부를 포함 (LCAM → Terreneuvian + Series2)
- `aggregate`: 복합 코드 (MUCAM → Miaolingian + Furongian)
- `unmappable`: 대응 불가 (INDET)

## 핵심 매핑 정의

| Code | ICS Concept(s) | Type |
|------|----------------|------|
| LCAM | Terreneuvian, CambrianSeries2 | partial |
| MCAM | Miaolingian | exact |
| UCAM | Furongian | exact |
| MUCAM | Miaolingian, Furongian | aggregate |
| LMCAM | Terreneuvian, CambrianSeries2, Miaolingian | aggregate |
| CAM | Cambrian (Period) | exact |
| LORD | LowerOrdovician | exact |
| MORD | MiddleOrdovician | exact |
| UORD | UpperOrdovician | exact |
| LMORD | LowerOrdovician, MiddleOrdovician | aggregate |
| MUORD | MiddleOrdovician, UpperOrdovician | aggregate |
| ORD | Ordovician (Period) | exact |
| LSIL | Llandovery | exact |
| USIL | Wenlock, Ludlow, Pridoli | partial |
| LUSIL | Llandovery, Wenlock, Ludlow, Pridoli | aggregate |
| SIL | Silurian (Period) | exact |
| LDEV | LowerDevonian | exact |
| MDEV | MiddleDevonian | exact |
| UDEV | UpperDevonian | exact |
| EDEV | LowerDevonian | exact |
| LMDEV | LowerDevonian, MiddleDevonian | aggregate |
| MUDEV | MiddleDevonian, UpperDevonian | aggregate |
| MISS | Mississippian (Sub-Period) | exact |
| PENN | Pennsylvanian (Sub-Period) | exact |
| LPERM | Cisuralian | exact |
| PERM | Permian (Period) | exact |
| UPERM | Lopingian | exact |
| INDET | (없음) | unmappable |

총 ~45행 예상.

## 파일 구조

```
vendor/ics/gts2020/
├── chart.ttl              ← 프로젝트 루트에서 이동
└── README.md              ← 출처/라이선스 정보

scripts/
└── import_ics.py          ← 임포트 스크립트 (~400줄)
```

## 임포트 스크립트 (`scripts/import_ics.py`)

COW 패턴(`scripts/import_cow.py`) 따름:

```python
def parse_ttl(ttl_path):
    """rdflib로 chart.ttl 파싱, concept 리스트 반환"""

def create_ics_chronostrat(conn, concepts):
    """테이블 생성 + 2-pass 삽입 (1차: 데이터, 2차: parent_id)"""

def create_temporal_ics_mapping(conn):
    """수동 정의된 매핑 28개 코드 → ICS concept 연결"""

def add_provenance(conn):
    """provenance 테이블에 ICS 출처 추가"""

def update_schema_descriptions(conn):
    """schema_descriptions 갱신"""

def main():
    """--dry-run, --report 지원"""
```

**rdflib 파싱 핵심:**
- `skos:Concept` 타입인 것만 추출 (Collection 제외)
- `gts:rank` → rank 컬럼
- `skos:prefLabel` (en) → name
- `skos:broader` → parent URI (2차 패스에서 parent_id로 변환)
- `time:hasBeginning/hasEnd` → blank node에서 `ischart:inMYA` 추출
- `skos:notation` (ccgmShortCode) → short_code
- `sdo:color` → color
- `sh:order` → display_order

## 실행 순서

1. `vendor/ics/gts2020/` 디렉토리 생성, chart.ttl 이동
2. `pip install rdflib`
3. `scripts/import_ics.py` 작성
4. `python scripts/import_ics.py --dry-run` 으로 검증
5. `python scripts/import_ics.py` 실행
6. 테스트 추가 및 통과 확인
7. devlog/HANDOVER 갱신
8. 커밋

## 검증 기준

- 179개 ICS concept 임포트 완료
- 계층 관계 정확 (parent_id 체인: Age → Epoch → Period → Era → Eon)
- 28개 temporal_ranges 코드 전부 매핑 (INDET = unmappable)
- 매핑 행 ~45개
- provenance 기록
- schema_descriptions 갱신
- 기존 테스트 + 신규 테스트 전부 통과
