# COW(State System Membership v2024) → Trilobase countries 보강 계획

> 목적: 기존 `countries` 테이블(142개)의 국가명을 COW 주권국가 코드와 매핑하여, 명명/occurrence 보고 당시의 국가명을 정확히 추적할 수 있는 기초 데이터 구축
> 데이터 소스: Correlates of War Project — **State System Membership (v2024)**

---

## 1. 배경

### 1.1 현재 상태

`countries` 테이블 142개 항목은 Jell & Adrain (2002) 원문에서 추출한 지명으로, 세 가지 유형이 혼재:

| 유형 | 예시 | 대략 건수 |
|------|------|----------|
| 주권국가 | France, China, USA | ~50 |
| 방향 접두어 + 국가/지역 | NW Mongolia, SE Morocco | ~49 |
| 하위 행정구역/지역명 | England, Alaska, Sichuan, Yakutia | ~36 |

- 데이터 품질 정리 완료 (151→142건, `devlog/20260212_031_countries_data_quality.md`)
- COW는 주권국가만 다루므로 직접 매칭률은 약 33% (50/142)

### 1.2 `genus_locations.region` 필드 분석

`genus_locations` 테이블 4,841건 중:
- `region` 있음: 3,320건 (69%)
- `region` 없음: 1,521건 (31%)

**현재 구조의 특성:**

- `England`, `Scotland`, `Wales`는 독립 country 항목 (UK라는 항목은 없음)
- `N Germany`, `E Kazakhstan` 등 방향 접두어도 독립 country 항목 (`Germany`와 별도)
- 같은 genus가 `N Germany`와 `Germany` 양쪽에 동시 연결되는 일은 없음
- `region`은 country 내부의 더 세부적인 지역:

| country | region 예시 |
|---------|-----------|
| Canada | Quebec, British Columbia, Alberta, Newfoundland, Ontario |
| China | Guizhou, Liaoning, Hunan, Anhui, Jiangsu, Hubei |
| England | Devon, Shropshire, Shelve |
| Scotland | Fife, Lothian |
| Wales | Dyfed, Gwynedd, Powys |

### 1.3 설계 원칙

- `countries` 테이블을 통합/재구조화하지 않음 — 원본 텍스트의 지명을 그대로 보존 (SCODA 원칙)
- `country_cow_mapping`이 오버레이 형태로 매핑만 추가 → 기존 데이터에 파괴적 변경 없음
- `N Germany`와 `Germany`는 별도 항목으로 유지하되, 둘 다 같은 `cow_ccode`(독일)에 매핑

### 1.4 목적

- 기존 `countries` 항목을 COW 주권국가에 매핑 (가능한 것만)
- 하위 지역(England→UK, Alaska→USA 등)도 상위 국가에 연결
- 매핑 불가능한 역사적 지명은 원본 보존하되 표시

---

## 2. DB 스키마

기존 테이블 컨벤션(`countries`, `formations`, `synonyms`)에 맞춰 명명.

### 2.1 `cow_states` — COW 주권국가 마스터

```sql
CREATE TABLE IF NOT EXISTS cow_states (
    cow_ccode    INTEGER NOT NULL,     -- CCode (예: 200=UK, 2=USA)
    abbrev       TEXT    NOT NULL,     -- StateAbb (예: UKG, USA)
    name         TEXT    NOT NULL,     -- StateNme (예: United Kingdom)
    start_date   TEXT    NOT NULL,     -- YYYY-MM-DD (체제 가입일)
    end_date     TEXT    NOT NULL,     -- YYYY-MM-DD (체제 탈퇴일)
    version      INTEGER NOT NULL DEFAULT 2024,
    PRIMARY KEY (cow_ccode, start_date)
);
```

- 탈퇴/재가입으로 같은 `cow_ccode`에 여러 tenure 레코드 가능
- `system2024` (국가-연도 테이블)은 **적재하지 않음** — start/end 범위로 충분

### 2.2 `country_cow_mapping` — Trilobase countries ↔ COW 매핑

```sql
CREATE TABLE IF NOT EXISTS country_cow_mapping (
    country_id   INTEGER NOT NULL,     -- countries.id (Trilobase 기존)
    cow_ccode    INTEGER,              -- cow_states.cow_ccode (NULL이면 매핑 불가)
    parent_name  TEXT,                 -- 매핑 근거 (예: "England → United Kingdom")
    notes        TEXT,                 -- 특이사항
    FOREIGN KEY (country_id) REFERENCES countries(id),
    PRIMARY KEY (country_id)
);
```

