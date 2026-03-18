# 138. TSF 기반 신규 패키지 6개 생성

**날짜:** 2026-03-18
**유형:** feat

---

## 개요

기존 TSF(Taxonomic Source Format) 소스 파일을 활용하여 6개 신규 SCODA 패키지를 생성.
brachiopoda 빌드 스크립트를 템플릿으로 사용.

## 신규 패키지

| 패키지 | Treatise Part | Taxa | Genera | Assertions | Profiles |
|--------|--------------|------|--------|-----------|----------|
| bryozoa | Part G | 1,050 | 850 | 1,101 | 2 (1953 + Revised 1983) |
| coelenterata | Part F | 1,204 | 901 | 1,199 | 1 (1956) |
| hexapoda | Part R | 2,824 | 2,612 | 2,811 | 1 (1992) |
| porifera | Part E | 2,815 | 2,317 | 3,452 | 2 (1955 + Revised 1972-2015) |
| echinodermata | Parts S/T/U | 1,836 | 1,364 | 1,818 | 2 (1966-67 + Revised 2011) |
| mollusca | Parts I/K/L/N | 6,026 | 4,982 | 7,405 | 2 (1957-71 + Supplements 1989-96) |

## 소스 파일 매핑

| 패키지 | Profile 1 소스 | Profile 2 소스 |
|--------|---------------|---------------|
| bryozoa | bryozoa_1953.txt | bryozoa_revised_1983.txt |
| coelenterata | coelenterata_1956.txt | — |
| hexapoda | hexapoda_1992.txt | — |
| porifera | archaeocyatha_porifera_1955.txt | archaeocyatha_revised_1972.txt + porifera_revised 2003/2004/2015 (4 files) |
| echinodermata | echinodermata_1967_vol_s.txt + 1966_vol_u1.txt + 1966_vol_u2.txt | echinodermata_2011_vol_t.txt |
| mollusca | ammonoidea_1957.txt + mollusca_1960.txt + cephalopoda_1964.txt + bivalvia 1969/1971 (3 files) | mollusca_scaphopoda_1989.txt + ammonoidea_1996.txt |

## Paleobase 업데이트

- 11개 바인딩으로 확장 (기존 5 + 신규 6)
- paleobase 버전: 0.1.1 → 0.2.0
- 신규 바인딩: bryozoa→node:bryozoa, coelenterata→node:cnidaria, hexapoda→node:arthropoda, porifera→node:porifera, echinodermata→node:echinodermata, mollusca→node:mollusca

## 생성 파일

| 카테고리 | 파일 |
|----------|------|
| 빌드 스크립트 | build_{bryozoa,coelenterata,hexapoda,porifera,echinodermata,mollusca}_db.py (6) |
| SCODA 빌더 | build_{bryozoa,coelenterata,hexapoda,porifera,echinodermata,mollusca}_scoda.py (6) |
| DB 파일 | db/{bryozoa,coelenterata,hexapoda,porifera,echinodermata,mollusca}-0.1.0.db (6) |
| paleobase | data/paleobase_bindings.json 갱신, build_paleobase_scoda.py 갱신 |
