# Assertion DB v0.1.8: 탭 라벨 간소화 + 검증 개선

**Date:** 2026-03-11

## 변경 사항

### 1. 탭 라벨 간소화 (create_assertion_db.py)

최상위 탭 텍스트를 짧게 변경하여 탭 바 공간 절약:

| 기존 | 변경 |
|------|------|
| Taxonomy Tree | Taxonomy |
| All Genera | Genera |
| All Assertions | Assertions |
| Classification Profiles | Profiles |
| Profile Comparison | Comparison |
| Tree Chart | Tree |

한 단어인 탭(References, Formations, Countries, Chronostratigraphy)은 그대로 유지.

Compound view 내부 sub-view: Morphing → Animation

### 2. 검증 스크립트 개선 (validate_assertion_db.py)

기존 "orders in tree" 체크는 default profile의 `v_taxonomy_tree`만 확인하여
Treatise import 후 항상 실패(12/16)했음.

**변경**: 프로필별로 Order 수를 개별 체크하도록 수정.

| 프로필 | Orders |
|--------|--------|
| Jell & Adrain 2002 + Adrain 2011 | 13 |
| treatise1959 | 9 |
| treatise2004 | 9 |

검증 결과: 17/17 전체 통과.

### 3. Assertion DB v0.1.8 빌드

v0.1.7 → v0.1.8 버전 범프 + 리빌드 (Treatise 1959 + 2004 import 포함).

### 4. R03 설계 문서 작성

`devlog/20260311_R03_comprehensive_scope_and_removal.md`:
Comprehensive scope와 taxon removal 처리에 대한 설계 리뷰.

- Reference × taxon 조합별 coverage (comprehensive/sparse) 모델링
- Comprehensive removal 로직: scope 내 미언급 taxa의 edge 삭제
- Removed taxa 사이드 패널 UI 설계

## scoda-engine 변경 (별도 레포)

- Show Text / Hide Text 버튼 → 눈 아이콘(bi-eye / bi-eye-slash) + T
- Morph animation: node.x (angle), node.y (radius) interpolation 추가
  → 라벨 각도가 중간에 갑자기 바뀌던 문제 해결
- _drawMorphLabels: shortest-path angular interpolation으로 180° 경계 부드럽게 전환
- Diff legend 위치: 캔버스 왼쪽 위 → 오른쪽 아래 (breadcrumb과 겹침 해소)
