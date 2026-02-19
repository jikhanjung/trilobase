# Phase 13: SCODA-Core 메타데이터 구현 완료

**날짜:** 2026-02-07
**브랜치:** `feature/scoda-implementation`
**커밋:** `dffd912`

## 작업 내용

SCODA(Self-Contained Data Artifact) 프레임워크의 필수 요소(SCODA-Core)를 trilobase.db에 구현.
DB 파일 하나만으로 "이 아티팩트가 무엇인지" 스스로 설명할 수 있게 되었음.

## 새 테이블 (3개)

### artifact_metadata (7건)
아티팩트의 신원 정보 (key-value).

| key | value |
|-----|-------|
| artifact_id | trilobase |
| name | Trilobase |
| version | 1.0.0 |
| schema_version | 1.0 |
| created_at | 2026-02-07 |
| description | Trilobite genus-level taxonomy database... |
| license | CC-BY-4.0 |

### provenance (3건)
데이터 출처 기록.

| source_type | citation | year |
|-------------|----------|------|
| primary | Jell & Adrain (2002) | 2002 |
| supplementary | Adrain (2011) | 2011 |
| build | Trilobase data pipeline (2026) | 2026 |

### schema_descriptions (90건)
모든 테이블과 컬럼에 대한 설명을 DB 안에 기록.
SCODA 자체 테이블(artifact_metadata, provenance, schema_descriptions)도 포함.

## 새 API 엔드포인트 (2개)

- `GET /api/metadata` — 아티팩트 메타데이터 + DB 통계 (genus/family/order 수, valid_genera, synonyms, bibliography 등)
- `GET /api/provenance` — 출처 목록

## 파일 변경

| 파일 | 변경 |
|------|------|
| `scripts/add_scoda_tables.py` | **신규** — 마이그레이션 스크립트 |
| `app.py` | 수정 — 2개 엔드포인트 추가 |
| `test_app.py` | 수정 — SCODA 테이블 fixture + 10개 테스트 추가 |
| `trilobase.db` | 수정 — 3개 테이블 추가 |

## 테스트

- 기존 37개 + 신규 10개 = **47개 전체 통과**
- TestApiMetadata (5개): identity, license, statistics 구조/값 검증
- TestApiProvenance (5개): 목록, primary/supplementary source, 레코드 구조 검증
