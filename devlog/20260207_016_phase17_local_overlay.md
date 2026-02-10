# Phase 17: Local Overlay (사용자 주석) 완료

**날짜:** 2026-02-07

## 요약

SCODA 구현의 마지막 레이어인 Local Overlay를 완성. 사용자가 canonical 데이터를 수정하지 않고 genus/family 등에 메모, 교정, 대안적 해석, 링크를 추가할 수 있는 주석 시스템 구축.

## 구현 내용

### 1. `user_annotations` 테이블
- 6개 entity_type 지원: genus, family, order, suborder, superfamily, class
- 4개 annotation_type: note, correction, alternative, link
- `schema_descriptions`에 8건 추가 (테이블 설명 + 7개 컬럼 설명)

### 2. API 엔드포인트 (3개)
| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/annotations/<entity_type>/<entity_id>` | 주석 목록 (최신순) |
| POST | `/api/annotations` | 주석 생성 (검증 포함) |
| DELETE | `/api/annotations/<annotation_id>` | 주석 삭제 |

### 3. 프론트엔드 My Notes UI
- `showGenusDetail()`: Raw Entry 섹션 뒤에 My Notes 섹션 추가
- `showRankDetail()`: Notes 섹션 뒤에 My Notes 섹션 추가
- 배경색 `#fffde7`(연한 노란색)으로 canonical 데이터와 시각적 구분
- 헬퍼 함수: `buildAnnotationSectionHTML()`, `loadAnnotations()`, `addAnnotation()`, `deleteAnnotation()`

### 4. CSS 스타일
- `.annotation-section`: 노란 배경, 둥근 모서리
- `.annotation-item`: 항목 구분선
- `.annotation-form`: 입력 폼

### 5. `scripts/release.py` 수정
- `get_statistics()`에 `user_annotations` 카운트 추가

## 수정 파일

| 파일 | 변경 | 신규/수정 |
|------|------|----------|
| `scripts/add_user_annotations.py` | 마이그레이션 스크립트 | 신규 |
| `app.py` | 3개 API 엔드포인트 + 검증 상수 | 수정 |
| `static/js/app.js` | My Notes 섹션 + 4개 헬퍼 함수 | 수정 |
| `static/css/style.css` | annotation 스타일 3개 | 수정 |
| `test_app.py` | TestAnnotations 클래스 (10개 테스트) | 수정 |
| `scripts/release.py` | annotations 통계 추가 | 수정 |

## 테스트 결과

```
101 passed (91 기존 + 10 신규)
```

신규 테스트:
- `test_get_annotations_empty` - 빈 배열 반환
- `test_create_annotation` - 생성 + 201
- `test_create_annotation_missing_content` - content 누락 → 400
- `test_create_annotation_invalid_type` - 잘못된 annotation_type → 400
- `test_create_annotation_invalid_entity` - 잘못된 entity_type → 400
- `test_get_annotations_after_create` - 생성 후 조회
- `test_delete_annotation` - 삭제 + 200
- `test_delete_annotation_not_found` - 없는 ID → 404
- `test_annotations_ordered_by_date` - 최신순 정렬
- `test_annotation_response_structure` - 응답 구조 검증

## SCODA 구현 완료 요약

Phase 13-17을 통해 SCODA(Self-Contained Data Artifact) 참조 구현 완성:

| Phase | 내용 | 핵심 원칙 |
|-------|------|----------|
| 13 | Core Metadata | Identity, Provenance, Semantics |
| 14 | Display Intent + Queries | Data carries its own UI hints |
| 15 | UI Manifest | Declarative view definitions |
| 16 | Release Mechanism | Immutability, integrity verification |
| 17 | Local Overlay | Canonical data immutable, user opinions separate |
