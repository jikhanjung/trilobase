# Trilobase

**Trilobase**는 삼엽충(Trilobita) 속(genus) 수준의 분류학 정보를
문헌 기반으로 정제·정규화하여 구축한 **연구용 관계형 데이터베이스**입니다.

본 프로젝트는 기존 분류학 문헌에 흩어져 있는 속명, 동의어, 상위 분류군,
산지 및 지층 정보를 **기계가 질의 가능한 형태(SQLite)**로 구조화하는 것을
목표로 합니다.

---

## Overview

Trilobase는 다음 두 핵심 문헌을 기반으로 구축되었습니다.

- **Jell, P.A. & Adrain, J.M. (2002)**
  *Available Generic Names for Trilobites*
  Memoirs of the Queensland Museum 48(2): 331–553.

- **Adrain, J.M. (2011)**
  *Class Trilobita Walch, 1771*
  In: Zhang, Z.-Q. (Ed.), *Animal biodiversity* (Zootaxa 3148): 104–109.

원본 PDF에서 추출한 데이터를 수작업 검토 및 정규화 과정을 거쳐
SQLite 데이터베이스로 구축하였으며,
Flask 기반 웹 인터페이스를 통해 탐색할 수 있습니다.

---

## Database Statistics

| Taxonomic Rank | Count |
|---------------|-------|
| Class         | 1     |
| Order         | 12    |
| Suborder      | 8     |
| Superfamily   | 13    |
| Family        | 191   |
| Genus         | 5,113 |
| **Total**     | **5,338** |

### Genus Details

- **Valid genera**: 4,258 (83.3%)
- **Invalid genera**: 855 (16.7%)
- **Synonym relationships**: 1,055
- **Bibliographic references**: 2,130

---

## Installation & Usage

### Option 1: Standalone Executable (Recommended for End Users)

**Windows / Linux 사용자를 위한 간편한 실행 방법:**

1. 릴리스 페이지에서 `trilobase.exe` (Windows) 또는 `trilobase` (Linux) 다운로드
2. 실행 파일을 더블클릭 또는 터미널에서 실행
3. GUI 컨트롤 패널에서 "▶ Start Server" 클릭
4. 웹 브라우저가 자동으로 열리며 http://localhost:8080 표시

**특징:**
- Python 설치 불필요
- 모든 데이터와 웹 서버가 단일 실행 파일에 포함
- 사용자 주석은 별도 파일(`trilobase_overlay.db`)에 저장되어 영구 보존

### Option 2: Python Development Mode

**개발자 또는 소스 코드 수정이 필요한 사용자:**

#### Requirements

- Python 3.8+
- Flask

#### Installation

```bash
git clone https://github.com/yourusername/trilobase.git
cd trilobase
pip install flask
```

#### Run Web Server

```bash
python app.py
```

Open your browser and navigate to:
http://localhost:8080

---

## Web Interface Features

- **Tree View**
  Class → Order → Suborder → Superfamily → Family hierarchy

- **Genus List**
  Display genera within a selected family

- **Genus Detail View**
  Author, year, type species, formation, locality, synonymy

- **Filtering**
  Option to display only valid taxa

- **Expand / Collapse**
  Global tree control

---

## Database Schema

### Core Tables

**taxonomic_ranks**
Unified taxonomic hierarchy (Class–Genus, 5,338 records)

- id, name, rank, parent_id
- author, year, year_suffix
- genera_count, notes
- (Genus only) type_species, formation, location, is_valid, …

**synonyms**
Synonym relationships (1,055 records)

- junior_taxon_id
- senior_taxon_id
- synonym_type
- fide_author, fide_year

**Other tables**

- genus_formations (4,854)
- genus_locations (4,841)
- formations (2,009)
- countries (151)
- temporal_ranges (28)
- bibliography (2,130)

---

## Example Queries

```sql
-- Valid genera
SELECT name, author, year
FROM taxonomic_ranks
WHERE rank='Genus' AND is_valid=1
LIMIT 10;
```

```sql
-- Full taxonomic hierarchy of a genus
SELECT g.name AS genus, f.name AS family, o.name AS "order"
FROM taxonomic_ranks g
LEFT JOIN taxonomic_ranks f ON g.parent_id = f.id
LEFT JOIN taxonomic_ranks sf ON f.parent_id = sf.id
LEFT JOIN taxonomic_ranks o ON sf.parent_id = o.id
WHERE g.name = 'Paradoxides';
```

```sql
-- Genera reported from a specific country
SELECT g.name, gl.region
FROM taxonomic_ranks g
JOIN genus_locations gl ON g.id = gl.genus_id
JOIN countries c ON gl.country_id = c.id
WHERE c.name = 'China'
LIMIT 10;
```

---

## Temporal Range Codes

| Code | Meaning |
|-----|--------|
| LCAM / MCAM / UCAM | Lower / Middle / Upper Cambrian |
| LORD / MORD / UORD | Lower / Middle / Upper Ordovician |
| LSIL / USIL | Lower / Upper Silurian |
| LDEV / MDEV / UDEV | Lower / Middle / Upper Devonian |
| MISS / PENN | Mississippian / Pennsylvanian |
| LPERM / PERM / UPERM | Lower / Middle / Upper Permian |

---

## Synonym Types

- **j.s.s.** – junior subjective synonym
- **j.o.s.** – junior objective synonym
- **preocc.** – preoccupied name

---

## SCODA (Self-Contained Data Artifact)

Trilobase는 **SCODA** 프레임워크의 참조 구현입니다.

SCODA는 데이터를 서비스가 아닌 **자기완결적 지식 객체**로 다루는 접근법입니다.
`trilobase.db` 파일 하나가 데이터뿐 아니라 자신의 신원(identity), 출처(provenance),
스키마 설명(semantics)을 내장하고 있어, 외부 문서 없이도 스스로를 설명합니다.

```sql
-- 아티팩트 정보 확인
SELECT * FROM artifact_metadata;

-- 데이터 출처 확인
SELECT source_type, citation, year FROM provenance;

-- 테이블/컬럼 설명 조회
SELECT * FROM schema_descriptions WHERE table_name = 'taxonomic_ranks';
```

자세한 내용은 `Trilobase_as_SCODA.md`와 `devlog/20260207_P07_scoda_implementation.md`를 참조하세요.

---

## Intended Use & Scope

- Research, data exploration, and methodological development
- Not intended for nomenclatural acts
- Does not replace expert taxonomic judgment or official registries

---

## License

This project is provided for academic research purposes.
Copyright of the original taxonomic data remains with the respective authors.

---

## References

- [Treatise on Invertebrate Paleontology](https://www.biodiversitylibrary.org/)
- [Paleobiology Database](https://paleobiodb.org/)
