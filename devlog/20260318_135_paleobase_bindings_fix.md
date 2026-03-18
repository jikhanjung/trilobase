# 135. Paleobase Bindings — 실제 DB taxon 이름/rank 맞춤

**날짜:** 2026-03-18
**유형:** fix
**관련:** #134 (Stage 0-1), scoda-engine #042 (meta-package 구현)

---

## 배경

scoda-engine Phase 3 (합성 트리 API) 통합 테스트에서 chelicerata, ostracoda, brachiopoda의 root taxon을 찾지 못하는 문제 발견. bindings에 지정된 이름/rank가 실제 DB 데이터와 불일치.

## 수정 내용

`data/paleobase_bindings.json`:

| 패키지 | 변경 전 | 변경 후 |
|--------|--------|--------|
| chelicerata | `Chelicerata` / `Subphylum` | `CHELICERATA` / `Subphylum` |
| ostracoda | `Ostracoda` / `Class` | `OSTRACODA` / `Subclass` |
| brachiopoda | `Brachiopoda` / `Phylum` | `BRACHIOPODA` / `Phylum` |
| graptolithina | `Graptolithina` / `Phylum` | `Graptolithina` / `Class` |

trilobita (`Arthropoda` / `Phylum`)는 #134에서 새로 생성한 taxon이므로 정확.

## 검증

paleobase-0.1.0.scoda 리빌드 후 composite-tree 확장 테스트:
- node:arthropoda → trilobita(1), chelicerata(3), ostracoda(5) children 정상
- node:brachiopoda → brachiopoda(5) children 정상
- node:hemichordata → graptolithina(5) children 정상
