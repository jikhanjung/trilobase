# 데이터 품질 수정: 콜론 4건 + BRAÑA 13건 + Paraacidaspis 1건 + 하이픈 줄바꿈 165건

**날짜:** 2026-02-19
**유형:** 데이터 수정 (bugfix)

## 1. Colon-Family parent_id 연결 — 4건

원본에서 family 이름 뒤에 세미콜론(`;`) 대신 콜론(`:`)을 사용하여 파싱되지 않은 케이스.
family는 모두 DB에 존재하며 확정적(? 없음).

| id | Genus | raw_entry 패턴 | → Family (id) |
|----|-------|----------------|---------------|
| 1769 | Esseigania | `TSINANIIDAE: UCAM` | → Tsinaniidae (62) |
| 2291 | Illaenoides | `STYGINIDAE: LSIL` | → Styginidae (61) |
| 3081 | Mindycrusta | `ASAPHISCIDAE: MUCAM` | → Asaphiscidae (132) |
| 4436 | Saimixiella | `DOLICHOMETOPIDAE: LCAM` | → Dolichometopidae (52) |

```sql
UPDATE taxonomic_ranks SET parent_id = 62,  family = 'Tsinaniidae'      WHERE id = 1769;
UPDATE taxonomic_ranks SET parent_id = 61,  family = 'Styginidae'       WHERE id = 2291;
UPDATE taxonomic_ranks SET parent_id = 132, family = 'Asaphiscidae'     WHERE id = 3081;
UPDATE taxonomic_ranks SET parent_id = 52,  family = 'Dolichometopidae' WHERE id = 4436;
```

## 2. BRANI°A → BRAÑA 인코딩 수정 — 13건

원본 PDF에서 `ñ`(n-tilde)가 `°`(degree sign)로 OCR/인코딩 오류.
스페인어 성 **BRAÑA**의 올바른 표기로 교정.

추가로 `BRANI°A&`에서 `&` 앞 공백 누락도 함께 수정 (`BRAÑA & VANĚK`).

**수정 대상:**

| author 변경 | 건수 | 대상 genera |
|-------------|------|-------------|
| `ELDREDGE & BRANI°A` → `ELDREDGE & BRAÑA` | 6 | Andinacaste, Belenops, Curuyella, Deltacephalaspis, Prestalia, Romanops |
| `BRANI°A& VANĚK` → `BRAÑA & VANĚK` | 7 | Bolivianaspis, Chacomurus, Chiarumanipyge, Fenestraspis, Francovichia, Gamonedaspis, Kozlowskiaspis |

```sql
UPDATE taxonomic_ranks SET author = 'ELDREDGE & BRAÑA' WHERE author = 'ELDREDGE & BRANI°A';
UPDATE taxonomic_ranks SET author = 'BRAÑA & VANĚK'    WHERE author = 'BRANI°A& VANĚK';
UPDATE taxonomic_ranks SET raw_entry = REPLACE(raw_entry, 'BRANI°A', 'BRAÑA') WHERE raw_entry LIKE '%BRANI°A%';
```

수정 후 `°` 문자가 포함된 레코드: **0건** (완전 제거)

## 3. Paraacidaspis 중복 해소 — 1963 → is_valid=0

원본 NOTE 8에 의하면:
- Paraacidaspis는 Poletaeva (1960)에서 sibirica를 type species by monotypy로 유효하게 됨
- Poletaeva in Egorova et al. (1963)의 hunanica는 후대 사용

따라서 1963 entry(id=3484)를 `is_valid=0`으로 변경.

| id | author | year | is_valid 변경 |
|----|--------|------|---------------|
| 3483 | POLETAEVA | 1960 | 1 (유지) |
| 3484 | POLETAEVA in EGOROVA et al. | 1963 | 1 → **0** |

```sql
UPDATE taxonomic_ranks SET is_valid = 0 WHERE id = 3484;
```

## 결과

