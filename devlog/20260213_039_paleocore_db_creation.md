# Phase 31: PaleoCore DB 생성 스크립트

**날짜:** 2026-02-13
**유형:** 작업 로그

---

## 목표

`docs/paleocore_schema.md` 정의서를 기반으로 PaleoCore DB 생성 스크립트 구현.

## 작업 내용

### `scripts/create_paleocore.py` 구현

`trilobase.db`에서 8개 데이터 테이블을 추출하여 독립 `paleocore.db`를 생성하는 스크립트.

**데이터 테이블 (8개):**
- countries (142), geographic_regions (562), cow_states (244), country_cow_mapping (142)
- formations (2,004), temporal_ranges (28), ics_chronostrat (178), temporal_ics_mapping (40)
- 총 3,340 레코드

**변경 사항:**
- `taxa_count` 컬럼 제거: countries, geographic_regions, formations
- 나머지 5개 테이블: 그대로 복사

**SCODA 메타데이터 (6개 테이블):**
- artifact_metadata: 7건 (identity, version, license 등)
- provenance: 3건 (COW v2024, ICS GTS 2020, build pipeline)
- schema_descriptions: 88건 (8 데이터 테이블 + 6 SCODA 테이블 + 컬럼 설명)
- ui_display_intent: 4건 (countries, formations, chronostratigraphy, temporal_ranges)
- ui_queries: 8건 (countries_list, regions_list, formations_list 등)
- ui_manifest: 1건 (4개 뷰: countries, formations, chronostratigraphy, temporal_ranges)

**기능:**
- `--dry-run`: 미리보기 (파일 생성 안 함)
- `--source`: 소스 DB 경로 지정
- `--output`: 출력 DB 경로 지정
- FK integrity check (bulk insert 시 OFF, 이후 검증)
- taxa_count 컬럼 제거 검증

### 결과

```
paleocore.db: 328 KB, 14개 테이블, 3,340 데이터 레코드
FK integrity: 0 errors
taxa_count 제거: OK (3개 테이블)
```

## 새 파일

- `scripts/create_paleocore.py` — PaleoCore DB 생성 스크립트
- `paleocore.db` — 생성된 DB (`.gitignore`에 추가)
