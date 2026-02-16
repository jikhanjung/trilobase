# Bibliography Detail — Related Genera 전체 표시 버그 수정

**날짜:** 2026-02-16

## 문제

Bibliography detail 모달의 "Related Genera" 섹션에 전체 genera가 표시됨.

## 원인

`add_scoda_manifest.py`의 `bibliography_detail`이 레거시 엔드포인트를 사용:

```json
"source": "/api/bibliography/{id}"
```

이 엔드포인트는 `bibliography_genera` 쿼리의 `author_name` 파라미터를 매핑하지 못함.
→ `WHERE tr.author LIKE '%%'` → 전체 genera 매칭.

## 수정

composite endpoint + sub_queries 파라미터 매핑 추가:

```json
"source": "/api/composite/bibliography_detail?id={id}",
"source_query": "bibliography_detail",
"source_param": "bibliography_id",
"sub_queries": {
    "genera": {"query": "bibliography_genera", "params": {"author_name": "result.authors"}}
}
```

bibliography의 `authors` 필드 → `author_name` 파라미터로 전달 → 관련 genera만 필터.

## 변경 파일

- `scripts/add_scoda_manifest.py`: bibliography_detail에 composite endpoint 설정 추가
- `trilobase.db`: ui_manifest 직접 UPDATE

## 테스트

- `pytest tests/ -x -q` → 231 passed