| 항목 | 변경 전 | 변경 후 |
|------|---------|---------|
| parent_id NULL (total) | 329 | **325** |
| parent_id NULL (valid) | 72 | **68** |
| 유효 Genus | 4,260 | **4,259** |
| 무효 Genus | 855 | **856** |
| `°` 문자 포함 레코드 | 13 | **0** |
| valid genus 이름 중복 | 1 (Paraacidaspis) | **0** |

## 4. trilobite_genus_list.txt + DB 소스 데이터 동기 수정

DB(author, raw_entry)와 원본 텍스트 파일 양쪽 모두에 동일한 교정 반영.

### 4a. 이전 수정분 (DB 수정과 동시) — 22건

| 수정 유형 | 건수 | 내용 |
|-----------|------|------|
| `BRANI°A` → `BRAÑA` | 14 | tilde 오인식 (OCR/인코딩), `&` 앞 공백 복원 포함 |
| `IDAE:` → `IDAE;` | 4 | 콜론→세미콜론 (Esseigania, Illaenoides, Mindycrusta, Saimixiella) |
| `Grinellaspis` → `Grinnellaspis` | 1 | `n` 1자 누락 (Actinopeltis entry) |
| `Bailliella` → `Bailiella` | 1 | `l` 1자 초과 (Liocephalus entry) |
| `Parakoldinoidia` → `Parakoldinioidia` | 1 | `i` 1자 누락 (Macroculites entry) |
| `Tschernyschewella` → `Tschernyschewiella` | 1 | `i` 1자 누락 (Schmidtella entry) |

### 4b. 공백 누락 수정 — 44건 (txt + DB author + raw_entry)

대문자 사이 `in`, `et`, `&` 앞뒤 공백 누락을 일괄 교정.

| 패턴 | 건수 | 대표 예시 |
|------|------|-----------|
| `VANĚKinPŘIBYL` → `VANĚK in PŘIBYL` | 18 | Alreboaspis, Ancyginaspis 등 |
| `Xin Y` (in 앞 공백 누락) | 8 | POLETAEVAin, CHERNYSHEVAin, REPINAin, EGOROVAin, SIVOVin, ROZOVAin, CHU-GAEVAin |
| `Xet al.` (et 앞 공백 누락) | 12 | CHERNYSHEVAet, EGOROVAet, REPINAet, HORNYet, PŘIBYLet |
| `X& Y` (& 앞 공백 누락) | 5 | PRANTL&(×2), FORTEY&, KACHA&, ENGEL& |
| `PIBL` → `PŘIBYL` (제어문자 오류) | 1 | Parvixochus: `P\x02IBL` → `PŘIBYL` |

### 4c. 제어문자 제거 — 2건

| 줄 | Genus | 제어문자 | 처리 |
|----|-------|---------|------|
| 3037 | Nitidocare | `\x08` (BS) 줄 끝 | 삭제 |
| 3797 | Proliobole | `\x01` (SOH) `cuII\x01)` 내 | 삭제 |

### 4d. CHU-GAEVA → CHUGAEVA — 1건

Harpidoides (id=2086) entry에서 저자명 `CHU-GAEVA`를 `CHUGAEVA`로 수정.
같은 entry 내의 `APOLLONOV & CHUGAEVA`와 표기 통일.

```sql
UPDATE taxonomic_ranks SET author = REPLACE(author, 'CHU-GAEVA', 'CHUGAEVA'),
  raw_entry = REPLACE(raw_entry, 'CHU-GAEVA', 'CHUGAEVA') WHERE id = 2086;
```

### 4e. PDF 줄바꿈 하이픈 제거 — 165건 (149개 고유 패턴)

원본 PDF에서 줄바꿈 시 삽입된 하이픈(`-`)을 제거하여 단어를 복원.
txt + DB raw_entry 양쪽 동시 수정.

| 범주 | 고유 패턴 | 수정 건수 | 대표 예시 |
|------|-----------|-----------|-----------|
| 분류군 이름 | 38 | 47 | `Odonto-pleura`→`Odontopleura`, `Chas-mops`→`Chasmops`, `Para-doxides`→`Paradoxides` |
| 종소명/형용사 | 52 | 55 | `macro-cephalus`→`macrocephalus`, `sub-coronatus`→`subcoronatus`, `semi-circularis`→`semicircularis` |
| 지명 | 56 | 60 | `Coal-brookedale`→`Coalbrookedale`, `Rock-ledge`→`Rockledge`, `Fran-conia`→`Franconia` |
| 복합 하이픈 (부분 복원) | 3 | 3 | `Bosh-che-Kulya`→`Boshche-Kulya`, `Bad-enas-Schichten`→`Badenas-Schichten`, `Hebe-discus-Judomia`→`Hebediscus-Judomia` |

