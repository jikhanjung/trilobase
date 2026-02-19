# parent_id NULL — 유효 Genus 13건 Family 연결

**날짜:** 2026-02-19
**유형:** 데이터 수정 (bugfix)

## 배경

`parent_id IS NULL`인 Genus 342건 중 `is_valid=1`인 85건을 분석한 결과,
대부분은 원본(Jell & Adrain 2002)에서 family가 불확실(`?`, `FAMILY UNCERTAIN`, `INDET`)하여
파싱 시 의도적으로 `family` 필드를 비운 것이었다.

그러나 13건은 `raw_entry`에 확정적인 family 이름이 있는데도 파싱되지 않은 누락이었다.

## 원인 분석

파싱 실패 원인 추정:
- 콜론(`:`) vs 세미콜론(`;`) 구분자 불일치 (Esseigania, Illaenoides, Mindycrusta, Wutingaspis)
- `?MDEV` 처럼 temporal code에 `?`가 붙어 family 파싱 로직이 혼동
- `UCAM/LORD` 같은 복합 temporal code
- 텍스트 패턴이 표준 포맷에서 벗어난 경우

## 수정 대상 13건

| id | Genus | Family (raw_entry) | Family ID | 비고 |
|----|-------|-------------------|-----------|------|
| 373 | Alokistocare | ALOKISTOCARIDAE | 100 | 세미콜론 앞 위치 불규칙 |
| 449 | Andinacaste | CALMONIIDAE | 77 | |
| 534 | Archaeopleura | ODONTOPLEURIDAE | 72 | temporal: UCAM/LORD |
| 606 | Astycoryphe | TROPIDOCORYPHIDAE | 98 | Eifel 지명 뒤 콤마 |
| 996 | Carniphillipsia | PROETIDAE | 97 | temporal: PENN/LPERM |
| 1706 | Eoleonaspis | ODONTOPLEURIDAE | 72 | temporal: UORD/LSIL |
| 2089 | Harringtonacaste | ACASTIDAE | 76 | temporal: USIL/LDEV |
| 2721 | Linguaproetus | TROPIDOCORYPHIDAE | 98 | ?MDEV — family는 확정 |
| 3737 | Pericopyge | DALMANITIDAE | 79 | temporal: USIL/LDEV |
| 4049 | Protillaenus | KINGSTONIIDAE | 173 | synonym 주석 뒤 콤마 |
| 4530 | Semadiscus | WEYMOUTHIIDAE | 7 | |
| 4718 | Strictagnostus | AGNOSTIDAE | 201 | |
| 5194 | Wutingaspis | REDLICHIIDAE | 43 | 콜론(`:`) 사용 |

## 수정 내용

```sql
UPDATE taxonomic_ranks SET parent_id = 100, family = 'Alokistocaridae'   WHERE id = 373;
UPDATE taxonomic_ranks SET parent_id = 77,  family = 'Calmoniidae'       WHERE id = 449;
UPDATE taxonomic_ranks SET parent_id = 72,  family = 'Odontopleuridae'   WHERE id = 534;
UPDATE taxonomic_ranks SET parent_id = 98,  family = 'Tropidocoryphidae' WHERE id = 606;
UPDATE taxonomic_ranks SET parent_id = 97,  family = 'Proetidae'         WHERE id = 996;
UPDATE taxonomic_ranks SET parent_id = 72,  family = 'Odontopleuridae'   WHERE id = 1706;
UPDATE taxonomic_ranks SET parent_id = 76,  family = 'Acastidae'         WHERE id = 2089;
UPDATE taxonomic_ranks SET parent_id = 98,  family = 'Tropidocoryphidae' WHERE id = 2721;
UPDATE taxonomic_ranks SET parent_id = 79,  family = 'Dalmanitidae'      WHERE id = 3737;
UPDATE taxonomic_ranks SET parent_id = 173, family = 'Kingstoniidae'     WHERE id = 4049;
UPDATE taxonomic_ranks SET parent_id = 7,   family = 'Weymouthiidae'     WHERE id = 4530;
UPDATE taxonomic_ranks SET parent_id = 201, family = 'Agnostidae'        WHERE id = 4718;
UPDATE taxonomic_ranks SET parent_id = 43,  family = 'Redlichiidae'      WHERE id = 5194;
```

## 결과

- parent_id NULL Genus: 342 → **329** (valid: 85→72, invalid: 257 변동 없음)
- 13건 모두 원본 raw_entry에 명시된 family와 DB의 Family 레코드가 1:1 매칭됨
- 데이터 출처: 전부 Jell & Adrain (2002) — adrain2011.txt에는 해당 없음

## 남은 parent_id NULL 현황

| 구분 | 건수 | 설명 |
|------|------|------|
| invalid (is_valid=0) | 257 | synonym, misspelling, preoccupied 등 — family 정보 자체 없음 (정상) |
| FAMILY UNCERTAIN | 22 | Suborder만 명시, family 미확정 |
| ?FAMILY | 29 | 불확실한 family 배정 (`?PROETIDAE` 등) |
| INDET | 14 | 분류 미결정 |
| ??FAMILY | 2 | 매우 불확실 |
| UNCERTAIN(other) | 2 | 기타 불확실 |
| FAMILY: (콜론) | 2 | 콜론 구분자 사용 (family는 확정이나 ?가 붙은 것으로 이전 분석에서 분류) |
| **합계** | **329** | |
