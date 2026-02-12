# Countries 테이블 데이터 품질 정리

**일시:** 2026-02-12

## 배경

COW(Correlates of War) 국가 데이터 도입을 위한 사전 작업으로 `countries` 테이블(151건)의 품질 문제를 정리.

## 수정 내용

### 1. 파싱 오류 (1건)

| 문제 항목 | 원인 | 수정 |
|-----------|------|------|
| `1980)` (id=120) | Metagnostus의 location `N Germany (originates from ... fide FORTEY, 1980)`에서 `)` 이후가 국가명으로 잘못 파싱 | genus_locations를 `N Germany`(id=28)로 재연결, 항목 삭제 |

### 2. 중복/오타 병합 (8건)

| 잘못된 항목 | 병합 대상 | genera 수 |
|------------|----------|-----------|
| `Czech Repubic` (id=130) | `Czech Republic` (id=8) | 1 |
| `Brasil` (id=127) | `Brazil` (id=80) | 1 |
| `N. Ireland` (id=87) | `N Ireland` (id=76) | 1 |
| `NWGreenland` (id=86) | `NW Greenland` (id=18) | 2 |
| `E. Kazakhstan` (id=140) | `E Kazakhstan` (id=29) | 0 |
| `arctic Russia` (id=150) | `Arctic Russia` (id=73) | 4 |
| `\u201d Spain` (id=105) | `Spain` (id=7) | 1 |
| `\u201d SE Morocco` (id=119) | `SE Morocco` (id=60) | 1 |

- `\u201d`(U+201D)는 유니코드 right double quotation mark. 원본 텍스트의 따옴표가 국가명에 포함된 파싱 오류.

### 3. 소문자 접두어 정규화 (4건)

| 변경 전 | 변경 후 |
|---------|---------|
| `central Afghanistan` | `Central Afghanistan` |
| `central Kazakhstan` | `Central Kazakhstan` |
| `central Morocco` | `Central Morocco` |
| `eastern Iran` | `Eastern Iran` |

## 결과

- **151 → 142개** (9개 삭제)
- orphaned genus_locations: 0건
- 테스트: 111개 모두 통과

## 스크립트

- `scripts/fix_countries_quality.py` — 자동 수정 스크립트 (유니코드 따옴표 2건은 별도 SQL로 처리)
