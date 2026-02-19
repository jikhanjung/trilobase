# Phase 12: Bibliography 테이블 구축 완료

**날짜:** 2026-02-05

## 작업 결과

### 테이블 생성

`bibliography` 테이블 생성 (SQLite에서 `references`는 예약어라 변경)

```sql
CREATE TABLE bibliography (
    id INTEGER PRIMARY KEY,
    authors TEXT NOT NULL,
    year INTEGER,
    year_suffix TEXT,
    title TEXT,
    journal TEXT,
    volume TEXT,
    pages TEXT,
    publisher TEXT,
    city TEXT,
    editors TEXT,
    book_title TEXT,
    reference_type TEXT DEFAULT 'article',
    raw_entry TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 통계

| 항목 | 값 |
|------|-----|
| 총 레코드 | 2,130 |
| article | 1,902 (89%) |
| book | 161 (8%) |
| chapter | 52 (2%) |
| cross_ref | 15 (1%) |
| 연도 범위 | 1745 - 2003 |

### 필드 커버리지

| 필드 | 레코드 수 | 비율 |
|------|----------|------|
| year | 2,110 | 99% |
| title | 2,099 | 99% |
| journal | 1,604 | 75% |
| authors | 2,130 | 100% |
| raw_entry | 2,130 | 100% |

### 파싱 처리 사항

1. **줄 병합**: 연속된 줄을 하나의 참고문헌으로 병합
2. **저자 연속 처리**: 연도만 있는 항목에 이전 저자 복사
3. **타입 분류**:
   - article: 저널 논문 (volume:pages 패턴)
   - book: 단행본 (Publisher: City 패턴)
   - chapter: 편집서 챕터 (In EDITOR (ed.) 패턴)
   - cross_ref: 교차 참조 (see 패턴)

## 생성된 파일

- `scripts/parse_references.py` - 파싱 스크립트

## 샘플 데이터

**Article:**
```
ADRAIN, J.M. 1994
Journal: Journal of Paleontology 68: 1081-1099
Title: The lichid trilobite Borealarges n. gen...
```

**Book:**
```
APOLLONOV, M.K. 1970
Publisher: Akademiya Nauk Kazakh SSR, Alma Ata
Pages: 136p
```

## 알려진 제한사항

- 복잡한 형식의 책 항목 일부 파싱 오류
- 원본 텍스트(raw_entry)는 항상 보존되어 있음
