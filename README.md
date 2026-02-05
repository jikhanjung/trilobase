# Trilobase

삼엽충(Trilobite) 분류학 데이터베이스 프로젝트

## 개요

Trilobase는 Jell & Adrain (2002) "Available Generic Names for Trilobites"를 기반으로 구축한 삼엽충 속(genus) 수준의 분류학 데이터베이스입니다. 원본 PDF에서 추출한 데이터를 정제, 정규화하여 SQLite 데이터베이스로 구축하고, Flask 기반 웹 인터페이스를 통해 탐색할 수 있습니다.

### 데이터 출처

- **Jell, P.A. & Adrain, J.M. (2002)**. Available Generic Names for Trilobites. *Memoirs of the Queensland Museum* 48(2): 331-553.
- **Adrain, J.M. (2011)**. Class Trilobita Walch, 1771. In: Zhang, Z.-Q. (Ed.) Animal biodiversity: An outline of higher-level classification and survey of taxonomic richness. *Zootaxa* 3148: 104-109.

## 데이터베이스 통계

| 분류 계급 | 개수 |
|-----------|------|
| Class | 1 |
| Order | 12 |
| Suborder | 8 |
| Superfamily | 13 |
| Family | 191 |
| Genus | 5,113 |
| **총계** | **5,338** |

### Genus 상세

- 유효(Valid) Genus: 4,258개 (83.3%)
- 무효(Invalid) Genus: 855개 (16.7%)
- 동의어(Synonym) 관계: 1,055건
- 참고문헌: 2,130건

## 설치 및 실행

### 요구사항

- Python 3.8+
- Flask

### 설치

```bash
git clone https://github.com/yourusername/trilobase.git
cd trilobase
pip install flask
```

### 웹 서버 실행

```bash
python app.py
```

브라우저에서 http://localhost:8080 접속

## 웹 인터페이스 기능

- **Tree View**: Class → Order → Suborder → Superfamily → Family 계층 구조 탐색
- **Genus List**: Family 선택 시 해당 속 목록 표시
- **Genus Detail**: 각 속의 상세 정보 (저자, 연도, 모식종, 산지, 지층, 동의어 등)
- **필터링**: 유효 분류군만 표시 옵션
- **Expand/Collapse**: 트리 전체 펼치기/접기

## 데이터베이스 스키마

### 주요 테이블

```
taxonomic_ranks     # 통합 분류 체계 (Class~Genus) - 5,338건
├── id, name, rank, parent_id
├── author, year, year_suffix
├── genera_count, notes
└── (Genus 전용) type_species, formation, location, is_valid, ...

synonyms            # 동의어 관계 - 1,055건
├── junior_taxon_id, senior_taxon_id
└── synonym_type, fide_author, fide_year

genus_formations    # Genus-Formation 관계 - 4,854건
genus_locations     # Genus-Country 관계 - 4,841건
formations          # 지층 정보 - 2,009건
countries           # 국가 정보 - 151건
temporal_ranges     # 지질시대 코드 - 28건
bibliography        # 참고문헌 - 2,130건
```

### 예제 쿼리

```bash
# 유효 Genus 목록
sqlite3 trilobase.db "SELECT name, author, year FROM taxonomic_ranks
                      WHERE rank='Genus' AND is_valid=1 LIMIT 10;"

# 특정 Genus의 전체 분류 계층
sqlite3 trilobase.db "
SELECT g.name as genus, f.name as family, o.name as 'order'
FROM taxonomic_ranks g
LEFT JOIN taxonomic_ranks f ON g.parent_id = f.id
LEFT JOIN taxonomic_ranks sf ON f.parent_id = sf.id
LEFT JOIN taxonomic_ranks o ON sf.parent_id = o.id
WHERE g.name = 'Paradoxides';"

# 특정 국가의 Genus 조회
sqlite3 trilobase.db "
SELECT g.name, gl.region
FROM taxonomic_ranks g
JOIN genus_locations gl ON g.id = gl.genus_id
JOIN countries c ON gl.country_id = c.id
WHERE c.name = 'China' LIMIT 10;"
```

## 프로젝트 구조

```
trilobase/
├── trilobase.db                  # SQLite 데이터베이스
├── app.py                        # Flask 웹 애플리케이션
├── templates/
│   └── index.html                # 메인 페이지
├── static/
│   ├── css/style.css
│   └── js/app.js
├── scripts/                      # 데이터 처리 스크립트
│   ├── normalize_lines.py
│   ├── create_database.py
│   ├── normalize_database.py
│   └── ...
├── trilobite_genus_list.txt      # 정제된 원본 데이터
├── trilobite_genus_list_original.txt  # 원본 백업
├── devlog/                       # 작업 로그
└── docs/
    └── HANDOVER.md               # 인수인계 문서
```

## 데이터 형식

### 지질시대 코드

| 코드 | 의미 |
|------|------|
| LCAM/MCAM/UCAM | Lower/Middle/Upper Cambrian |
| LORD/MORD/UORD | Lower/Middle/Upper Ordovician |
| LSIL/USIL | Lower/Upper Silurian |
| LDEV/MDEV/UDEV | Lower/Middle/Upper Devonian |
| MISS/PENN | Mississippian/Pennsylvanian |
| LPERM/PERM/UPERM | Lower/Middle/Upper Permian |

### 동의어 유형

- `j.s.s.` - junior subjective synonym (주관적 후행 이명)
- `j.o.s.` - junior objective synonym (객관적 후행 이명)
- `preocc.` - preoccupied (선취명)

## 라이선스

이 프로젝트는 학술 연구 목적으로 제작되었습니다. 원본 데이터의 저작권은 해당 저자에게 있습니다.

## 참고

- [Treatise on Invertebrate Paleontology](https://www.biodiversitylibrary.org/)
- [Paleobiology Database](https://paleobiodb.org/)
