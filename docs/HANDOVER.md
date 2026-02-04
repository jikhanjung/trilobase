# Trilobase 프로젝트 Handover

**마지막 업데이트:** 2026-02-04

## 프로젝트 개요

삼엽충(trilobite) 분류학 데이터베이스 구축 프로젝트. Jell & Adrain (2002) PDF에서 추출한 genus 목록을 정제하여 데이터베이스화하는 것이 목표.

## 현재 상태

### 완료된 작업
- **Phase 1 완료**: 줄 정리 (한 genus = 한 줄)
  - Soft hyphen 제거 (1,357건)
  - 합쳐진 genera 분리 (56건)
  - Continuation 병합 (106건)
  - 빈 줄/깨진 줄 삭제 (16건)

- **Phase 2 완료**: 깨진 문자 및 오타 수정 (총 424건)
  - 체코어 저자명 복원: ŠNAJDR(85), PŘIBYL(145), VANĚK(118), RŮŽIČKA(12), KLOUČEK(9), NOVÁK(19)
  - 체코어 지명 복원: Šárka Fm(27), Třenice(4), Králův Dvůr Fm(1)
  - Genus 이름 수정: Šnajdria(1)
  - 오타 수정: Glabrella, Natalina, Strenuella 쉼표 제거(3)
  - 불완전 엔트리 복원: Actinopeltis(1)

- **Phase 3 완료**: 데이터 검증
  - 형식 일관성 검사 완료 (괄호/대괄호 짝 맞춤, 세미콜론 구분자)
  - 데이터 무결성 검사 완료 (연도 범위, 시대 코드, Family 이름 유효성)
  - 중복 genus 확인 완료 (명명법적 복잡성 이해)

- **Phase 4 완료**: DB 스키마 설계 및 데이터 임포트
  - SQLite 데이터베이스 생성 (`trilobase.db`)
  - 총 taxa: 5,113 / 유효 taxa: 4,457
  - Synonym 레코드: 899
  - 고유 Family: 186

- **Phase 5 완료**: 데이터베이스 정규화
  - formations 테이블 생성 (1,987 records)
  - countries 테이블 생성 (151 records)
  - Synonym 관계 연결 (814/899 = 90.5%)
  - Taxa-country 연결 (4,733/5,113 = 92.6%)
  - Taxa-formation 연결 (4,781/5,113 = 93.5%)

### 파일 구조
```
trilobase/
├── trilobase.db                      # SQLite 데이터베이스
├── trilobite_genus_list.txt          # 최신 버전 (항상 이 파일 수정)
├── trilobite_genus_list_original.txt # 원본 백업
├── trilobite_genus_list_structure_fixed.txt  # Phase 1 완료 시점
├── trilobite_family_list.txt         # Family 목록 (미처리)
├── trilobite_nomina_nuda.txt         # Nomina nuda (미처리)
├── Jell_and_Adrain_2002_Literature_Cited.txt  # 참고문헌
├── scripts/
│   ├── normalize_lines.py            # 줄 정규화 스크립트
│   ├── create_database.py            # DB 생성 스크립트
│   └── normalize_database.py         # DB 정규화 스크립트
├── devlog/
│   ├── 20260204_P01_data_cleaning_plan.md
│   ├── 20260204_001_phase1_line_normalization.md
│   ├── 20260204_002_phase2_character_fixes.md
│   ├── 20260204_003_phase3_data_validation_summary.md
│   ├── 20260204_004_phase4_database_creation.md
│   └── 20260204_005_phase5_normalization.md
└── CLAUDE.md
```

## 다음 작업 (Phase 6: 상위 분류군 통합)

### 작업 대상
1. **Family 테이블 생성**: 186개 Family 정규화
2. **Order 데이터 추가**: Family를 Order로 그룹화
3. **계층 구조 완성**: taxa → Family → Order 관계

### 미해결 항목
- 현재 없음

## 전체 계획

1. ~~Phase 1: 줄 정리~~ ✅
2. ~~Phase 2: 깨진 문자 및 오타 수정~~ ✅
3. ~~Phase 3: 데이터 검증~~ ✅
4. ~~Phase 4: DB 스키마 설계 및 데이터 임포트~~ ✅
5. ~~Phase 5: 정규화 (Formation, Location, Synonym)~~ ✅
6. Phase 6: 상위 분류군 통합 (Family, Order)

## DB 스키마 (구현됨)

```sql
-- taxa: 5,113 records
taxa (id, name, author, year, year_suffix, type_species,
      type_species_author, formation, location, family,
      temporal_code, is_valid, notes, raw_entry, created_at,
      country_id, formation_id)

-- synonyms: 899 records (814 linked)
synonyms (id, junior_taxon_id, senior_taxon_name, senior_taxon_id,
          synonym_type, fide_author, fide_year, notes)

-- formations: 1,987 records
formations (id, name, normalized_name, formation_type,
            country, region, period, taxa_count)

-- countries: 151 records
countries (id, name, code, taxa_count)

-- temporal_ranges: 28 records
temporal_ranges (id, code, name, period, epoch, start_mya, end_mya)
```

## DB 사용법

```bash
# 기본 쿼리
sqlite3 trilobase.db "SELECT * FROM taxa LIMIT 10;"

# Family별 통계
sqlite3 trilobase.db "SELECT family, COUNT(*) FROM taxa GROUP BY family ORDER BY 2 DESC;"

# 특정 속 검색
sqlite3 trilobase.db "SELECT * FROM taxa WHERE name LIKE 'Asaph%';"
```

## 주의사항

- `trilobite_genus_list.txt`가 항상 최신 버전
- 각 Phase 완료 시 반드시 git commit
- 중간 과정 파일은 `_원본명_단계명.txt` 형식으로 보존
- 원본 PDF 필요 시: Jell & Adrain (2002)
