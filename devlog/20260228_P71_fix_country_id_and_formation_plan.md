# T-5: genus_locations country_id 수정 + Formation 오정렬 해결 계획

**Date:** 2026-02-28
**Status:** ✅ 완료 (devlog 098 참조)

## Context

`genus_locations` 테이블 조사 결과 두 가지 대규모 데이터 품질 문제를 발견:

1. **country_id 매핑 오류**: 4,841건 중 3,752건 (77.5%) 잘못 배정
2. **Formation 필드 오정렬**: ~389건에서 지역명/국가명이 Formation으로 저장됨

### 근본 원인

**country_id 오류**: `normalize_database.py`의 `LIKE '%country_name'` 반복 UPDATE에서 후속 매칭이 이전 결과를 덮어씀.

**Formation 오정렬**: `create_database.py`가 `]` ~ `; FAMILY;` 사이 텍스트를 첫 `,` 기준으로만 분할.

| 원문 패턴 | 파싱 결과 | 문제 |
|-----------|----------|------|
| `Fm, Region, Country` | formation=Fm, location="Region, Country" | 정상 |
| `Region, Country` | formation=Region, location="Country" | Formation에 지역명 |
| `Country` | formation=Country, location=NULL | Formation에 국가명 |

### 주요 country_id 오류 패턴 (상위 10)

| 원문 국가 | 잘못된 배정 | 건수 |
|-----------|-----------|------|
| China | England | 1,023 |
| USA | Mexico | 666 |
| Russia | Spitsbergen | 558 |
| Canada | USA | 306 |
| Australia | Russia | 210 |
| Germany | Australia | 150 |
| England | Luxemburg | 121 |
| Argentina | China | 67 |
| Sweden | S France | 65 |
| Scotland | Luxemburg | 58 |

---

## 수정 계획

### Phase A: country_id 일괄 수정 (자동화 가능)

**스크립트**: `scripts/fix_country_id.py`

**로직**:

```
1. genus_locations JOIN taxonomic_ranks → location 텍스트 추출
2. location의 마지막 ','  뒤 부분 = true_country
3. 국가명 정규화 (COUNTRY_NORMALIZE 맵):
   - "Czech Repubic" → "Czech Republic"
   - "N. Ireland" → "N Ireland"
   - "NWGreenland" → "NW Greenland"
   - "arctic Russia" → "Arctic Russia"
   - "eastern Iran" → "Eastern Iran"
   - "central Kazakhstan" → "Central Kazakhstan"
   - "central Morocco" → "Central Morocco"
   - "central Afghanistan" → "Central Afghanistan"
   - '" SE Morocco' → "SE Morocco"
   - '" Spain' → "Spain"
   - "southern Kazakhstan" → "S Kazakhstan"
4. pc.countries에서 name 매칭 → correct_country_id
5. UPDATE genus_locations SET country_id = correct_country_id
```

**에지 케이스 처리**:
- 파싱 오류 (예: `"China: REDLICHIIDAE"`, `"TROPIDOCORYPHIDAE"`) → 리포트 출력, 수동 수정
- location이 NULL인 genus (formation=country인 경우) → Phase B에서 처리
- 매칭 불가 국가명 → 리포트 출력

**옵션**: `--dry-run` (리포트만), `--report` (현황 통계만)

### Phase B: Formation 오정렬 수정 (반자동)

**스크립트**: `scripts/fix_formation_misalignment.py`

세 가지 유형을 분류하여 처리:

**Type 1: formation = country (8건)**
- 조건: `location IS NULL AND formation IN (알려진 국가명)`
- 예: `Sweden; CHEIRURIDAE; LORD.` → formation="Sweden"
- 수정:
  - `taxonomic_ranks.formation` → NULL
  - `genus_formations` 해당 레코드 삭제 (잘못된 formation 참조)
  - `genus_locations`에 country_id 매핑 추가
  - 특수 케이스: Tetralichas (Baltic Russia → country=Russia, region="Baltic Russia")

