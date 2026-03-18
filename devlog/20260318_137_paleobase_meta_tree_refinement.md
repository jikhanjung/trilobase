# 137. Paleobase Meta Tree 구조 개선

**날짜:** 2026-03-18
**유형:** fix + refactor
**관련:** #134 (Stage 0-1), #135 (bindings 수정)

---

## Meta Tree 구조 변경

### root 변경: Life → Metazoa
- Life → Eukaryota → Metazoa 3단 계층 → **Metazoa를 root로** 단순화
- 현재 모든 패키지가 Metazoa 하위이므로 상위 노드 불필요

### Brachiopoda/Hemichordata 노드 제거
- `node:brachiopoda`, `node:hemichordata` meta 노드 삭제
- brachiopoda(`BRACHIOPODA`, Phylum)와 graptolithina(`Graptolithina`, Class)를 Metazoa에 직접 바인딩
- 기존: Brachiopoda(meta) → BRACHIOPODA(패키지) — Phylum 중복
- 변경: Metazoa(meta) → BRACHIOPODA(패키지) — 깔끔

### Trilobita binding 수정
- `Arthropoda(Phylum)` → `Trilobita(Class)`로 변경
- meta tree의 Arthropoda 노드 아래에 Class로 직접 표시

## 최종 트리 구조

```
Metazoa (root)
├── Arthropoda (phylum) ← meta node
│   ├── Trilobita (Class) → trilobita
│   ├── Chelicerata (Subphylum) → chelicerata
│   └── Ostracoda (Subclass) → ostracoda
├── Brachiopoda (Phylum) → brachiopoda
├── Graptolithina (Class) → graptolithina
├── Bryozoa ← 비활성
├── Cnidaria ← 비활성
├── Echinodermata ← 비활성
├── Mollusca ← 비활성
└── Porifera ← 비활성
```

## 변경 파일

| 파일 | 변경 |
|------|------|
| `data/paleobase_meta_tree.json` | Life/Eukaryota/Brachiopoda/Hemichordata 노드 제거, Metazoa를 root로 |
| `data/paleobase_bindings.json` | trilobita root → Trilobita(Class), brachiopoda/graptolithina → node:metazoa 직접 바인딩 |
