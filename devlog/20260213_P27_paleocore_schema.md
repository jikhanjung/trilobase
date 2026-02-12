# Plan P27: PaleoCore 테이블 스키마 정의서 작성

**날짜:** 2026-02-13
**유형:** 계획(Plan) 문서
**목표:** PaleoCore 패키지 스키마를 구체적으로 정의하는 설계 문서 작성

---

## 배경

현재 Trilobase는 monolithic DB (`trilobase.db`)에 삼엽충 분류학 데이터와 지리/연대 인프라 데이터가 함께 들어 있다. SCODA 패키지 분리 아키텍처에 따라 **PaleoCore**(공유 인프라)와 **Trilobase**(분류학 도메인)를 분리해야 한다.

### 왜 분리하는가?

1. **재사용성**: 국가, 지층, 지질연대 데이터는 삼엽충뿐 아니라 모든 고생물학 프로젝트에서 사용 가능
2. **의존성 분리**: Trilobase가 PaleoCore를 참조하는 단방향 의존 (circular dependency 없음)
3. **독립 업데이트**: ICS 연대표, COW 국가 목록은 분류학 데이터와 무관하게 업데이트 가능
4. **SCODA 원칙 준수**: 각 패키지가 자기 완결적 아티팩트(self-contained artifact)로 기능

### 분리 대상

현재 `trilobase.db`의 20개 테이블 중:
- **8개 데이터 테이블** → PaleoCore로 이동 (countries, geographic_regions, cow_states, country_cow_mapping, formations, temporal_ranges, ics_chronostrat, temporal_ics_mapping)
- **11개 데이터 테이블** → Trilobase에 유지 (taxonomic_ranks, synonyms, bibliography, genus_locations, genus_formations, user_annotations 등)
- **6개 SCODA 메타데이터 테이블** → 양쪽 각자 보유 (artifact_metadata, provenance, schema_descriptions, ui_display_intent, ui_queries, ui_manifest)

---

## 설계 결정

### 1. `taxa_count` 컬럼 제거

현재 `countries`, `geographic_regions`, `formations`에 `taxa_count`가 있으나, 이 값은 Trilobase(소비자 패키지)의 genus 데이터에 의존한다. PaleoCore는 분류학과 무관한 인프라 패키지이므로 `taxa_count`를 제거하고, 소비자가 런타임에 JOIN으로 계산한다.

### 2. `formations` 텍스트 컬럼 유지

`formations.country`, `formations.region`, `formations.period`는 원본 Jell & Adrain (2002) 데이터에서 온 텍스트 필드다. 이들은 정규화된 FK가 아닌 참고용 텍스트이므로 PaleoCore에 그대로 유지한다. 향후 `formations.country_id` 같은 FK를 추가할 수 있으나 현 단계에서는 불필요.

### 3. Logical Foreign Key

패키지 간 FK는 SQLite FOREIGN KEY 제약으로 강제할 수 없다 (별도 .db 파일). 대신 **logical FK**로 문서화하고, 런타임에 `ATTACH`로 JOIN한다:

```python
conn.execute("ATTACH 'paleocore.db' AS pc")
# SELECT ... FROM genus_locations gl JOIN pc.countries c ON gl.country_id = c.id
```

### 4. `taxonomic_ranks`에서 레거시 컬럼 삭제

`country_id`, `formation_id`는 Phase 10에서 junction table(`genus_locations`, `genus_formations`)로 대체된 레거시 컬럼이다. PaleoCore 분리 시 이 컬럼들을 삭제한다.

### 5. SCODA 메타데이터 분배

각 패키지가 자기 완결적이므로, SCODA 메타데이터 6개 테이블은 양쪽에 각자 있되 내용이 다르다:
- **PaleoCore**: 지리/연대 관련 메타데이터만
- **Trilobase**: 분류학 관련 메타데이터만

---

## Deliverables

1. **`docs/paleocore_schema.md`** — PaleoCore 패키지 구체적 스키마 정의서
   - 테이블 분류 매핑표
   - 14개 테이블 전체 CREATE TABLE SQL
   - manifest.json 정의
   - SCODA 메타데이터 (artifact_metadata, provenance, schema_descriptions, ui_display_intent, ui_queries, ui_manifest)
   - Trilobase 변경 사항 요약
   - Logical Foreign Key 명세

2. **HANDOVER.md 갱신** — 현재 상태 반영

---

## 구현은 별도 단계

이번 작업은 **설계 문서 작성만**이 목표다. 실제 DB 분리, 마이그레이션 스크립트, 코드 수정은 후속 Phase에서 진행한다.
