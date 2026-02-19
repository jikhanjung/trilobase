# Phase 5: 데이터베이스 정규화

**작업일:** 2026-02-04

## 결과 요약

### 최종 데이터베이스 통계

| 항목 | 값 | 비율 |
|------|-----|------|
| 총 Taxa | 5,113 | 100% |
| 유효 Taxa | 4,258 | 83.3% |
| 무효 Taxa | 855 | 16.7% |

### 테이블별 현황

#### taxa (5,113 records)
- Location 있음: 4,847 (94.8%)
- Formation 있음: 4,854 (95.0%)
- Country 연결됨: 4,841 (99.9%)
- Formation 연결됨: 4,854 (100%)

#### synonyms (1,055 records)
- Senior taxa 연결됨: 1,031 (97.7%)
- 미연결: 4건 (원본에 senior taxa 없음)

#### formations (1,987+ records)
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

## 수행한 작업

### 1. Synonym 파싱 개선
- 세미콜론으로 구분된 복합 synonym 처리
- 하이픈 제거 (Meta-doxides → Metadoxides)
- 괄호 별칭 처리 (Selenoharpes (=Scotoharpes) → Scotoharpes)
- 대소문자 불일치 해결
- **결과**: 90.5% → 97.7% 연결률

### 2. is_valid 분류 개선
- preocc., misspelling, emendation, error 등 무효 처리
- **결과**: 유효 4,457 → 4,258 (정확도 향상)

### 3. Location/Formation 파싱 개선
- 비표준 Family 패턴 처리 (??FAMILY, FAMILY UNCERTAIN)
- 114건 추가 파싱
- **결과**: 유효 taxa 중 미연결 0건

### 4. 관계 테이블 생성 및 연결
- formations 테이블 생성
- countries 테이블 생성
- foreign key 연결 (country_id, formation_id, senior_taxon_id)

## 미연결 사례

### Synonym 미연결 (4건)
원본 데이터에 senior taxa가 수록되지 않음:
- Actinopeltis → Grinellaspis
- Liocephalus → Bailliella
- Macroculites → Parakoldinoidia
- Schmidtella → Tschernyschewella

### Location/Formation 없음
- 모두 무효 taxa (is_valid=0)
- 원본 데이터에 산지/지층 정보 없음 (정상)

## 생성된 파일
- `scripts/fix_synonyms.py` - Synonym 파싱 개선 스크립트
- `unlinked_synonyms.txt` - 미연결 synonym 목록 (4건)
- `unlinked_taxa_no_location.txt` - Location 없는 taxa (266건, 모두 무효)
- `unlinked_taxa_no_formation.txt` - Formation 없는 taxa (259건, 모두 무효)
