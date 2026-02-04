# Phase 5: 데이터베이스 정규화

**작업일:** 2026-02-04

## 결과 요약

### 새로 생성된 테이블

#### formations (1,987 records)
| formation_type | 개수 |
|----------------|------|
| Formation | 903 |
| (unclassified) | 616 |
| Limestone | 179 |
| Zone | 83 |
| Horizon | 78 |
| Shale | 77 |
| Beds | 42 |
| Group | 8 |
| Suite | 1 |

#### countries (151 records)
Top 10 국가별 taxa 수:
1. China (1,055)
2. USA (654)
3. Russia (580)
4. Canada (312)
5. Czech Republic (297)
6. Australia (220)
7. Germany (188)
8. Sweden (146)
9. Kazakhstan (141)
10. Argentina (124)

### 관계 연결

#### Synonym 연결
- 총 synonyms: 899
- senior_taxon_id 연결됨: 814 (90.5%)
- 미연결: 85 (데이터 품질 이슈 - 하이픈, 추가 텍스트 등)

#### Taxa 참조 연결
- country_id 연결: 4,733/5,113 (92.6%)
- formation_id 연결: 4,781/5,113 (93.5%)

### 추가된 인덱스
- idx_taxa_country
- idx_taxa_formation_id
- idx_synonyms_senior
- idx_formations_type
- idx_countries_name

## 최종 데이터베이스 구조

```sql
-- taxa: 5,113 records
taxa (id, name, author, year, year_suffix, type_species,
      type_species_author, formation, location, family,
      temporal_code, is_valid, notes, raw_entry, created_at,
      country_id, formation_id)  -- 새로 추가

-- synonyms: 899 records
synonyms (id, junior_taxon_id, senior_taxon_name,
          synonym_type, fide_author, fide_year, notes,
          senior_taxon_id)  -- 새로 추가

-- formations: 1,987 records (새 테이블)
formations (id, name, normalized_name, formation_type,
            country, region, period, taxa_count)

-- countries: 151 records (새 테이블)
countries (id, name, code, taxa_count)

-- temporal_ranges: 28 records
temporal_ranges (id, code, name, period, epoch, start_mya, end_mya)
```

## 파일
- `scripts/normalize_database.py` - 정규화 스크립트
