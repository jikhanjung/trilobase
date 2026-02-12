# COW(State System Membership v2024) → SCODA import 계획

> 목적: SCODA 내부에서 **국가 단위 필터링/그룹핑**을 지원하기 위한 “근현대 주권국가(국제체제 회원)” 기준 국가 마스터 테이블 구축  
> 데이터 소스: Correlates of War Project — **State System Membership (v2024)** citeturn1view0turn2view1

---

## 1. 범위와 정의

- “국가(country/state)”는 **COW가 정의한 국제체제(State System) 회원국**을 의미한다. citeturn1view0turn2view1  
- 시간 범위: **1816년 ~ 2024-12-31** (v2024) citeturn1view0turn2view1
- 본 모듈은 우선 **필터링/그룹핑** 목적이므로, 국경(폴리곤), 행정구역 계층, 식민지/제국의 내부 단위 등은 다루지 않는다.

---

## 2. SCODA 내 배치(권장)

### 2.1 SCODA 패키지 구조 (Phase B, ZIP)

```
<dataset>.scoda (zip)
├── manifest.json
├── data.db
├── assets/
│   └── ...
└── checksums.sha256
```

### 2.2 DB 스키마(최소)

#### (A) 국가 마스터 테이블 (필수)
- 테이블명 예시: `core_country_cow`
- 데이터는 “기간(tenure)” 레코드가 여러 개일 수 있음(탈퇴/재가입) citeturn2view1

```sql
CREATE TABLE IF NOT EXISTS core_country_cow (
  cow_ccode      INTEGER NOT NULL,     -- CCode
  cow_abbrev     TEXT    NOT NULL,     -- StateAbb
  name_primary   TEXT    NOT NULL,     -- StateNme (Primary COW state name)
  start_date     TEXT    NOT NULL,     -- YYYY-MM-DD (StYear/StMonth/StDay)
  end_date       TEXT    NOT NULL,     -- YYYY-MM-DD (EndYear/EndMonth/EndDay)
  version        INTEGER NOT NULL,     -- Version (2024)
  PRIMARY KEY (cow_ccode, start_date, end_date)
);
```

#### (B) “연도→국가” 빠른 필터링을 위한 뷰/테이블(선택)
COW는 `system2024`로 “국가-연도” 베이스를 제공한다. citeturn2view1  
쿼리 빈도가 높다면 이걸 그대로 적재하는 편이 편하다.

```sql
CREATE TABLE IF NOT EXISTS core_country_year_cow (
  cow_ccode   INTEGER NOT NULL,
  cow_abbrev  TEXT    NOT NULL,
  year        INTEGER NOT NULL,
  version     INTEGER NOT NULL,
  PRIMARY KEY (cow_ccode, year)
);
```

---

## 3. 소스 파일 및 변수 매핑

COW v2024는 `.csv` 및 `.dta` 형식을 제공하며, 대표 파일은 다음과 같다. citeturn1view0turn2view1

- `states2024` : 국가 코드/약어/이름 + **국가 체제 회원 시작/종료 날짜** citeturn2view1  
  - `StateAbb`, `CCode`, `StateNme`, `StYear`, `StMonth`, `StDay`, `EndYear`, `EndMonth`, `EndDay`, `Version` citeturn2view1
- `system2024` : 국가-연도(country-year) 베이스 citeturn2view1  
  - `StateAbb`, `CCode`, `Year`, `Version` citeturn2view1

---

## 4. 가져오기(Import) 파이프라인

### 4.1 다운로드

공식 다운로드 페이지에서 v2024 자료를 받는다. citeturn1view0

- 페이지: “State System Membership (v2024)” citeturn1view0
- 일반적으로 ZIP(예: `States2024.zip`)에 `states2024.csv`, `system2024.csv` 등이 포함된다. citeturn2view1

권장(재현 가능한) 명령 예시:

