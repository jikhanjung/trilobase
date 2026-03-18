# 데이터베이스 스키마

Trilobase는 **3-데이터베이스 아키텍처**를 사용합니다:

1. **정본 DB** (`trilobita.db`) — 읽기 전용, 불변 분류학 데이터
2. **오버레이 DB** (`trilobita_overlay.db`) — 읽기/쓰기 사용자 주석
3. **PaleoCore DB** (`paleocore.db`) — 공유 지리/층서 참조 데이터

```python
conn = sqlite3.connect('db/trilobita.db')
conn.execute("ATTACH DATABASE 'dist/trilobita_overlay.db' AS overlay")
conn.execute("ATTACH DATABASE 'db/paleocore.db' AS pc")
```

---

## 정본 DB (trilobita.db)

### taxonomic_ranks

통합 분류 계층 — 5,341건 (Class~Genus + 플레이스홀더 2 + Suborder 1).

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | INTEGER | 기본키 |
| name | TEXT | 분류군명 |
| rank | TEXT | 분류 계급 (Class, Order, Suborder, Superfamily, Family, Genus) |
| parent_id | INTEGER | 상위 분류군 FK |
| author | TEXT | 명명 저자 |
| year | INTEGER | 기재 연도 |
| year_suffix | TEXT | 동일 저자-연도 구분용 접미사 |
| genera_count | INTEGER | 소속 속 수 (상위 분류군용) |
| notes | TEXT | 비고 |
| created_at | TEXT | 레코드 생성 시각 |
| type_species | TEXT | 모식종 (Genus 전용) |
| type_species_author | TEXT | 모식종 명명 저자 (Genus 전용) |
| formation | TEXT | 모식 지층 텍스트 (Genus 전용) |
| location | TEXT | 모식 산지 텍스트 (Genus 전용) |
| family | TEXT | 과명 텍스트 (Genus 전용) |
| temporal_code | TEXT | 시대 코드 (Genus 전용) |
| is_valid | INTEGER | 1 = 유효, 0 = 무효 (Genus 전용) |
| raw_entry | TEXT | 원본 텍스트 (Genus 전용) |

### synonyms (뷰)

`taxonomic_opinions`에 대한 하위 호환 뷰 — SYNONYM_OF 행을 레거시 스키마로 노출. 1,055행.

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | INTEGER | opinion id |
| junior_taxon_id | INTEGER | 이차 동의어 FK (taxonomic_ranks) |
| senior_taxon_name | TEXT | 선취 동의어명 |
| senior_taxon_id | INTEGER | 선취 동의어 FK (taxonomic_ranks) |
| synonym_type | TEXT | 유형: j.s.s., j.o.s., preocc. |
| fide_author | TEXT | "~에 따르면" 저자 |
| fide_year | INTEGER | "~에 따르면" 연도 |
| notes | TEXT | 비고 |

### genus_formations

속-지층 다대다 관계 — 4,853건.

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | INTEGER | 기본키 |
| genus_id | INTEGER | taxonomic_ranks FK |
| formation_id | INTEGER | pc.formations FK |
| is_type_locality | INTEGER | 모식 산지 여부 |
| notes | TEXT | 비고 |

### genus_locations

속-국가 다대다 관계 — 4,841건.

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | INTEGER | 기본키 |
| genus_id | INTEGER | taxonomic_ranks FK |
| country_id | INTEGER | pc.countries FK |
| region | TEXT | 하위 지역 |
| is_type_locality | INTEGER | 모식 산지 여부 |
| notes | TEXT | 비고 |

### bibliography

참고문헌 — 2,130건.

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | INTEGER | 기본키 |
| authors | TEXT | 저자 |
| year | INTEGER | 출판 연도 |
| year_suffix | TEXT | 동일 연도 구분 접미사 |
| title | TEXT | 논문/장 제목 |
| journal | TEXT | 학술지명 |
| volume | TEXT | 권 |
| pages | TEXT | 페이지 범위 |
| publisher | TEXT | 출판사 |
| city | TEXT | 출판 도시 |
| editors | TEXT | 편집자 |
| book_title | TEXT | 도서 제목 (장의 경우) |
| reference_type | TEXT | article, book, chapter |
| raw_entry | TEXT | 원본 인용문 |

### taxon_bibliography

분류군-참고문헌 FK 연결 — 4,040건.

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | INTEGER | 기본키 |
| taxon_id | INTEGER | taxonomic_ranks FK |
| bibliography_id | INTEGER | bibliography FK |
| relationship_type | TEXT | original_description, fide |
| opinion_id | INTEGER | taxonomic_opinions FK (동의어를 통한 경우) |
| match_confidence | REAL | 매칭 신뢰도 |
| match_method | TEXT | 매칭 방법 |
| notes | TEXT | 비고 |
| created_at | TEXT | 생성 시각 |

### taxonomic_opinions

분류학적 의견 — 1,139건 (PLACED_IN 82 + SPELLING_OF 2 + SYNONYM_OF 1,055).

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | INTEGER | 기본키 |
| taxon_id | INTEGER | taxonomic_ranks FK |
| opinion_type | TEXT | PLACED_IN, SPELLING_OF, SYNONYM_OF |
| related_taxon_id | INTEGER | 관련 분류군 FK |
| synonym_type | TEXT | j.s.s., j.o.s., preocc., replacement, suppressed (SYNONYM_OF 전용) |
| proposed_valid | INTEGER | 유효 제안 여부 |
| bibliography_id | INTEGER | bibliography FK |
| assertion_status | TEXT | asserted, incertae_sedis, indet, questionable |
| curation_confidence | TEXT | 확신도 |
| is_accepted | INTEGER | 현재 채택 여부 |
| notes | TEXT | 비고 |
| created_at | TEXT | 생성 시각 |

### taxa (뷰)

하위 호환을 위한 뷰. Genus rank 레코드만 노출.

```sql
CREATE VIEW taxa AS SELECT ... FROM taxonomic_ranks WHERE rank = 'Genus';
```

---

## SCODA 메타데이터 테이블

| 테이블 | 설명 |
|--------|------|
| artifact_metadata | 아티팩트 신원 (이름, 버전 등) 키-값 쌍 |
| provenance | 인용 및 설명이 포함된 데이터 출처 |
| schema_descriptions | 테이블 및 컬럼에 대한 사람이 읽을 수 있는 설명 |
| ui_display_intent | UI 렌더링을 위한 뷰 타입 힌트 |
| ui_queries | 파라미터 정의가 포함된 이름 있는 SQL 쿼리 |
| ui_manifest | 선언적 UI 뷰 정의 (JSON) |

---

## 오버레이 DB (trilobita_overlay.db)

### overlay_metadata

이 오버레이가 연결된 정본 DB 버전을 추적합니다.

| 컬럼 | 타입 | 설명 |
|------|------|------|
| key | TEXT | 메타데이터 키 (canonical_version, created_at) |
| value | TEXT | 메타데이터 값 |

### user_annotations

데이터베이스 업데이트 시에도 보존되는 사용자 주석.

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | INTEGER | 기본키 |
| entity_type | TEXT | 주석 대상 엔티티 타입 |
| entity_id | INTEGER | 주석 대상 엔티티 ID |
| entity_name | TEXT | 릴리스 간 매칭용 이름 |
| annotation_type | TEXT | 주석 유형 |
| content | TEXT | 주석 내용 |
| author | TEXT | 주석 작성자 |
| created_at | TEXT | 생성 시각 |
