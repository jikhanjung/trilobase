# Phase 1: 줄 정리 (Line Normalization) 완료

**날짜:** 2026-02-04
**작업자:** Claude Opus 4.5

## 목표

Jell & Adrain (2002) PDF에서 추출한 `trilobite_genus_list.txt` 파일을 "한 genus = 한 줄" 형식으로 정리

## 발견된 문제

1. **Soft hyphen (U+00AD)**: PDF 줄바꿈 시 삽입된 보이지 않는 하이픈 (1,357건)
   - 예: `Lisogor­agnostus` → `Lisogoragnostus`

2. **합쳐진 genera**: 여러 genus가 한 줄에 있는 경우 (56건)
   - 예: `Albansia ... MCAM. Albertella WALCOTT, 1908 ...`

3. **분리된 continuation**: `[j.s.s. of ...]` 등이 별도 줄로 분리됨 (106건)

4. **빈 줄/깨진 줄**: 빈 줄, 깨진 문자만 있는 줄 (16건)
   - 예: `˘ˇ˘. ˇ˙˝`

## 작업 내용

### 1. 정규화 스크립트 개발
`scripts/normalize_lines.py` 작성:
- `is_garbage_line()`: 빈 줄/깨진 줄 감지
- `is_continuation_line()`: continuation 줄 감지 (병합 대상)
- `find_genus_split_points()`: 합쳐진 genera 분리 위치 감지

### 2. 처리 순서
1. Soft hyphen 제거 및 단어 연결
2. Continuation 줄을 이전 줄에 병합
3. 합쳐진 genera를 각각 분리 (반복적으로 수행)
4. 빈 줄/깨진 줄 제거

### 3. 결과
- **원본**: 5,095줄
- **수정 후**: 5,105줄 (분리로 인한 증가)

## 생성된 파일

| 파일 | 설명 |
|------|------|
| `trilobite_genus_list_original.txt` | 원본 백업 |
| `trilobite_genus_list_structure_fixed.txt` | Phase 1 완료 버전 |
| `trilobite_genus_list.txt` | 최신 버전 (= structure_fixed) |
| `scripts/normalize_lines.py` | 정규화 스크립트 |
| `devlog/20260204_genus_list_changes_summary.txt` | 전체 변경사항 (soft hyphen 포함) |
| `devlog/20260204_genus_list_structural_changes.txt` | 구조적 변경사항만 |
| `devlog/20260204_genus_list_normalize_lines.diff` | git diff 전체 |

## 남은 문제

1. **불완전한 엔트리**: `Actinopeltis HAWLE & CORDA, 1847 [carolialexandri] Kral` - 원본 PDF 확인 필요

2. **깨진 저자명** (Phase 2에서 처리 예정):
   - `.NAJDR` → `ŠNAJDR`
   - `PIBYL` → `PŘIBYL`
   - `VAN˛K` → `VANĚK`

3. **오타** (Phase 2에서 처리 예정):
   - `Glabrella,` - 쉼표 오류
   - `.najdria` - 깨진 문자

## Git Commit

```
a70c477 fix: normalize line breaks (one genus per line)
```

## 다음 단계

Phase 2: 깨진 문자 및 오타 수정
- 체코어 저자명 복원 (ŠNAJDR, PŘIBYL, VANĚK)
- 기타 깨진 문자 수정
- 오타 수정
