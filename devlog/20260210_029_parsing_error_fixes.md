# 029: DB 파싱 오류 수정 및 누락 genus 추가

**날짜:** 2026-02-10

## 작업 개요

Canonical DB의 파싱 오류 레코드를 `raw_entry` 기반으로 수동 수정하고, 원본 텍스트에서 누락된 genus 2건을 추가.

**원칙:** 파싱 로직 수정 없이 오류 레코드만 직접 수정. `?` 불확실성 기호는 현행 유지.

---

## 수정 내용

### 1. taxonomic_ranks 파싱 오류 16건

| ID | Name | 문제 | 수정 내용 |
|----|------|------|-----------|
| 799 | Blountiana | 미스스펠링 엔트리인데 author/year/type_species에 잘못된 값 | 모두 NULL |
| 815 | Bohemopyge | 익명 저자, type species year(1872)가 genus year로 | author=NULL, year=1950 |
| 1144 | Clarella | `[sic]` 중첩으로 type_species truncate, location에 연도 유입 | type_species/author/formation/location 복원 |
| 1615 | Ellipsocephalus | `[sic]` 중첩으로 type_species truncate, formation에 쓰레기 유입 | type_species/formation 복원 |
| 1672 | Eoasaphiscellus | JELL nov. 파싱 실패, Guizhou가 formation으로 오인 | author=JELL, year=2002, formation=NULL, location=Guizhou China |
| 2245 | Huntoniatonia | CAMPBELL nov. 파싱 실패, replacement target year 유입 | author=CAMPBELL, year=2002 |
| 2441 | Kaniniella | 다음 줄 Kanlingia 데이터가 formation/location으로 유입 | formation/location NULL |
| 2679 | Leptoplastoides | 미스스펠링 엔트리 파싱 실패 | author/year/type_species NULL |
| 2965 | Melopetasus | 다음 줄 Memmatella 데이터가 formation/location으로 유입 | formation/location NULL |
| 3510 | Paracalymenemene | JELL nov. 파싱 실패 | author=JELL, year=2002 |
| 3655 | Parasolopleurena | JELL nov. 파싱 실패 | author=JELL, year=2002 |
| 3762 | Petrbokia | `[Ni-leus]` 하이픈 중첩 괄호 파싱 실패 | type_species/author/formation/location 복원 |
| 4398 | Rokycania | 인코딩 오류(VANĚK→VAN˛#) + `[sic]` 파싱 실패 | 전체 수정 |
| 4919 | Toernquistia | `(Toernquistia [sic])` 중첩 괄호 파싱 실패 | type_species/formation 복원 |
| 4980 | Trigonyangaspis | JELL nov. 파싱 실패 | author=JELL, year=2002 |
| 5325 | Zhifangiafangia | JELL nov. 파싱 실패 | author=JELL, year=2002 |

**`nov.` year 처리 원칙:** JELL nov./CAMPBELL nov. 모두 year=2002 (Jell & Adrain 2002 기준)

### 2. formations 테이블 수정 (5건)

| ID | 기존 이름 | 수정 |
|----|-----------|------|
| 564 | `venustus BILLINGS` | → `Manuels River Fm` (이름 수정) |
| 1876 | `) nicholsoni] Keisley Lst` | → `Keisley Lst` (이름 수정) |
| 796 | `ambiguus] Jince Fm` | 삭제 (Jince Fm id=12로 대체) |
| 1556 | `longicauda KLOUČEK` | 삭제 (Dobrotiva Fm id=383으로 대체) |
| 1729 | `primula HOLUB` | 삭제 (Klabava Fm id=265로 대체) |

### 3. genus_formations/genus_locations 연결 수정

- Ellipsocephalus: formation_id 796→12 (Jince Fm)
- Petrbokia: formation_id 1556→383 (Dobrotiva Fm)
- Rokycania: formation_id 1729→265 (Klabava Fm)
- Eoasaphiscellus: genus_formations 항목 삭제 (Guizhou는 formation 아님)
- Kaniniella: genus_formations/locations 항목 삭제 (Kanlingia 데이터 제거)
- Melopetasus: genus_formations/locations 항목 삭제 (Memmatella 데이터 제거)
- Clarella: genus_locations region 수정 (`1874] Manuels River Fm` → `Newfoundland`)
- Petrbokia: genus_locations region 수정 (`1916] Dobrotiva Fm` → NULL)
- Rokycania: genus_locations region 수정 (`1912] Klabava Fm` → NULL)
- Eoasaphiscellus: genus_locations region 추가 (`Guizhou`)

### 4. 원본 텍스트파일 수정

`trilobite_genus_list.txt`에서 두 줄을 각각 분리:
- 2216번: `Kaniniella SIVOV...` + `Kanlingia T. ZHANG...` → 두 줄로 분리
- 2740번: `Melopetasus SCHALLREUTER...` + `Memmatella W. ZHANG...` → 두 줄로 분리

### 5. 신규 genus 2건 추가

| ID | Name | Author | Year | Family | Temporal | Formation | Location |
|----|------|--------|------|--------|----------|-----------|----------|
| 5339 | Kanlingia | T. ZHANG | 1981 | Raphiophoridae | MORD | Saergan Fm | Xinjiang, China |
| 5340 | Memmatella | W. ZHANG in W. ZHANG et al. | 1995 | Proasaphiscidae | MCAM | Changhia Fm | Henan, China |

---

## 결과

- 전체 Genus 수: 5,113 → **5,115**
- Raphiophoridae genera_count: 41 → 42
- Proasaphiscidae genera_count: 80 → 81
- formations 테이블: 2,009 → **2,006** (5개 삭제, 2개 이름 수정)

## 잔여 비파싱-오류 항목 (현행 유지)

- type_species 내 `?` 불확실성 기호 124건: 분류학적 불확실성 표기, 현행 유지
- type_species 내 `(Subgenus) species` 형태 337건: 분류학적 정상 표기, 현행 유지
- Metagnostus(3012): location에 `(originates from Asaphus Lst..., fide FORTEY, 1980)` — 원본 데이터의 특이한 서술 형태, 현행 유지
