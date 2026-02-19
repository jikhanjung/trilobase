# Phase 17: Local Overlay (사용자 주석) 구현 계획

**날짜:** 2026-02-07

## 배경

SCODA의 핵심 원칙: **canonical 데이터는 불변, 사용자 의견은 별도 레이어**. 분류학에서 의견 차이는 정상이므로 사용자가 genus/family 등에 메모, 대안적 해석, 링크를 추가할 수 있되 원본 데이터를 수정하지 않는 구조가 필요.

Phase 13-16에서 DB 내부 메타데이터 + 릴리스 메커니즘을 갖추었으므로, 마지막으로 사용자 주석 레이어를 추가하여 SCODA 구현을 완성한다.

## 구현 단계

### 1. 마이그레이션 스크립트: `scripts/add_user_annotations.py` (신규)

기존 마이그레이션 패턴(`scripts/add_scoda_tables.py`) 따름.

```sql
CREATE TABLE IF NOT EXISTS user_annotations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL,      -- 'genus', 'family', 'order' 등
    entity_id INTEGER NOT NULL,     -- 대상 레코드 ID
    annotation_type TEXT NOT NULL,  -- 'note', 'correction', 'alternative', 'link'
    content TEXT NOT NULL,
    author TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_annotations_entity
    ON user_annotations(entity_type, entity_id);
```

+ `schema_descriptions`에 `user_annotations` 테이블/컬럼 설명 삽입 (7건)

### 2. `app.py` 수정 — API 3개 추가 (기존 라우트 뒤, `app.py:449` 부근)

#### `GET /api/annotations/<entity_type>/<int:entity_id>`
- 해당 엔티티의 주석 목록 반환 (JSON 배열)
- `ORDER BY created_at DESC`

#### `POST /api/annotations`
- JSON body: `{entity_type, entity_id, annotation_type, content, author}`
- `entity_type` 허용값 검증: `genus`, `family`, `order`, `suborder`, `superfamily`, `class`
- `annotation_type` 허용값 검증: `note`, `correction`, `alternative`, `link`
- `content` 필수 검증
- 성공 시 201 + 생성된 annotation 반환

#### `DELETE /api/annotations/<int:annotation_id>`
- 해당 ID의 주석 삭제
- 없으면 404

### 3. `static/js/app.js` 수정 — My Notes UI

`showGenusDetail()` 함수 (`app.js:469-594`) 수정:
- Raw Entry 섹션 뒤에 **"My Notes"** 섹션 추가
- `GET /api/annotations/genus/{id}` 로 주석 목록 로드
- 배경색 `#fffde7` (연한 노란색)으로 canonical 데이터와 시각적 구분
- 각 주석에 삭제 버튼
- 새 주석 작성 폼: annotation_type 드롭다운 + textarea + 작성자 input + 추가 버튼
- 추가/삭제 시 목록 새로고침

`showRankDetail()` 함수에도 동일 패턴 적용 (entity_type = rank 값의 소문자).

신규 헬퍼 함수:
- `loadAnnotations(entityType, entityId)` → 주석 로드 + HTML 렌더
- `addAnnotation(entityType, entityId)` → POST 후 새로고침
- `deleteAnnotation(annotationId, entityType, entityId)` → DELETE 후 새로고침

### 4. `static/css/style.css` 수정

```css
.annotation-section { background: #fffde7; border-radius: 8px; padding: 12px; margin-top: 8px; }
.annotation-item { border-bottom: 1px solid #f0e68c; padding: 8px 0; }
.annotation-form textarea { width: 100%; }
```

### 5. `test_app.py` 수정 — TestAnnotations 클래스 (~10개 테스트)

`test_db` fixture에 `user_annotations` 테이블 CREATE 추가.

| 테스트 | 검증 내용 |
|--------|----------|
| `test_get_annotations_empty` | 주석 없는 엔티티 → 빈 배열 |
| `test_create_annotation` | POST → 201, 생성된 annotation 반환 |
| `test_create_annotation_missing_content` | content 누락 → 400 |
| `test_create_annotation_invalid_type` | 잘못된 annotation_type → 400 |
| `test_create_annotation_invalid_entity` | 잘못된 entity_type → 400 |
| `test_get_annotations_after_create` | 생성 후 GET → 1건 |
| `test_delete_annotation` | DELETE → 200 |
| `test_delete_annotation_not_found` | 없는 ID → 404 |
| `test_annotations_ordered_by_date` | 최신순 정렬 |
| `test_annotation_response_structure` | 응답에 필수 키 포함 |

### 6. `scripts/release.py` 수정 — annotations 통계 추가

`get_statistics()` 함수에 추가:
```python
cursor.execute("SELECT COUNT(*) as count FROM user_annotations")
stats['annotations'] = cursor.fetchone()['count']
```

### 7. 문서 (코드 커밋 전 작성)

1. `devlog/20260207_016_phase17_local_overlay.md` — 완료 기록
2. `docs/HANDOVER.md` 갱신

## 수정 파일 요약

| 파일 | 변경 | 신규/수정 |
|------|------|----------|
| `scripts/add_user_annotations.py` | 마이그레이션 스크립트 | 신규 |
| `app.py` | 3개 API 엔드포인트 (GET/POST/DELETE) | 수정 |
| `static/js/app.js` | My Notes 섹션 + CRUD 헬퍼 함수 | 수정 |
| `static/css/style.css` | annotation 스타일 | 수정 |
| `test_app.py` | TestAnnotations (~10개 테스트) | 수정 |
| `scripts/release.py` | annotations 통계 추가 | 수정 |

## 검증 방법

1. `python scripts/add_user_annotations.py` — 마이그레이션
2. `python -m pytest test_app.py` — 91개 기존 + ~10개 신규 = ~101개 통과
3. 웹 UI: genus detail → My Notes 섹션 확인 (추가/삭제)
4. `python scripts/release.py --dry-run` — annotations 통계 포함 확인
