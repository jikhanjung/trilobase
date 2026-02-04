# Phase 4: DB 스키마 설계 및 데이터 임포트

**작업일:** 2026-02-04

## 결과 요약

### 데이터베이스 통계
- **총 taxa**: 5,113
- **유효 taxa**: 4,457
- **Synonym 레코드**: 899
- **고유 Family**: 186

### 테이블 구조

#### taxa
| 컬럼 | 설명 |
|------|------|
| id | Primary key |
| name | 속명 |
| author | 저자 |
| year | 기재 연도 |
| year_suffix | 연도 접미사 (a, b, c...) |
| type_species | 모식종 |
| type_species_author | 모식종 저자 |
| formation | 지층 |
| location | 산지 |
| family | 과 |
| temporal_code | 시대 코드 |
| is_valid | 유효성 (1=유효, 0=이명) |
| raw_entry | 원본 텍스트 |

#### synonyms
| 컬럼 | 설명 |
|------|------|
| id | Primary key |
| junior_taxon_id | 이명 taxa ID |
| senior_taxon_name | 선취명 이름 |
| synonym_type | 이명 유형 |
| fide_author | 출처 저자 |
| fide_year | 출처 연도 |

#### temporal_ranges
| 컬럼 | 설명 |
|------|------|
| code | 시대 코드 (LCAM, MCAM 등) |
| name | 전체 이름 |
| period | 기 (Period) |
| epoch | 세 (Epoch) |
| start_mya | 시작 (백만년 전) |
| end_mya | 종료 (백만년 전) |

## 주요 통계

### Top 10 Families
1. PROETIDAE (346)
2. ASAPHIDAE (185)
3. PTYCHOPARIIDAE (183)
4. STYGINIDAE (115)
5. SOLENOPLEURIDAE (102)
6. CHEIRURIDAE (101)
7. OLENIDAE (86)
8. ELLIPSOCEPHALIDAE (83)
9. PROASAPHISCIDAE (80)
10. REMOPLEURIDIDAE (77)

### 시대별 분포
1. UCAM - Upper Cambrian (967)
2. MCAM - Middle Cambrian (933)
3. LCAM - Lower Cambrian (640)
4. LORD - Lower Ordovician (509)
5. UORD - Upper Ordovician (401)

### 이명 유형
- j.s.s. (junior subjective synonym): 595
- replacement: 124
- preocc. (preoccupied): 118
- j.o.s. (junior objective synonym): 53
- suppressed: 9

## 파일
- `scripts/create_database.py` - DB 생성 스크립트
- `trilobase.db` - SQLite 데이터베이스
