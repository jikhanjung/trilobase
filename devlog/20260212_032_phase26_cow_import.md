# Phase 26: COW State System Membership v2024 도입

**일시:** 2026-02-12

## 배경

`countries` 테이블(142개)의 국가명을 COW(Correlates of War) 주권국가 코드와 매핑하여, 명명/occurrence 보고 당시의 국가명을 정확히 추적할 수 있는 기초 데이터 구축.

## 데이터 소스

- **Correlates of War Project — State System Membership (v2024)**
- URL: https://correlatesofwar.org/data-sets/state-system-membership/
- 파일: `vendor/cow/v2024/States2024/statelist2024.csv` (244 레코드, git 추적)

## 신규 테이블

### `cow_states` (244 레코드)

COW 주권국가 마스터. 같은 `cow_ccode`에 복수 tenure(탈퇴/재가입) 가능.

| 컬럼 | 타입 | 설명 |
|------|------|------|
| cow_ccode | INTEGER | COW 국가 코드 (PK 일부) |
| abbrev | TEXT | 약어 (예: UKG, USA) |
| name | TEXT | 국가명 (예: United Kingdom) |
| start_date | TEXT | 체제 가입일 (YYYY-MM-DD) |
| end_date | TEXT | 체제 탈퇴일 (YYYY-MM-DD) |
| version | INTEGER | 2024 |

PK: `(cow_ccode, start_date)`

### `country_cow_mapping` (142 레코드)

Trilobase `countries` ↔ COW 매핑. 오버레이 방식으로 기존 `countries` 테이블 불변.

| 컬럼 | 타입 | 설명 |
|------|------|------|
| country_id | INTEGER | countries.id (PK) |
| cow_ccode | INTEGER | cow_states.cow_ccode (NULL이면 매핑 불가) |
| parent_name | TEXT | 매핑 근거 설명 |
| notes | TEXT | 매핑 방법 (exact/prefix/manual/unmappable) |

## 매핑 결과

| 방법 | 건수 | 설명 |
|------|------|------|
| exact | 50 | 이름 완전 일치 (대소문자 무시) |
| manual | 54 | 수동 매핑 사전 (하위지역→국가, 이름 불일치) |
| prefix | 33 | 방향 접두어 제거 후 매칭 (NW Mongolia → Mongolia) |
| unmappable | 5 | 매핑 불가 (cow_ccode = NULL) |
| **합계** | **142** | **매핑률 96.5%** |

### 미매핑 5건

| 항목 | 사유 |
|------|------|
| Antarctica | 주권국가 아님 |
| Central Asia | 역사적 지역명, 특정 국가 지정 불가 |
| Turkestan | 역사적 지역명 |
| Tien-Shan | 복수 국가에 걸친 산맥 |
| Kashmir | 인도/파키스탄 분쟁 지역 |

### 수동 매핑 주요 항목

| Trilobase 지역명 | COW 매핑 |
|------------------|----------|
| England, Scotland, Wales, Devon 등 | United Kingdom (200) |
| Alaska, Iowa, Texas, Pennsylvania 등 | United States of America (2) |
| South Australia, Western Australia | Australia (900) |
| Ontario, New Brunswick, NW Canada | Canada (20) |
| Sichuan, Guangxi, Henan | China (710) |
| Yakutia, Arctic Russia, Novaya Zemlya 등 | Russia (365) |
| Greenland, E/N/NW Greenland | Denmark (390) |
| USA | United States of America (2) — 이름 불일치 |
| Burma | Myanmar (775) |
| Luxemburg | Luxembourg (212) — 철자 차이 |
| Tadzikhistan | Tajikistan (702) — 구 철자 |
| North Vietnam | Vietnam/DRV (816) |

## 스크립트

- `scripts/import_cow.py` — COW 데이터 임포트 (cow_states + country_cow_mapping + provenance)
  - `--dry-run`: 미리보기
  - `--report`: 매핑 리포트만 출력

## 설계 원칙

- `countries` 테이블 불변 — 원본 텍스트 보존 (SCODA 원칙)
- `country_cow_mapping`이 오버레이 형태로 매핑만 추가
- `N Germany`와 `Germany`는 별도 항목 유지, 둘 다 같은 cow_ccode(255)에 매핑
- COW CSV 원본은 `vendor/cow/v2024/`에 git 추적

## 검증

- 테스트: 111개 전부 통과
- cow_states: 244 레코드
- country_cow_mapping: 142건 (매핑 137, 미매핑 5)
- provenance: COW 출처 추가 (1건)
