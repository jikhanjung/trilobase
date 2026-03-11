# 122: HANDOFF.md + CLAUDE.md — 0.3.0 통합 반영

**날짜**: 2026-03-11

## 요약

devlog 121에서 trilobase-assertion → trilobase 0.3.0 통합을 완료했으나, HANDOFF.md와 CLAUDE.md가 이전 구조(canonical DB 0.2.6, assertion DB 별도)를 기술하고 있었음. 현재 상태에 맞게 전면 갱신.

## HANDOFF.md 변경

### Current Status 테이블
- Trilobase version: 0.2.6 → **0.3.0**
- taxonomic_ranks 5,341 → taxon 5,627, assertion 8,382, reference 2,135 등 assertion-centric 수치로 교체
- classification_edge_cache, classification_profile 추가

### Database Status
- 기존 canonical DB 스키마(taxonomic_ranks, bibliography, taxonomic_opinions 등) → assertion-centric 스키마(taxon, assertion, reference, classification_profile, classification_edge_cache 등)로 전면 교체
- Overlay DB 섹션 제거 (별도 관리)
- Legacy canonical DB: `trilobase-canonical-0.2.6.db` 보존 명시

### Build Pipeline
- 새 스크립트 이름 반영: `build_trilobase_db.py`, `build_trilobase_scoda.py`, `validate_trilobase_db.py`, `build_all.py`
- Admin 모드 실행 명령 갱신 (`trilobase-0.3.0.db`)

### History 섹션
- P72~P80, Treatise 1959/2004, Profile Comparison, Source-Driven Build, 0.3.0 통합을 압축 정리
- 개별 Phase 상세 내용 → 요약 + devlog 링크로 축소

### File Structure
- `scripts/`: 활성 스크립트 7개만 표시 (60+ 레거시 → `archive/`)
- `db/`: `trilobase-0.3.0.db` 메인, `trilobase-canonical-0.2.6.db` 보존
- `data/sources/` 추가
- `docs/canonical_vs_assertion.md`, `source_data_guide.md` 추가

### DB Schema
- canonical 스키마 → assertion-centric 스키마로 전면 교체
- DB Usage Examples 제거 (구 스키마 기반이라 오해 소지)

### 기타
- 완료된 UI/Manifest 태스크 목록 유지 (~~strikethrough~~)
- Next Tasks에 P84 (Tree Search + Watch) 추가
- Notes 섹션: 소스 경로, DB 경로 갱신

## CLAUDE.md 변경

### Repository Structure
- `db/`: `trilobase-0.3.0.db` 메인, `trilobase-canonical-0.2.6.db` 보존
- `data/sources/` 추가, 불필요 항목 제거
- `scripts/`: 새 스크립트 이름 반영
- `docs/`: `canonical_vs_assertion.md`, `source_data_guide.md` 추가

## 삭제된 내용 (−474줄)

대부분 0.3.0 통합으로 불필요해진 중간 버전 상세 기록:
- P74 assertion-centric test DB 상세 테이블
- P76~P80 개별 Phase 상세 내용
- Assertion DB v0.1.5~v0.2.0 버전별 변경 내역
- R01/R02 설계 리뷰 전문 (→ 링크로 대체)
- 구 canonical DB 스키마 + Usage Examples
