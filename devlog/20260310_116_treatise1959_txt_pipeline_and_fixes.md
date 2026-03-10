# 116 — Treatise 1959 TXT 파이프라인 구축 + 버그 수정

**날짜**: 2026-03-10
**버전**: trilobase-assertion 0.1.7

---

## 작업 개요

1. `treatise_1959_taxonomy.txt` → JSON 변환 파이프라인 구축
2. Assertion DB 버전 0.1.7 bump
3. `import_treatise.py` EODISCINA_ID 하드코딩 버그 수정
4. Diff Tree `rank_radius` 누락 버그 수정

---

## 1. TXT → JSON 변환 파이프라인 (`parse_treatise_txt.py`)

### 배경

수작업으로 `data/treatise_1959_taxonomy.txt`를 정리하여 Treatise 1959 분류를 입력 중.
기존 JSON은 OCR 기반이라 오류가 있었으며, 수작업 TXT를 정제된 소스로 사용하기로 결정.

### 신규 스크립트: `scripts/parse_treatise_txt.py`

- TXT 파일을 파싱하여 JSON 계층 구조로 변환
- **들여쓰기 기반이 아닌 rank 키워드 기반** 계층 파악 (space/tab 혼용 문제 해결)
- **taxon name 정규화**: 첫 글자만 대문자 (`AGNOSTINAE` → `Agnostinae`)
  - 단일 단어 이름만 적용, 복합 이름 (`Order Uncertain (Trilobita)`) 은 유지
- 기존 JSON에서 TXT가 커버하는 Order만 교체, 나머지 유지 (merge 전략)
- `--dry-run` 옵션으로 사전 확인 가능

### TXT 파일 형식 규칙

```
Order AGNOSTIDA Kobayashi, 1935
  Suborder AGNOSTINA
    Family AGNOSTIDAE M'Coy, 1849
      Agnostus Brongniart, 1822 [Entomostracites pisiformis]
      ?Rudagnostus Lermontova, 1951   # ? 접두사 = questionable
    Family CLAVAGNOSTIDAE Howell, 1937
      Subfamily CLAVAGNOSTINAE ...
```

- `[...]` 괄호 (type species 정보) 자동 제거
- `?` 접두사 처리
- `nov.` 연도 없는 author 처리

### 이번 세션 반영 결과

| 항목 | 이전 | 이번 |
|------|------|------|
| Agnostida genera | 78 | 78 |
| Redlichiida families | 2 | 14 |
| Redlichiida genera | 22 | 88 |
| TXT 전체 genera | 100 | 166 |

Redlichiina suborder (12 families, 66 genera) 추가 완료.

### 사용법

```bash
python scripts/parse_treatise_txt.py           # JSON 업데이트
python scripts/parse_treatise_txt.py --dry-run # 미리보기만
python scripts/create_scoda.py                 # scoda 빌드
```

---

## 2. Assertion DB 버전 0.1.7 bump

```bash
python scripts/bump_version.py assertion 0.1.7
```

---

## 3. EODISCINA_ID 하드코딩 버그 수정 (`import_treatise.py`)

### 증상

```
7667|Spinagnostidae|PLACED_IN|Agnostida     ← 잘못됨
7668|EODISCOIDEA|PLACED_IN|Spinagnostidae   ← 잘못됨
```

### 원인

`EODISCINA_ID = 5353`으로 하드코딩되어 있었는데, Redlichiida 데이터 추가로 인해 taxon ID가 변경됨:
- id=5353 → Spinagnostidae (Family)  ← 실제
- id=5354 → Eodiscina (Suborder)     ← 실제

`_match_or_create()`에서 `name == "eodiscina"` 특수 처리 시 잘못된 ID 반환 → 엉뚱한 taxon이 Eodiscina로 사용됨.

### 수정

하드코딩 상수를 `main()`에서 DB 동적 조회로 변경:

```python
# 수정 전
EODISCINA_ID = 5353
AGNOSTIDA_ID = 5341

# 수정 후
AGNOSTIDA_ID = _resolve_id("Agnostida", "Order")
EODISCINA_ID = _resolve_id("Eodiscina", "Suborder")
```

### 수정 후 결과

```
6205|Spinagnostidae|PLACED_IN|Agnostina      ✓ (treatise1959)
7571|Spinagnostidae|PLACED_IN|AGNOSTOIDEA    ✓ (treatise2004)
7668|EODISCOIDEA|PLACED_IN|Eodiscina         ✓ (treatise2004)
```

---

## 4. Diff Tree rank_radius 누락 버그 수정

### 증상

Diff Tree에서 Agnostida를 root로 보면 Subfamily가 Genus보다 바깥쪽에 표시.

### 원인

`diff_tree` 뷰의 `tree_chart_options`에 `rank_radius`가 없어 **auto-alignment (평균 depth 기반)** 사용.

전체 트리에서 대부분의 Genus는 Family 바로 밑 (depth 4)에 위치하고, Subfamily는 Agnostida/Redlichiida 일부에만 존재 (depth 5). 결과적으로:
- 평균 Genus depth ≈ 4 (대다수 직계 Family 하위)
- 평균 Subfamily depth ≈ 5

→ Genus(4) < Subfamily(5) → Genus가 안쪽, Subfamily가 바깥쪽으로 역전.

### 수정

`create_assertion_db.py`의 `diff_tree` 뷰에 `rank_radius` 명시 추가:

```python
"tree_chart_options": {
    "source_view": "tree_chart",
    "rank_radius": {
        "_root": 0,
        "Class": 0.08,
        "Order": 0.20,
        "Suborder": 0.32,
        "Superfamily": 0.44,
        "Family": 0.56,
        "Subfamily": 0.70,
        "Genus": 1.0,
    },
    "diff_mode": { ... }
}
```

기존 `tree_chart` 뷰와 동일한 rank_radius 값 사용. scoda-engine 변경 없음.

---

## 파일 변경 목록

| 파일 | 변경 내용 |
|------|-----------|
| `scripts/parse_treatise_txt.py` | 신규: TXT→JSON 변환 스크립트 |
| `data/treatise_1959_taxonomy.json` | Agnostida + Redlichiida 교체 (TXT 기반, name 정규화) |
| `scripts/import_treatise.py` | EODISCINA_ID/AGNOSTIDA_ID 동적 조회로 변경 |
| `scripts/create_assertion_db.py` | diff_tree에 rank_radius 추가, ASSERTION_VERSION 0.1.7 |
| `.gitignore` | `data/Treatise 1959 classification only.pdf` 추가 |
| `db/trilobase-assertion-0.1.7.db` | 신규 생성 |
| `dist/trilobase-assertion-0.1.7.scoda` | 신규 생성 |
