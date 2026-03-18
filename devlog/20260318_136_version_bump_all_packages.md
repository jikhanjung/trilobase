# 136. 전 패키지 버전 범프

**날짜:** 2026-03-18
**유형:** build

---

## 변경

패키지 리네임(#133) + Paleobase Stage 0-1(#134) + bindings 수정(#135) 반영하여 전 패키지 patch 버전 올림.

| 패키지 | 이전 | 변경 |
|--------|------|------|
| trilobita | 0.3.3 | **0.3.4** |
| brachiopoda | 0.2.6 | **0.2.7** |
| graptolithina | 0.1.2 | **0.1.3** |
| chelicerata | 0.1.2 | **0.1.3** |
| ostracoda | 0.1.2 | **0.1.3** |
| paleocore | 0.1.3 | **0.1.4** |
| paleobase | 0.1.0 | **0.1.1** |

## 주요 변경 사항 (이 버전에 포함)

- 패키지명 라틴화 (artifact_id, DB 파일명)
- trilobita: Phylum Arthropoda 추가
- 4개 패키지: paleocore 의존성 선언 + schema_version 메타데이터
- paleobase: bindings 실제 DB taxon 이름/rank 맞춤

## 검증

- 7개 패키지 전부 DB + .scoda 빌드 성공
- 117 tests passing