**Type 2: formation = location (36건)**
- 조건: formation과 location이 동일한 값 (둘 다 국가명)
- 예: `Acerocarina` — formation="Sweden", location="Sweden"
- 수정:
  - `taxonomic_ranks.formation` → NULL
  - `genus_formations` 해당 레코드 삭제

**Type 3: formation = region, location = country (~306건)**
- 조건: formation에 Formation 접미사(Fm/Lst/Sh/Gp 등) 없음 AND location이 comma 없는 국가명
- 예: `Mendoza, Argentina` → formation="Mendoza", location="Argentina"
- 수정:
  - `genus_locations.region` = 현재 formation 값
  - `taxonomic_ranks.formation` → NULL
  - `genus_formations` 해당 레코드 삭제

**화이트리스트 (수정 제외, 56개)**: 원문에서 formation으로 확인 가능한 항목
- 표준 접미사 없는 유효 지층명: `Andrarum`, `Surkh Bum`, `Krekling` 등
- 독일어 지층명: `Leimitz Schiefer`, `Wiltz Schicten` 등
- 프랑스어 지층명: `Schistes de Saint-Chinian`, `Gres de Marcory` 등
- 지질학적 맥락: `glacial erratic`, `Donetz Basin` 등
- 불확실한 항목은 리포트에 출력하여 사용자 확인

**실행 순서**:
1. `--dry-run`으로 분류 결과 확인
2. Type 1, Type 2, Type 3 각각의 대상 목록 출력
3. 사용자 확인 후 실행

### Phase C: 검증 및 문서화

1. **정합성 검증 쿼리**:
   ```sql
   -- country_id 일치율 (목표: 95%+)
   SELECT SUM(CASE WHEN tr.location LIKE '%' || c.name THEN 1 ELSE 0 END) * 100.0 / COUNT(*)
   FROM genus_locations gl
   JOIN taxonomic_ranks tr ON gl.genus_id = tr.id
   JOIN pc.countries c ON gl.country_id = c.id;
   ```

2. **pytest 전체 통과**: `pytest tests/` — 4개 신규 테스트 추가
   - `test_country_id_match_rate` — 95%+ 매칭률
   - `test_china_not_mapped_to_england` — 최대 오류 재발 방지
   - `test_formation_not_country_name` — formation이 국가명이 아닌지 검증
   - `test_type1_genera_have_locations` — Type 1 대상 genus_locations 존재 검증

3. **수정 전후 비교 리포트**: country별 건수 변동, formation 삭제 건수

4. **문서화**:
   - devlog: `devlog/20260228_098_fix_country_id_and_formation.md`
   - HANDOFF.md 업데이트

---

## 수정 대상 파일

| 파일 | 작업 |
|------|------|
| `scripts/fix_country_id.py` | **신규** — Phase A: country_id 일괄 수정 |
| `scripts/fix_formation_misalignment.py` | **신규** — Phase B: formation 오정렬 수정 |
| `db/trilobase.db` | UPDATE genus_locations.country_id + taxonomic_ranks.formation + genus_formations |
| `db/paleocore.db` | formations 테이블에서 orphan entries 정리 |
| `tests/test_trilobase.py` | country_id 정합성 테스트 추가 (4개) |
| `devlog/20260228_098_fix_country_id_and_formation.md` | 작업 기록 |
| `HANDOFF.md` | 상태 업데이트 |

## 검증 방법

```bash
# Phase A
python scripts/fix_country_id.py --dry-run          # 수정 대상 리포트
python scripts/fix_country_id.py                     # 실제 수정
pytest tests/                                        # 테스트

# Phase B
python scripts/fix_formation_misalignment.py --dry-run  # 분류 결과 확인
python scripts/fix_formation_misalignment.py            # 실제 수정
pytest tests/                                           # 테스트

# 수동 검증
sqlite3 db/trilobase.db "ATTACH DATABASE 'db/paleocore.db' AS pc; \
  SELECT tr.name, tr.location, gl.region, c.name as country \
  FROM genus_locations gl JOIN taxonomic_ranks tr ON gl.genus_id = tr.id \
  JOIN pc.countries c ON gl.country_id = c.id \
  WHERE tr.location LIKE '%China' LIMIT 5;"
```