```bash
# (1) 작업 디렉토리
mkdir -p vendor/cow/v2024 && cd vendor/cow/v2024

# (2) 다운로드 (URL은 COW 사이트에서 확인 후 고정)
curl -L -o States2024.zip "https://correlatesofwar.org/wp-content/uploads/States2024.zip"

# (3) 무결성 확보(선택): sha256 기록
sha256sum States2024.zip > States2024.zip.sha256

# (4) 압축 해제
unzip -o States2024.zip -d extracted/
```

> 팁: URL은 “고정값”으로 코드에 박기보다, **SCODA 빌드 스크립트에서 버전별 URL을 명시**하고, `vendor/`에 원본을 보관하는 방식을 추천.

### 4.2 전처리 규칙

- 날짜 정규화: `StYear/StMonth/StDay` → `YYYY-MM-DD`  
  - 월/일이 0 또는 누락인 경우가 있으면(케이스 존재 가능) 아래 우선순위로 정규화:
    1) 월/일 모두 유효 → 그대로  
    2) 월만 유효, 일 누락 → `01`로 대체  
    3) 월/일 모두 누락 → `01-01`로 대체  
  - 원본 값은 별도 컬럼(`start_year`, `start_month`, `start_day` …)으로 보존해도 됨(추적성).

- 레코드 중복: (cow_ccode, start_date, end_date) 기준으로 유니크.

### 4.3 적재(Load)

- `core_country_cow`: `states2024.csv` 기준으로 적재
- `core_country_year_cow`: `system2024.csv` 기준으로 적재(선택)

### 4.4 검증(Validation)

최소 검증 체크리스트:

1) `Version == 2024`인지 확인 citeturn2view1  
2) `start_date <= end_date`  
3) `cow_ccode`가 NULL/0이 아닌지  
4) `system2024`를 적재했다면:
   - `core_country_year_cow`의 각 `(cow_ccode, year)`가 **states tenure 범위** 안에 들어가는지 샘플링 검사

---

## 5. SCODA provenance(권장)

SCODA 특성상 “이 국가 목록이 어디서 왔는지”를 패키지 내부에 명확히 남긴다.

- `_scoda_provenance` 또는 `manifest.json`에 다음을 기록:
  - source: `Correlates of War Project`
  - dataset: `State System Membership`
  - version: `v2024`
  - temporal_coverage: `1816-01-01 .. 2024-12-31` citeturn1view0turn2view1
  - retrieved_at: 빌드 날짜
  - citation: COW 권장 인용문(문서 참조) citeturn2view1

---

## 6. 운영/업데이트 계획

- 업데이트 주기: COW가 새 버전을 릴리스하면(v2025 등) `vendor/cow/vYYYY/`로 추가
- 새 버전 도입 시:
  1) `core_country_cow`에 `version` 컬럼으로 공존 가능하게 유지하거나,
  2) 패키지 레벨에서 “국가 마스터는 v2024 고정” 정책을 명시(스냅샷 철학에 적합)

---

## 7. 구현 체크리스트(바로 실행용)

- [ ] `vendor/cow/v2024/` 디렉토리 생성  
- [ ] `States2024.zip` 다운로드 및 sha256 기록  
- [ ] `states2024.csv` / `system2024.csv` 존재 확인  
- [ ] 날짜 정규화 로직 구현  
- [ ] `data.db`에 `core_country_cow` 생성 및 적재  
- [ ] (선택) `core_country_year_cow` 생성 및 적재  
- [ ] 검증 쿼리/샘플링 테스트 추가  
- [ ] `manifest.json` 및 `_scoda_provenance` 기록  
- [ ] `.scoda` ZIP 패키징 + `checksums.sha256` 생성

---

## 8. 참고(공식 문서)

- State System Membership (v2024) 다운로드/개요 citeturn1view0  
- State System Membership List Codebook v2024 (변수 정의/버전 설명) citeturn2view1
