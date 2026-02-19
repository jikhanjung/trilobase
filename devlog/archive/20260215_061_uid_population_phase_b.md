# UID Population Phase B — 품질 수정 + same_as_uid 연결 완료

**날짜:** 2026-02-15
**계획:** `devlog/20260215_P43_uid_population_phase_b.md`

## 목표

Phase A에서 이미 geographic_regions/countries를 100% 채웠으나,
P43 계획에서 지적한 품질 이슈 3가지를 수정한다.

## 배경

Phase A 구현 시, countries 테이블의 primary 선정이 "ISO 코드별 최단 이름"
기준이었다. 이로 인해 서브내셔널 지역(Sumatra, NW Korea)이 해당 ISO 코드의
primary로 잘못 선정됨.

## 발견된 이슈

### 이슈 1: countries primary 선정 오류

| ISO | 잘못된 primary | 올바른 primary |
|-----|--------------|--------------|
| ID | Sumatra (서브내셔널) | Indonesia (국가) |
| KP | NW Korea (서브내셔널) | North Korea (국가) |

원인: shortest-name 규칙이 서브내셔널 지역을 우선함.

### 이슈 2: geographic_regions country-level UID 불일치

| name | geographic_regions uid | countries uid | 원인 |
|------|----------------------|--------------|------|
| Indonesia | iso3166-1:ID | fp_v1:sha256:... | countries에서 Sumatra가 ID primary |
| North Korea | iso3166-1:KP | fp_v1:sha256:... | countries에서 NW Korea가 KP primary |
| South Korea | iso3166-1:KR-2 | fp_v1:sha256:... | collision suffix -2 |
| Turkey | fp_v1:sha256:... | iso3166-1:TR | pycountry가 "Türkiye" 변경 미인식 |

### 이슈 3: Alborz Mtns / Alborz Mts 중복

Turkestan 하위에 같은 산맥의 표기 변형 2건 존재.
- Alborz Mtns (id=482): genus 1건 참조
- Alborz Mts (id=483): genus 1건 참조
- same_as_uid 미연결

## 수정 내용

**파일:** `scripts/populate_uids_phase_b.py` (신규)

### Step 1: countries primary 교정

`COUNTRY_PRIMARY_OVERRIDES` 딕셔너리로 2건 교정:
- Sumatra: iso3166-1:ID → fp_v1 (demoted)
- Indonesia: fp_v1 → iso3166-1:ID (promoted)
- NW Korea: iso3166-1:KP → fp_v1 (demoted)
- North Korea: fp_v1 → iso3166-1:KP (promoted)

UNIQUE 제약 충돌 방지: temp UID → swap → final UID 3단계 교체.

### Step 2: geographic_regions country-level 동기화

countries 테이블 수정 후, 불일치 4건을 countries.uid에 맞춰 업데이트:
- Indonesia, North Korea: countries가 이제 iso3166-1 → gr도 iso3166-1
- South Korea: collision suffix -2 제거, fp_v1로 동기화
- Turkey: fp_v1 → iso3166-1:TR (countries와 동일)

### Step 3: Alborz same_as_uid 연결

- Alborz Mts (id=483).same_as_uid = Alborz Mtns uid (id=482의 uid)

### same_as_uid에 대한 판단

country-level geographic_regions와 countries 테이블은 **동일 엔티티**를 표현하며
이미 **동일 UID**를 공유한다. same_as_uid는 "덜 권위있는 → 더 권위있는" 관계용이므로,
동일 엔티티 간에는 설정하지 않는 것이 올바르다.

## 수정 후 검증

```
countries: 142/142 UIDs (dupes=0)
geographic_regions: 562/562 UIDs (dupes=0)
country-level gr ↔ countries mismatches: 0
Alborz Mtns: same_as_uid=NULL (primary)
Alborz Mts: same_as_uid=SET (→ Alborz Mtns)
```

## 테스트

`TestUIDPhaseB` 4개 신규:

| 테스트 | 검증 |
|--------|------|
| `test_country_level_gr_matches_countries` | country-level gr ↔ countries UID 일치 |
| `test_no_collision_suffixes` | collision suffix (-2, -3) 없음 |
| `test_same_as_uid_references_valid_uid` | same_as_uid가 유효한 uid 참조 |
| `test_iso_primary_is_actual_country` | sub-regional 이름이 iso3166-1 primary 아님 |

```
212 passed in 159s
```

## 신규/변경 파일

| 파일 | 유형 |
|------|------|
| `scripts/populate_uids_phase_b.py` | 신규 |
| `paleocore.db` | 변경 (6건 uid 수정 + 1건 same_as_uid) |
| `tests/test_runtime.py` | 변경 (TestUIDPhaseB 4개 추가) |

## 다음 단계

- **Phase C** (P44): bibliography DOI/fp + formations lexicon/fp
