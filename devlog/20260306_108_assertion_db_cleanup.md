# 108: Assertion DB 데이터 정리 및 프로필 개선

**날짜:** 2026-03-06
**버전:** trilobase-assertion 0.1.3 → 0.1.4

## 변경 사항

### 1. Classification Profile 정리

- `ja2002_strict` 프로필 삭제 (edge_cache 0건, 미사용)
- `default` 프로필 → `Jell & Adrain 2002 + Adrain 2011`으로 이름/설명 변경
  - description: "Genus taxonomy from Jell & Adrain (2002) with family hierarchy from Adrain (2011)"
- edge cache rebuild hook SQL: `p.name != 'default'` → `p.id != 1` (이름 변경에 안전)
- treatise2004 프로필: id=3 → id=2로 자동 재할당

| Before | After |
|--------|-------|
| id=1 `default` | id=1 `Jell & Adrain 2002 + Adrain 2011` |
| id=2 `ja2002_strict` | 삭제 |
| id=3 `treatise2004` | id=2 `treatise2004` |

### 2. Treatise placeholder taxa rank 대문자 통일

소문자로 시작하던 rank 8건을 대문자로 통일하여 tree chart에서 정상 표시되도록 수정.

| 변경 전 | 변경 후 | 건수 |
|---------|---------|------|
| `family` | `Family` | 2 |
| `subfamily` | `Subfamily` | 3 |
| `superfamily` | `Superfamily` | 2 |
| `unrecognizable` | `Family` | 1 |

### 3. Uncertain placeholder 이름 정리

`uncertain (ch4 subfamily)` 등 chapter/rank 접미사 제거 → `Uncertain`으로 통일.

| Before | After |
|--------|-------|
| `uncertain (ch4 subfamily)` | `Uncertain` |
| `uncertain (ch4 family)` | `Uncertain` |
| `uncertain (ch4 superfamily)` | `Uncertain` |
| `uncertain (ch5 superfamily)` | `Uncertain` |
| `uncertain (ch5 family)` | `Uncertain` |

### 4. Unrecognizable Redlichioid Genera → Redlichioidea 하부 Family

- rank: `Unrecognizable` → `Family`
- parent: `Redlichiina (Suborder)` → `Redlichioidea (Superfamily)`
- children: Genus 10개 그대로 유지 (Eomalungia, Fandianaspis 등)
- `treatise_ch5_taxonomy.json` 수정: 해당 노드를 Redlichioidea children으로 이동

## 수정 파일

| 파일 | 변경 |
|------|------|
| `scripts/create_assertion_db.py` | ja2002_strict 삭제, default 이름 변경, hook SQL `p.id != 1`, 버전 0.1.4 |
| `scripts/import_treatise.py` | uncertain placeholder 이름 정리, unrecognizable → Family rank |
| `scripts/validate_treatise_import.py` | 프로필 기대값 3 → 2 |
| `data/treatise_ch5_taxonomy.json` | Unrecognizable 노드를 Redlichioidea 하위로 이동 |

## 검증 결과

- `validate_assertion_db.py`: 15/15 통과
- `validate_treatise_import.py`: 17/17 통과
- `pytest tests/`: 118/118 통과

## DB 최종 상태

```
classification_profile:
  id=1  Jell & Adrain 2002 + Adrain 2011  (5,083 edges)
  id=2  treatise2004                       (5,138 edges)

distinct ranks: Class, Family, Genus, Order, Subfamily, Suborder, Superfamily
```
