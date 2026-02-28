# 098 — Treatise Chapter 4 & 5 Taxonomy Tree Extraction

**Date**: 2026-02-28

## Summary

Treatise on Invertebrate Paleontology (2004 revised edition) PDF에서 삼엽충 분류 체계(taxonomy tree)를 추출하여 JSON으로 저장.

## 작업 내용

### Chapter 5 (pp. 404–481): Order REDLICHIIDA
- `data/treatise_ch5_taxonomy.json` 생성
- 2 suborders, 6 superfamilies, 23 families, 22 subfamilies, 170 genera, 26 subgenera

### Chapter 4 (pp. 331–403): Order AGNOSTIDA
- `data/treatise_ch4_taxonomy.json` 생성
- 2 suborders, 4 superfamilies, 17 families, 13 subfamilies, 160 genera, 25 subgenera

### 분류 체계 구조

**Agnostida** 주요 구조:
```
Order AGNOSTIDA
├── Suborder AGNOSTINA
│   ├── Superfamily AGNOSTOIDEA (9 families, 160+ genera)
│   ├── Superfamily UNCERTAIN (Phalacromidae, Sphaeragnostidae)
│   └── Superfamily CONDYLOPYGOIDEA (Condylopygidae)
└── Suborder EODISCINA
    └── Superfamily EODISCOIDEA (6 families, 50+ genera)
```

## JSON 포맷

계층적 nested children 구조:
```json
{
  "rank": "order",
  "name": "AGNOSTIDA",
  "author": "SALTER",
  "year": 1864,
  "children": [...]
}
```
- `uncertain: true` — 배치가 불확실한 분류군 표시
- Subfamily/Family UNCERTAIN — 소속이 확정되지 않은 속들

## 생성 파일

| 파일 | 크기 | 내용 |
|------|------|------|
| `data/treatise_ch4_taxonomy.json` | ~48KB | Order AGNOSTIDA 전체 |
| `data/treatise_ch5_taxonomy.json` | ~55KB | Order REDLICHIIDA 전체 |

## 소스 PDF

- `data/Treatise Chapter 4.pdf` (51.3MB, pp. 331–403)
- `data/Treatise Chapter 5.pdf` (84.6MB, pp. 404–481)
