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
  - 체코어 저자명 복원: ŠNAJDR, PŘIBYL, VANĚK, RŮŽIČKA, KLOUČEK, NOVÁK
  - 체코어 지명 복원: Šárka Fm, Třenice, Králův Dvůr Fm
  - Genus 이름 수정, 오타 수정

- **Phase 3 완료**: 데이터 검증
  - 형식 일관성 검사 (괄호/대괄호 짝 맞춤)
  - 데이터 무결성 검사 (연도 범위, 시대 코드)

- **Phase 4 완료**: DB 스키마 설계 및 데이터 임포트
  - SQLite 데이터베이스 생성 (`trilobase.db`)

- **Phase 5 완료**: 데이터베이스 정규화
  - Synonym 파싱 개선 (97.7% 연결)
  - is_valid 분류 개선
  - Location/Formation 파싱 개선
  - formations, countries 테이블 생성

### 데이터베이스 현황

| 항목 | 값 | 비율 |
|------|-----|------|
| **총 Taxa** | 5,113 | 100% |
| 유효 Taxa | 4,258 | 83.3% |
| 무효 Taxa | 855 | 16.7% |
| **Synonym** | 1,055 | |
| Synonym 연결됨 | 1,031 | 97.7% |
| **Location** | 4,847 | 94.8% |
| Country 연결됨 | 4,841 | 99.9% |
| **Formation** | 4,854 | 95.0% |
| Formation 연결됨 | 4,854 | 100% |

### 파일 구조

```
trilobase/
├── trilobase.db                      # SQLite 데이터베이스
├── trilobite_genus_list.txt          # 정제된 genus 목록
├── trilobite_genus_list_original.txt # 원본 백업
├── unlinked_synonyms.txt             # 미연결 synonym (4건)
├── unlinked_taxa_no_location.txt     # Location 없는 taxa (266건)
├── unlinked_taxa_no_formation.txt    # Formation 없는 taxa (259건)
├── scripts/
│   ├── normalize_lines.py            # 줄 정규화 스크립트
│   ├── create_database.py            # DB 생성 스크립트
│   ├── normalize_database.py         # DB 정규화 스크립트
│   └── fix_synonyms.py               # Synonym 파싱 개선 스크립트
├── devlog/
│   ├── 20260204_P01_data_cleaning_plan.md
│   ├── 20260204_001_phase1_line_normalization.md
│   ├── 20260204_002_phase2_character_fixes.md
│   ├── 20260204_003_phase3_data_validation_summary.md
│   ├── 20260204_004_phase4_database_creation.md
│   └── 20260204_005_phase5_normalization.md
├── docs/
│   └── HANDOVER.md
└── CLAUDE.md
```

## 다음 작업 (Phase 6: 상위 분류군 통합)

### 작업 대상
1. **Family 테이블 생성**: 186개 Family 정규화
2. **Order 데이터 추가**: Family를 Order로 그룹화
3. **계층 구조 완성**: taxa → Family → Order 관계

### 미해결 항목
- Synonym 미연결 4건 (원본에 senior taxa 없음)
- Location/Formation 없는 taxa는 모두 무효 taxa (정상)

## 전체 계획

1. ~~Phase 1: 줄 정리~~ ✅
2. ~~Phase 2: 깨진 문자 및 오타 수정~~ ✅
3. ~~Phase 3: 데이터 검증~~ ✅
4. ~~Phase 4: DB 스키마 설계 및 데이터 임포트~~ ✅
5. ~~Phase 5: 정규화 (Formation, Location, Synonym)~~ ✅
6. Phase 6: 상위 분류군 통합 (Family, Order)

## DB 스키마

```sql
-- taxa: 5,113 records
taxa (id, name, author, year, year_suffix, type_species,
      type_species_author, formation, location, family,
      temporal_code, is_valid, notes, raw_entry, created_at,
      country_id, formation_id)

-- synonyms: 1,055 records
synonyms (id, junior_taxon_id, senior_taxon_name, senior_taxon_id,
          synonym_type, fide_author, fide_year, notes)

-- formations: 1,987+ records
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

# 유효 taxa만 조회
sqlite3 trilobase.db "SELECT * FROM taxa WHERE is_valid = 1;"

# Family별 통계
sqlite3 trilobase.db "SELECT family, COUNT(*) FROM taxa WHERE is_valid=1 GROUP BY family ORDER BY 2 DESC;"

# 국가별 통계
sqlite3 trilobase.db "SELECT c.name, c.taxa_count FROM countries c ORDER BY taxa_count DESC LIMIT 10;"

# 특정 속과 원본 텍스트 확인
sqlite3 trilobase.db "SELECT name, raw_entry FROM taxa WHERE name LIKE 'Asaph%';"

# Synonym 관계 조회
sqlite3 trilobase.db "SELECT t1.name as junior, t2.name as senior, s.synonym_type
FROM synonyms s
JOIN taxa t1 ON s.junior_taxon_id = t1.id
JOIN taxa t2 ON s.senior_taxon_id = t2.id
LIMIT 10;"
```

## 주의사항

- `trilobite_genus_list.txt`가 항상 최신 텍스트 버전
- `trilobase.db`가 최신 데이터베이스
- 각 Phase 완료 시 git commit
- 원본 PDF 필요 시: Jell & Adrain (2002)
