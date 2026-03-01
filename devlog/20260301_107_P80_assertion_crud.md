# 107: P80 Assertion DB CRUD 적용

**Date**: 2026-03-01

## Summary

scoda-engine의 manifest-driven CRUD 프레임워크를 trilobase assertion DB에 적용했다. Taxon, assertion, reference, classification_profile에 대한 편집 스키마를 manifest에 선언하고, admin 모드에서 웹 UI를 통해 CRUD가 가능하다.

## Changes

### `scripts/create_assertion_db.py`
- `_build_manifest()`에 `editable_entities` 섹션 추가:
  - **taxon**: CRUD, 13개 필드
  - **assertion**: CRUD, subject_taxon_id `readonly_on_edit`, predicate enum, FK (taxon, reference), edge cache 재빌드 훅
  - **reference**: CRU (삭제 불가), 13개 필드
  - **classification_profile**: CRUD
- Taxon detail linked_table에 `entity_type`, `entity_id_key`, `entity_defaults` 추가 → 인라인 assertion CRUD
- `taxon_assertions` 쿼리: `a.id` → `a.id as assertion_id` (taxon id와 충돌 방지)
- Linked_table에서 Accepted 컬럼 제거
- JA2002 reference: id=0 → auto_increment id (2132)로 변경

### `tests/test_trilobase.py`
- `TestAssertionDBEditableEntities` 클래스 추가 (6개 테스트):
  - editable_entities 존재 확인
  - taxon/assertion/reference 스키마 검증
  - manifest 검증 통과
  - FK 참조 테이블 유효성

## Usage

```bash
# Admin 모드로 실행
python -m scoda_engine.serve --db-path db/trilobase-assertion-0.1.2.db --mode admin --port 8090

# 브라우저에서 http://localhost:8090 접속
# Taxon detail → assertion 인라인 편집 (추가/수정/삭제)
# Assertion 편집 시:
#   - Subject Taxon: 읽기 전용 (이름 표시)
#   - Object Taxon: FK autocomplete (PLACED_IN 시 상위 rank 필터)
#   - Reference: FK autocomplete (저자 + 연도 표시)
```

## Test Results

- trilobase: 118 passed (112 기존 + 6 신규)
