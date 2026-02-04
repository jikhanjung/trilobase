# Trilobase 프로젝트 Handover

**마지막 업데이트:** 2026-02-04

## 프로젝트 개요

삼엽충(trilobite) 분류학 데이터베이스 구축 프로젝트. Jell & Adrain (2002) PDF에서 추출한 genus 목록을 정제하여 데이터베이스화하는 것이 목표.

## 현재 상태

### 완료된 작업
- **Phase 1 완료**: 줄 정리 (한 genus = 한 줄)
  - Soft hyphen 제거 (1,357건)
  - 합쳐진 genera 분리 (56건)
  - Continuation 병합 (106건)
  - 빈 줄/깨진 줄 삭제 (16건)

- **Phase 2 완료**: 깨진 문자 및 오타 수정 (총 404건)
  - 체코어 저자명 복원: ŠNAJDR(85), PŘIBYL(145), VANĚK(118), RŮŽIČKA(12), KLOUČEK(9)
  - 체코어 지명 복원: Šárka Fm(27), Třenice(4)
  - Genus 이름 수정: Šnajdria(1)
  - 오타 수정: Glabrella, Natalina, Strenuella 쉼표 제거(3)

### 파일 구조
```
trilobase/
├── trilobite_genus_list.txt          # 최신 버전 (항상 이 파일 수정)
├── trilobite_genus_list_original.txt # 원본 백업
├── trilobite_genus_list_structure_fixed.txt  # Phase 1 완료 시점
├── trilobite_family_list.txt         # Family 목록 (미처리)
├── trilobite_nomina_nuda.txt         # Nomina nuda (미처리)
├── Jell_and_Adrain_2002_Literature_Cited.txt  # 참고문헌
├── scripts/
│   └── normalize_lines.py            # 줄 정규화 스크립트
├── devlog/
│   ├── 20260204_P01_data_cleaning_plan.md    # 전체 계획
│   ├── 20260204_001_phase1_line_normalization.md  # Phase 1 작업 기록
│   ├── 20260204_002_phase2_character_fixes.md    # Phase 2 작업 기록
│   ├── 20260204_genus_list_changes_summary.txt
│   ├── 20260204_genus_list_structural_changes.txt
│   └── 20260204_genus_list_normalize_lines.diff
└── CLAUDE.md
```

## 다음 작업 (Phase 3: 데이터 검증)

### 검증 항목
1. **형식 일관성 검사**
   - 각 줄이 `GENUS AUTHOR, YEAR [type]...` 형식인지 확인
   - 대괄호/괄호 짝 맞춤 검사
   - 세미콜론 구분자 검사

2. **데이터 무결성 검사**
   - 연도 범위 확인 (1700-2002)
   - 시대 코드 유효성 (LCAM, MCAM, UCAM 등)
   - Family 이름 유효성

3. **중복 검사**
   - 동일 genus 중복 여부

### 미해결 항목 (원본 PDF 확인 필요)
- `Actinopeltis HAWLE & CORDA, 1847 [carolialexandri] Kral` - 엔트리 잘림

### 추가 검토 필요
- `NOVAK` (19건): 체코어 `NOVÁK`로 수정 여부 검토

## 전체 계획 (devlog/20260204_P01_data_cleaning_plan.md 참조)

1. ~~Phase 1: 줄 정리~~ ✅
2. ~~Phase 2: 깨진 문자 및 오타 수정~~ ✅
3. Phase 3: 데이터 검증
4. Phase 4: DB 스키마 설계 및 데이터 임포트
5. Phase 5: 정규화 (Formation, Location, Temporal Range, Synonym)
6. Phase 6: 상위 분류군 통합 (Family, Order)

## DB 스키마 (계획)

```
taxa
├── id, name, rank, parent_id, is_valid
├── author, year, type_specimen
├── formation_id, location
├── temporal_range_start, temporal_range_end
├── notes, created_at, updated_at

synonyms
├── id, junior_id, senior_id
├── type (subjective, objective, replacement, preoccupied, suppressed, nomen_oblitum)
├── fide_author, fide_year, notes

formations
├── id, name, normalized_name, country, region

temporal_ranges
├── id, code, name, start_mya, end_mya
```

## 주의사항

- `trilobite_genus_list.txt`가 항상 최신 버전
- 각 Phase 완료 시 반드시 git commit
- 중간 과정 파일은 `_원본명_단계명.txt` 형식으로 보존
- 원본 PDF 필요 시: Jell & Adrain (2002)