**수정하지 않은 하이픈 (정상):**

| 범주 | 건수 | 예시 |
|------|------|------|
| 하이픈 성씨 | ~21 | MUNIER-CHALMAS, PANTOJA-ALOR, WUNN-PETRY, BOWDLER-HICKS |
| 독일어 합성어 (-Stufe/-Schichten/-Kalk) | ~30 | Wocklumeria-Stufe, Stadtfeld-Schichten, Tentaculiten-Kalk |
| Biozone 범위 | ~15 | Sdzuyella-Aegunaspis, Kielanella-Tretaspis |
| 정상 지명 | ~50 | Dvorce-Prokop, Loire-Atlantique, Saint-Chinian |
| 중국어 로마자 (보류) | ~30 | Chang-shan, Gui-zhou, Shan-dong, Mao-tian |

### 4f. txt↔DB raw_entry 동기화 검증 및 수정 — 23건

전수 비교(5,115줄)로 txt와 DB raw_entry 사이 불일치를 검출하여 수정.

**DB raw_entry 미반영 — 17건:**

| 수정 유형 | 건수 | 원인 |
|-----------|------|------|
| `BRAÑA&` → `BRAÑA &` (공백 추가) | 7 | 인코딩 수정 시 raw_entry에 `&` 공백 미반영 |
| `IDAE:` → `IDAE;` | 4 | 콜론 수정 시 raw_entry 미반영 |
| `Grinellaspis` → `Grinnellaspis` | 1 | 철자 교정 raw_entry 미반영 |
| `Bailliella` → `Bailiella` | 1 | 철자 교정 raw_entry 미반영 |
| `Parakoldinoidia` → `Parakoldinioidia` | 1 | 철자 교정 raw_entry 미반영 |
| `Tschernyschewella` → `Tschernyschewiella` | 1 | 철자 교정 raw_entry 미반영 |
| Actinopeltis(294) Grinnellaspis | 1 | 위와 동일 |
| Liocephalus(2732) Bailiella | 1 | 위와 동일 |

**TXT 미반영 — 6건:**

| 패턴 | 건수 | 대상 genera |
|------|------|-------------|
| `inKRYSKOV` → `in KRYSKOV` | 1 | Kuraspis |
| `inROZOVA` → `in ROZOVA` | 1 | Paivinia |
| `inCHERNYSHEVA` → `in CHERNYSHEVA` | 1 | Paraorlovia |
| `inREPINA` → `in REPINA` | 1 | Parapagetia |
| `inEGOROVA` → `in EGOROVA` | 2 | Pseudonericella, Schoriella |

### 4g. 결합 엔트리 raw_entry 분리 — 2건

devlog 029에서 genus 분리 시 raw_entry는 원본 결합 텍스트를 유지했으나,
각 genus가 자기 raw_entry만 갖도록 분리.

| id | Genus | 변경 | 분리된 genus |
|----|-------|------|-------------|
| 2441 | Kaniniella | Kanlingia 부분 제거 | Kanlingia (id=5339, 이미 분리됨) |
| 2965 | Melopetasus | Memmatella 부분 제거 | Memmatella (id=5340, 이미 분리됨) |

### 최종 동기화 현황

**txt ↔ DB raw_entry: 5,115/5,115 (100%) 완전 일치**

## 남은 이슈 (미수정)

- **?FAMILY genera** 29건: `?CERATOPYGIDAE` 등 불확실 family 배정. 원저자 의도 존중하여 보류 중
- **valid genus without temporal_code** 85건: 확인 필요
- **중국어 로마자 하이픈** ~30건: 구 로마자 표기(Wade-Giles 등) 가능성 있어 보류
