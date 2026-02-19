# 미연결 Synonym 24건 정리

**날짜:** 2026-02-19
**유형:** 데이터 수정 (bugfix)

## 배경

`synonyms` 테이블에서 `senior_taxon_id IS NULL`인 레코드가 24건 존재했다.
원본(Jell & Adrain 2002)의 `raw_entry`를 분석하여 DB 내 senior taxon을 찾아 연결하고,
`junior_taxon_id` 오류도 함께 수정했다.

## 수정 결과 요약

| 구분 | 건수 |
|------|------|
| senior_taxon_id 연결 (exact match) | 18 |
| senior_taxon_id 연결 + 철자 교정 | 4 |
| senior_taxon_id 연결 + ICZN 조사 | 1 |
| junior_taxon_id 오류 수정 | 2 |
| 미연결 (정상 — 대체명 없음) | 1 |
| **합계** | **24** (중복 포함) |

최종 미연결: 24건 → **1건** (Szechuanella — 대체명 없는 것이 정상)

## A. senior_taxon_id 연결 — 23건

### A-1. Exact Match — 18건

| Syn ID | Junior (id) | → Senior (id) | Type |
|--------|-------------|---------------|------|
| 14 | Actinolobus (292) | → Illaenus (2296) | preocc. |
| 147 | Branisella (877) | → Maurotarion (2933) | preocc. |
| 182 | Cephalacanthus (1026) | → Callavia (950) | preocc. |
| 210 | Conocephalus (1193) | → Conocoryphe (1195) | preocc. |
| 237 | Cylindraspis (1304) | → Archegonus (537) | preocc. |
| 285 | Domina (1516) | → Licnocephala (2709) | preocc. |
| 404 | Hausmannia (2098) | → Odontochile (3303) | preocc. |
| 419 | Herse (2136) | → Solenopleurina (4639) | preocc. |
| 485 | Kirkella (2505) | → Ptyocephalus (4237) | preocc. |
| 866 | Rhinaspis (4371) | → Megistaspis (2957) | preocc. |
| 5 | Acanthaloma (239) | → Leonaspis (2671) | suppressed |
| 170 | Calymena (962) | → Calymene (963) | suppressed |
| 224 | Cryptonymus (1273) | → Illaenus (2296) | suppressed |
| 314 | Entomolithus (1663) | → Paradoxides (3537) | suppressed |
| 315 | Entomostracites (1664) | → Paradoxides (3537) | suppressed |
| 748 | Phillipsella (3786) | → Phillipsinella (3788) | suppressed |
| 782 | Polytomurus (3927) | → Dionide (1477) | suppressed |
| 836 | Pterygometopidella (4222) | → Eophacops (1716) | suppressed |

### A-2. 철자 교정 포함 — 4건

원본 raw_entry의 이름과 DB 내 genus 이름 사이에 철자 차이가 있었다.

| Syn ID | Junior (id) | raw_entry 상 이름 | → DB 이름 (id) | 차이 |
|--------|-------------|-------------------|----------------|------|
| 510 | Liocephalus (2732) | Bailliella | → Bailiella (662) | `l` 1자 초과 |
| 529 | Macroculites (2861) | Parakoldinoidia | → Parakoldinioidia (3570) | `i` 1자 누락 |
| 895 | Schmidtella (4493) | Tschernyschewella | → Tschernyschewiella (5009) | `i` 1자 누락 |
| 16 | Actinopeltis (294) | Grinellaspis | → Grinnellaspis (2009) | `n` 1자 누락 |

### A-3. ICZN 조사로 연결 — 1건

| Syn ID | Junior (id) | → Senior (id) | 근거 |
|--------|-------------|---------------|------|
| 634 | Ogygia (3314) | → Ogygiocaris (3317) | ICZN Opinion 1259: Ogygia 억제, Ogygiocaris/Ogygites 보존 |

raw_entry에 "in favour of X" 구문이 없어 초기 조사에서 연결 불가로 분류했으나,
ICZN Opinion 1259를 확인한 결과 Ogygia(1817)를 억제하고 Ogygiocaris Angelin, 1854와
Ogygites Tromelin & Lebesconte, 1876을 보존하는 결정이었음.
주 보존 대상인 Ogygiocaris(3317)로 연결.

## B. junior_taxon_id 오류 수정 — 2건

동명이속(homonym)에서 synonym 레코드가 valid 쪽에 잘못 연결되어 있었다.

| Syn ID | 수정 전 (잘못된 대상) | 수정 후 (올바른 대상) | 근거 |
|--------|----------------------|----------------------|------|
| 16 | Actinopeltis (293) HAWLE & CORDA, 1847 — valid | → Actinopeltis (294) POULSEN, 1946 — preocc. | raw_entry "preocc., replaced by Grinellaspis"는 1946 쪽 |
| 960 | Szechuanella (4774) W. ZHANG & FAN, 1960 — valid | → Szechuanella (4775) LU, 1962 — preocc. | raw_entry "preocc., not replaced"는 1962 쪽 |
| 961 | Szechuanella (4774) W. ZHANG & FAN, 1960 — valid | → Szechuanella (4775) LU, 1962 — preocc. | "j.s.s. of Paraszechuanella"도 1962 쪽 |

