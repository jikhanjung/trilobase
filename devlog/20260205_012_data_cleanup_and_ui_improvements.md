# Phase 11 후속: 데이터 정리 및 UI 개선

**날짜:** 2026-02-05

## 작업 내용

### 1. 트리뷰 상세정보 링크 추가

각 트리 노드(Class, Order, Suborder, Superfamily, Family)에 info 아이콘 추가
- hover 시 아이콘 표시
- 클릭 시 해당 rank의 상세정보 모달 표시

**새 API:**
- `GET /api/rank/<id>` - 분류 계층 상세정보

### 2. Author 필드 데이터 정리

원본 데이터에서 발생한 파싱 오류 수정:

**쉼표 두 개 → 하나:**
```
Hupé,, 1953 → Hupé, 1953
```

**연도 뒤 각주 번호 제거:**
```
Salter,, 186430 → Salter, 1864
Kobayashi,, 19393 → Kobayashi, 1939
Moore,, 195912 → Moore, 1959
```

**수정된 레코드:** 약 65건 (Order, Suborder, Superfamily, Family)

### 3. nov. 처리 (Adrain, 2011)

원본에서 "nov."로 표기된 새 분류군은 Adrain (2011)에서 명명된 것:

| 수정 전 | 수정 후 | Author |
|---------|---------|--------|
| Aulacopleurida nov. | Aulacopleurida | Adrain, 2011 |
| Olenida nov. (11 families) | Olenida | Adrain, 2011 |

### 4. Proetida 이름/Author 분리

```
Name: "Proetida Fortey &" → "Proetida"
Author: "Owens,, 197521" → "Fortey & Owens, 1975"
```

### 5. genera_count 재계산 및 taxa_count 제거

**문제:**
- `genera_count`: 원본 파일 통계 (부정확)
- `taxa_count`: 실제 DB 레코드 수 (중복 정보)
- `notes`: 원본 텍스트 통계

**해결:**
- `genera_count`를 실제 하위 Genus 수로 재계산
- `taxa_count` 참조 제거 (API, JavaScript)
- `notes`는 원본 참고용으로 유지

**예시 (Asaphidae):**
```
Before: genera_count=155, taxa_count=185, notes="(156 genera, 850 species)"
After:  genera_count=185, notes="(156 genera, 850 species)"
```

## 수정된 파일

- `app.py` - rank detail API 추가, taxa_count 참조 제거
- `static/js/app.js` - info 아이콘 추가, showRankDetail 함수, taxa_count 표시 제거
- `static/css/style.css` - info 아이콘 스타일
- `trilobase.db` - author 필드 정리, genera_count 재계산

## SQL 실행 내역

```sql
-- 쉼표 두 개 → 하나
UPDATE taxonomic_ranks SET author = REPLACE(author, ',,', ',') WHERE author LIKE '%,,%';

-- 연도 뒤 각주 번호 제거
UPDATE taxonomic_ranks SET author = SUBSTR(author, 1, INSTR(author, '18') + 3)
WHERE rank != 'Genus' AND author GLOB '*18[0-9][0-9][0-9]*';

UPDATE taxonomic_ranks SET author = SUBSTR(author, 1, INSTR(author, '19') + 3)
WHERE rank != 'Genus' AND author GLOB '*19[0-9][0-9][0-9]*';

-- nov. 처리
UPDATE taxonomic_ranks SET name = 'Aulacopleurida', author = 'Adrain, 2011' WHERE id = 99;
UPDATE taxonomic_ranks SET name = 'Olenida', author = 'Adrain, 2011' WHERE id = 129;

-- Proetida 수정
UPDATE taxonomic_ranks SET name = 'Proetida', author = 'Fortey & Owens, 1975' WHERE id = 96;

-- genera_count 재계산
UPDATE taxonomic_ranks SET genera_count = (
    SELECT COUNT(*) FROM taxonomic_ranks g
    WHERE g.parent_id = taxonomic_ranks.id AND g.rank = 'Genus'
) WHERE rank = 'Family';
```
