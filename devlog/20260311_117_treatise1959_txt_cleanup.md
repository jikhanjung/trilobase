# 117 — Treatise 1959 TXT 데이터 정제 + assertion DB 리빌드

**날짜**: 2026-03-11
**버전**: trilobase-assertion 0.1.7 (리빌드)

---

## 작업 개요

1. `treatise_1959_taxonomy.txt` 오타 수정 (25건)
2. 저자 이름 accent/diacritics 복원 (14명)
3. 파일 형식 검증 + 형식 문제 수정 (22건)
4. `parse_treatise_txt.py` 파서 개선 (3건)
5. JSON 갱신 및 assertion DB 리빌드

---

## 1. 오타 수정 (25건)

### Author 오타 (13건)
| 수정 전 | 수정 후 |
|---------|---------|
| Huep | Hupe |
| Masuy | Mansuy |
| Poletaeve | Poletaeva |
| Resseti | Rasetti |
| Muller (B. M.) | Miller |
| Cossman | Cossmann |
| Lochma | Lochman |
| Neoson | Nelson |
| Tjervnik | Tjernvik |
| Larmont | Lamont |
| Vogdees | Vogdes |
| Chernycheva | Chernysheva |
| Rosconi | Rusconi |
| Howel | Howell |

### 대소문자 오류 (6건)
COssmann, BUcksella, EIfliarges, SUbfamily, DIctyella, RUsconi

### 기타 (6건)
- 연도 공백: `19 35` → `1935`
- 불필요 문자: `j1934` → `1934`
- 기호 오타: `7` → `&`
- Family명: `STYGINIDA` → `STYGINIDAE`
- 불필요 쉼표: `Conoides,` → `Conoides`
- 행 분리: `Subfamily UNCERTAIN  Apatokephalina` → 별도 행

---

## 2. 저자 이름 Accent/Diacritics 복원 (14명)

DB에서 확인된 올바른 형태로 일괄 치환 (replace_all).

| 수정 전 | 수정 후 | 출처 |
|---------|---------|------|
| Hupe | Hupé | DB |
| Snajdr | Šnajdr | DB |
| Pribyl | Přibyl | DB |
| Gurich | Gürich | DB |
| Opik | Öpik | DB |
| Novak | Novák | DB |
| Ruzicka | Růžička | DB |
| Kloucek | Klouček | DB |
| Westergard | Westergård | 사용자 지정 |
| Brogger | Brøgger | 표준 |
| Lindstrom | Lindström | 표준 |
| Konig | König | 표준 |
| Loven | Lovén | 표준 |
| Kjar | Kiær | 표준 |

**학명 복원 2건**: replace_all로 학명까지 변경된 `Přibylia` → `Pribylia`, `Hupéia` → `Hupeia`

---

## 3. 형식 검증 + 수정 (22건)

### HIGH (4건)
- 연도 앞 쉼표 누락 3건 (lines 152, 869, 1048)
- Author 오타 + 괄호 불일치 1건: `Buncan` → `Duncan`, `)` → `]`

### MEDIUM (15건)
- Family/Subfamily명 대소문자 통일 14건 (mixed case → ALL CAPS)
- 중복 속명 제거 1건: `Synhomalonotus` (CALYMENINAE에서 제거, EOHOMALONOTINAE에 유지)

### LOW (3건)
- Trailing whitespace 제거 3건

---

## 4. 파서 개선 (`parse_treatise_txt.py`)

### 특수 Order 매핑
- `Order UNCERTAIN` → `Order Uncertain (Trilobita)` (기존 JSON 항목과 일치)
- `Order and Family UNCERTAIN` → `Order and Family Uncertain (Trilobita)`

### 섹션 헤더 skip
- `Unrecognizable Genera`, `Unrecognizable Asaphid Genera` → genus가 아닌 헤더로 인식, skip 처리

### 이전 실행 잔여물 정리
- JSON에 잘못 생성된 `Uncertain`, `And` order 제거

---

## 5. 0.1.5 (OCR) vs 현재 (TXT) 비교

| 항목 | 0.1.5 DB | 현재 JSON |
|------|----------|-----------|
| Genera | 1,021 | 1,457 |
| 공통 | 936 | 936 |
| 0.1.5 전용 | 85 | - |
| JSON 전용 | - | 521 |

- 0.1.5 전용 85건: OCR 오류 ~21건 + 잘못 포함된 속 ~64건
- JSON 전용 521건: TXT 수작업 입력으로 추가된 속

---

## 6. Assertion DB 리빌드 결과

| 항목 | 리빌드 전 | 리빌드 후 |
|------|----------|-----------|
| taxon | 5,604 | 5,610 |
| assertion | 7,950 | 8,331 |
| PLACED_IN | 6,893 | 7,274 |
| treatise1959 edges | 1,387 | 1,768 |
| treatise2004 edges | 1,681 | 2,053 |

Validation: 14/15 passed (기존 `orders in tree` 경고 동일)

---

## 파일 변경 목록

| 파일 | 변경 내용 |
|------|-----------|
| `data/treatise_1959_taxonomy.txt` | 오타 25건 + accent 14명 + 형식 22건 수정 |
| `data/treatise_1959_taxonomy.json` | TXT 기반 전면 갱신 (9개 order 모두 교체) |
| `scripts/parse_treatise_txt.py` | 특수 Order 매핑 + Unrecognizable skip + Pribylia 예외 |
| `db/trilobase-assertion-0.1.7.db` | 리빌드 (8,331 assertions, 8,904 edges) |
| `dist/trilobase-0.2.6.scoda` | 리빌드 |
| `dist/trilobase-assertion-0.1.7.scoda` | 리빌드 |