## C. 미연결 — 1건 (정상)

### Szechuanella (syn 960) — 대체명 없음이 정상

- Junior: Szechuanella LU, 1962 (id=4775)
- synonym_type: preocc., not replaced
- 사유: 원본 NOTE 8에 의하면, Szechuanella는 Zhang & Fan (1960)에 의해 rectangula를
  type species by monotypy로 유효하게 됨. Lu (1962)의 szechuanensis는 이후
  Paraszechuanella로 이동됨 (syn 961에서 이미 연결). 따라서 대체명이 필요 없음.
- notes에 NOTE 8 요약 기록 완료

## 실행 SQL

```sql
-- A-1. Exact match 18건
UPDATE synonyms SET senior_taxon_name = 'Illaenus',        senior_taxon_id = 2296 WHERE id = 14;
UPDATE synonyms SET senior_taxon_name = 'Maurotarion',     senior_taxon_id = 2933 WHERE id = 147;
UPDATE synonyms SET senior_taxon_name = 'Callavia',        senior_taxon_id = 950  WHERE id = 182;
UPDATE synonyms SET senior_taxon_name = 'Conocoryphe',     senior_taxon_id = 1195 WHERE id = 210;
UPDATE synonyms SET senior_taxon_name = 'Archegonus',      senior_taxon_id = 537  WHERE id = 237;
UPDATE synonyms SET senior_taxon_name = 'Licnocephala',    senior_taxon_id = 2709 WHERE id = 285;
UPDATE synonyms SET senior_taxon_name = 'Odontochile',     senior_taxon_id = 3303 WHERE id = 404;
UPDATE synonyms SET senior_taxon_name = 'Solenopleurina',  senior_taxon_id = 4639 WHERE id = 419;
UPDATE synonyms SET senior_taxon_name = 'Ptyocephalus',    senior_taxon_id = 4237 WHERE id = 485;
UPDATE synonyms SET senior_taxon_name = 'Megistaspis',     senior_taxon_id = 2957 WHERE id = 866;
UPDATE synonyms SET senior_taxon_name = 'Leonaspis',       senior_taxon_id = 2671 WHERE id = 5;
UPDATE synonyms SET senior_taxon_name = 'Calymene',        senior_taxon_id = 963  WHERE id = 170;
UPDATE synonyms SET senior_taxon_name = 'Illaenus',        senior_taxon_id = 2296 WHERE id = 224;
UPDATE synonyms SET senior_taxon_name = 'Paradoxides',     senior_taxon_id = 3537 WHERE id = 314;
UPDATE synonyms SET senior_taxon_name = 'Paradoxides',     senior_taxon_id = 3537 WHERE id = 315;
UPDATE synonyms SET senior_taxon_name = 'Phillipsinella',  senior_taxon_id = 3788 WHERE id = 748;
UPDATE synonyms SET senior_taxon_name = 'Dionide',         senior_taxon_id = 1477 WHERE id = 782;
UPDATE synonyms SET senior_taxon_name = 'Eophacops',       senior_taxon_id = 1716 WHERE id = 836;

-- A-2. 철자 교정 4건
UPDATE synonyms SET senior_taxon_name = 'Bailiella',           senior_taxon_id = 662  WHERE id = 510;  -- Bailliella→Bailiella
UPDATE synonyms SET senior_taxon_name = 'Parakoldinioidia',    senior_taxon_id = 3570 WHERE id = 529;  -- Parakoldinoidia→Parakoldinioidia
UPDATE synonyms SET senior_taxon_name = 'Tschernyschewiella',  senior_taxon_id = 5009 WHERE id = 895;  -- Tschernyschewella→Tschernyschewiella
UPDATE synonyms SET senior_taxon_name = 'Grinnellaspis',       senior_taxon_id = 2009 WHERE id = 16;   -- Grinellaspis→Grinnellaspis

-- A-3. ICZN 조사 1건
UPDATE synonyms SET senior_taxon_name = 'Ogygiocaris', senior_taxon_id = 3317,
  notes = 'ICZN Opinion 1259: Ogygia suppressed to conserve Ogygiocaris Angelin 1854 and Ogygites Tromelin & Lebesconte 1876'
  WHERE id = 634;

-- B. junior_taxon_id 오류 수정
UPDATE synonyms SET junior_taxon_id = 294  WHERE id = 16;   -- Actinopeltis: 293→294
UPDATE synonyms SET junior_taxon_id = 4775 WHERE id = 960;  -- Szechuanella: 4774→4775
UPDATE synonyms SET junior_taxon_id = 4775 WHERE id = 961;  -- Szechuanella: 4774→4775

-- C. Szechuanella notes 추가
UPDATE synonyms SET notes = 'NOTE 8: Zhang & Fan (1960) made genus available with rectangula as type by monotypy; Lu 1962 szechuanensis transferred to Paraszechuanella (see syn 961). No replacement needed.'
  WHERE id = 960;
```

## 최종 현황

- Synonym 연결률: 1,031/1,055 (97.6%) → **1,054/1,055 (99.9%)**
- 미연결 1건(Szechuanella syn 960)은 대체명이 없는 것이 학술적으로 정상