- `cow_ccode`가 NULL인 항목: 매핑 불가능 (예: `Central Asia`, `Tien-Shan`)
- 방향 접두어 항목(`NW Mongolia`)은 부모 국가의 cow_ccode로 매핑

---

## 3. 소스 파일 및 변수 매핑

COW v2024는 `.csv` 형식을 제공한다.

- `states2024.csv`: 국가 코드/약어/이름 + 체제 회원 시작/종료 날짜
  - `StateAbb`, `CCode`, `StateNme`, `StYear`, `StMonth`, `StDay`, `EndYear`, `EndMonth`, `EndDay`, `Version`
- `system2024.csv`: 국가-연도 베이스 → **사용하지 않음**

---

## 4. 구현 단계

### Step 1: 원본 다운로드 및 보관

```bash
mkdir -p vendor/cow/v2024
cd vendor/cow/v2024
# COW 사이트에서 States2024.zip 다운로드
sha256sum States2024.zip > States2024.zip.sha256
unzip -o States2024.zip
```

- `vendor/` 디렉토리를 `.gitignore`에 추가
- 원본 CSV를 그대로 보관 (재현 가능성)

### Step 2: `cow_states` 테이블 생성 및 적재

`scripts/import_cow.py` 스크립트 작성:

1. `states2024.csv` 읽기
2. 날짜 정규화: `StYear/StMonth/StDay` → `YYYY-MM-DD`
   - 월/일이 0 또는 누락 → `01`로 대체
3. `cow_states` 테이블에 INSERT
4. 검증:
   - `start_date <= end_date`
   - `cow_ccode`가 NULL/0이 아닌지
   - Version == 2024

### Step 3: `country_cow_mapping` 생성

자동 매핑 + 수동 보완:

1. **자동 매핑**: `countries.name`과 `cow_states.name`의 완전 일치/유사 일치
2. **방향 접두어 추출**: `NW Mongolia` → `Mongolia` → COW 매칭
3. **지역→국가 수동 매핑**: 별도 매핑 사전 필요

| Trilobase 지역명 | COW 매핑 |
|------------------|----------|
| England, Scotland, Wales, N Ireland, Devon | United Kingdom (200) |
| Alaska, Iowa, Massachusetts, Missouri, Pennsylvania, Tennessee, Texas | USA (2) |
| South Australia, Western Australia, Australian Capital Territory | Australia (900) |
| New Brunswick, Ontario, NW Canada | Canada (20) |
| Sichuan, Guangxi, Henan | China (710) |
| Yakutia, Gorny Altay, Novaya Zemlya, Arctic Russia, NW Russian Platform | Russia (365) |
| Gotland | Sweden (380) |
| Bavaria, Eifel Germany | Germany (255) |
| Sumatra, Timor | Indonesia (850) |
| Spitsbergen | Norway (385) |
| Kashmir | 매핑 보류 (인도/파키스탄 분쟁 지역) |
| Montagne Noire | France (220) |
| Central Asia, Turkestan, Tien-Shan | 매핑 불가 (cow_ccode = NULL) |

4. **매칭률 확인 후 잔여 항목 수동 처리**

### Step 4: provenance 기록

`provenance` 테이블에 추가:

```sql
INSERT INTO provenance (source_type, citation, description, year, url)
VALUES ('reference', 'Correlates of War Project. State System Membership (v2024)',
        'Sovereign state codes for country name normalization', 2024,
        'https://correlatesofwar.org/data-sets/state-system-membership/');
```

### Step 5: 검증 및 테스트

- `cow_states` 레코드 수 확인 (COW v2024 기준)
- `country_cow_mapping` 매핑률 리포트: 매핑 성공 / NULL / 총 142건
- 기존 API(`/api/metadata` 등)에 영향 없음 확인
- 기존 111개 테스트 통과 확인

---

## 5. `.gitignore` 추가

```
vendor/
```

---

## 6. 구현 체크리스트

- [ ] `vendor/cow/v2024/` 디렉토리 생성, CSV 다운로드
- [ ] `scripts/import_cow.py` 작성
- [ ] `cow_states` 테이블 생성 및 적재
- [ ] `country_cow_mapping` 테이블 생성
- [ ] 자동 매핑 (완전 일치 + 방향 접두어 추출)
- [ ] 수동 매핑 사전 (지역→국가)
- [ ] 매핑률 리포트 출력
- [ ] `provenance` 테이블에 COW 출처 추가
- [ ] 테스트 통과 확인
- [ ] devlog 기록

---

## 7. 참고

- Correlates of War Project: State System Membership (v2024)
- State System Membership List Codebook v2024
