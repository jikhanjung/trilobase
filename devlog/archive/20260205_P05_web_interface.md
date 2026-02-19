# Phase 11: Web Interface 계획

**날짜:** 2026-02-05

## 목표

삼엽충 분류 데이터베이스를 탐색할 수 있는 웹 인터페이스 구현

## 요구사항

### 화면 구성

```
+------------------+--------------------------------+
|                  |                                |
|   Tree View      |    Genus List (Family)         |
|   (Taxonomy)     |                                |
|                  |    - Name | Author | Year      |
|   ▼ Trilobita    |    - Name | Author | Year      |
|     ▼ Redlichiida|    - Name | Author | Year      |
|       ▼ Olenellina                               |
|         ▼ Olenelloidea                           |
|           ▼ Olenellidae                          |
|                  |                                |
+------------------+--------------------------------+
```

### 기능

1. **왼쪽 패널: Tree View**
   - Class → Order → Suborder → Superfamily → Family 계층 구조
   - Explorer 스타일 접기/펼치기
   - Family 클릭 시 오른쪽 패널에 Genus 목록 표시

2. **오른쪽 패널: Genus List**
   - 선택된 Family의 Genus 간략 목록
   - 컬럼: Name, Author, Year, Type Species, Location
   - Genus 클릭 시 상세정보 모달

3. **상세정보 모달**
   - Genus의 모든 정보 표시
   - Synonyms, Formations, Locations 관계 포함

## 기술 스택

- **Backend**: Python + Flask
- **Frontend**: HTML, CSS, JavaScript (Vanilla)
- **Database**: SQLite (trilobase.db)
- **UI**: Bootstrap 5 (CDN)

## 파일 구조

```
trilobase/
├── app.py                    # Flask 앱
├── templates/
│   └── index.html           # 메인 페이지
├── static/
│   ├── css/
│   │   └── style.css        # 커스텀 스타일
│   └── js/
│       └── app.js           # 프론트엔드 로직
└── trilobase.db
```

## API 엔드포인트

```
GET /api/tree
    - 전체 taxonomy hierarchy 반환 (Class~Family)

GET /api/family/<family_id>/genera
    - 특정 Family의 Genus 목록 반환

GET /api/genus/<genus_id>
    - Genus 상세정보 (synonyms, formations, locations 포함)
```

## 작업 순서

1. [ ] Flask 설치
2. [ ] app.py 생성 (기본 라우팅)
3. [ ] API 엔드포인트 구현
4. [ ] templates/index.html 생성
5. [ ] static/js/app.js 구현 (tree view, list, modal)
6. [ ] static/css/style.css 스타일링
7. [ ] 테스트
8. [ ] 커밋

## 데이터 구조

### Tree API Response
```json
{
  "id": 1,
  "name": "Trilobita",
  "rank": "Class",
  "children": [
    {
      "id": 2,
      "name": "Eodiscida",
      "rank": "Order",
      "children": [...]
    }
  ]
}
```

### Genus List API Response
```json
{
  "family": {"id": 12, "name": "Olenellidae"},
  "genera": [
    {"id": 226, "name": "Genus1", "author": "Author", "year": 1900, "is_valid": 1},
    ...
  ]
}
```

### Genus Detail API Response
```json
{
  "id": 226,
  "name": "Abadiella",
  "author": "HUPE",
  "year": 1953,
  "type_species": "...",
  "formation": "...",
  "location": "...",
  "synonyms": [...],
  "formations": [...],
  "locations": [...]
}
```
