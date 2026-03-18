# 139. Meta Tree 구조 수정 — Phylum root 정리 + Graptolithina 배치

**날짜:** 2026-03-18
**유형:** fix
**관련:** #138 (신규 패키지 6개), #137 (meta tree 구조)

---

## 문제

신규 패키지 6개를 paleobase에 바인딩한 후 발견된 이슈:

1. **Phylum 중복**: meta tree 노드(예: `node:bryozoa`)와 패키지 내 Phylum(예: `Bryozoa`)이 같은 rank에서 중복 표시
2. **Coelenterata Phylum 누락**: 패키지 내에 Phylum 노드가 없어 5개 Class가 각각 root로 표시됨
3. **Mollusca/Echinodermata binding 오류**: Phylum이 패키지 내에 존재하는데 하위 Class가 binding root_taxon으로 지정됨
4. **Graptolithina 위치**: Metazoa 직속 → Hemichordata 아래로 이동 필요

## 수정

### Meta Tree 단순화
- `node:bryozoa`, `node:porifera`, `node:cnidaria`, `node:echinodermata`, `node:mollusca` 제거
- 유지: `node:metazoa` (root), `node:arthropoda`, `node:hemichordata`
- 원칙: 패키지 내에 Phylum이 있으면 meta tree 노드 불필요. meta tree 노드는 **여러 패키지를 묶는 경우에만** 사용 (Arthropoda → trilobita+chelicerata+ostracoda+hexapoda)

### Coelenterata Phylum 추가
- `build_coelenterata_db.py`에 Phylum Coelenterata 생성 로직 추가
- 5개 orphan root Class (Protomedusae, Dipleurozoa, Scyphozoa, Hydrozoa, Anthozoa)를 Phylum 아래로 연결
- taxa 1204→1205, edges 1199→1204

### Bindings 정리
- 모든 Phylum-level 패키지를 `node:metazoa`에 직접 바인딩
- Graptolithina를 `node:hemichordata`에 바인딩
- root_taxon을 실제 Phylum으로 수정 (Mollusca, Echinodermata, Coelenterata 등)

## 최종 트리 구조

```
Metazoa (root)
├── Arthropoda (meta node)
│   ├── Trilobita (Class) → trilobita
│   ├── Chelicerata (Subphylum) → chelicerata
│   ├── Ostracoda (Subclass) → ostracoda
│   └── Insecta (Class) → hexapoda
├── Hemichordata (meta node)
│   └── Graptolithina (Class) → graptolithina
├── Brachiopoda (Phylum) → brachiopoda
├── Bryozoa (Phylum) → bryozoa
├── Coelenterata (Phylum) → coelenterata
├── Echinodermata (Phylum) → echinodermata
├── Mollusca (Phylum) → mollusca
└── Porifera (Phylum) → porifera
```
