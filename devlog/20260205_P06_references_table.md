# Phase 12: References 테이블 구축 계획

**날짜:** 2026-02-05

## 개요

Jell & Adrain (2002)의 Literature Cited 섹션을 파싱하여 references 테이블을 생성한다.

## 원본 파일 분석

**파일:** `Jell_and_Adrain_2002_Literature_Cited.txt`
- 약 2,292줄
- 예상 참고문헌 수: 1,500~2,000개

### 데이터 형식

#### 1. 표준 형식 (저널 논문)
```
AUTHOR, I.N. YEAR. Title. Journal volume: pages.
```

#### 2. 다중 저자
```
AUTHOR1, I. & AUTHOR2, I. YEAR. Title...
AUTHOR1, I., AUTHOR2, I. & AUTHOR3, I. YEAR. Title...
```

#### 3. 같은 저자 연속 (저자 생략)
```
ADRAIN, J.M. 1994. The lichid trilobite...
1997. Proetid trilobites from...
1998. Systematics of the Acanthoparyphinae...
```

#### 4. 책/단행본
```
AUTHOR. YEAR. Title. (Publisher: City). pages, plates.
```

#### 5. 편집서 챕터
```
AUTHOR. YEAR. Title. Pp. X-Y. In EDITOR (ed.) Book Title...
```

#### 6. 번역 제목 (중국어/러시아어)
```
[Title in Chinese]. Acta Palaeontologica Sinica...
```

#### 7. 교차 참조
```
ANCIGINand ANCYGIN see ANTSYGIN.
```

### 특이사항
- 빈 줄로 구분된 항목
- 연도 suffix (1967a, 1967b)
- 실제 출판연도 표기: `(for 1977)`
- 페이지/도판 정보: `136p, 21pls`

## 데이터베이스 스키마

```sql
CREATE TABLE references (
    id INTEGER PRIMARY KEY,
    authors TEXT NOT NULL,           -- 저자 (원본 형식)
    year INTEGER,                    -- 출판 연도
    year_suffix TEXT,                -- a, b 등 (1967a → 'a')
    title TEXT,                      -- 제목
    journal TEXT,                    -- 저널명
    volume TEXT,                     -- 권호
    pages TEXT,                      -- 페이지
    publisher TEXT,                  -- 출판사 (책)
    city TEXT,                       -- 출판 도시
    editors TEXT,                    -- 편집자 (챕터)
    book_title TEXT,                 -- 책 제목 (챕터)
    reference_type TEXT,             -- 'article', 'book', 'chapter', 'cross_ref'
    raw_entry TEXT NOT NULL,         -- 원본 텍스트
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 검색용 인덱스
CREATE INDEX idx_references_authors ON references(authors);
CREATE INDEX idx_references_year ON references(year);
```

## 구현 단계

### Step 1: 줄 병합
- 연속된 줄을 하나의 참고문헌 항목으로 병합
- 구분 기준:
  - 빈 줄
  - 대문자로 시작하는 새 저자명
  - 4자리 숫자(연도)로 시작하는 줄 (같은 저자 연속)

### Step 2: 저자 연속 처리
- 연도만으로 시작하는 항목에 이전 저자 정보 복사
- 예: `1997. Proetid...` → `ADRAIN, J.M. 1997. Proetid...`

### Step 3: 필드 파싱
정규식 패턴:
```python
# 저자 + 연도
r'^([A-Z][A-Za-z\s,\.&]+)\s+(\d{4})([a-z])?\.?\s*(.+)$'

# 저널 논문
r'^(.+?)\.\s+([A-Z][^:]+)\s+(\d+):\s*(\d+[-–]\d+)'

# 책
r'\(([^:]+):\s*([^)]+)\)\.\s*(\d+p)'

# 편집서 챕터
r'Pp?\.\s*(\d+[-–]\d+)\.\s*In\s+([^(]+)\(ed[s]?\.\)'
```

### Step 4: 타입 분류
- `article`: 저널 논문 (volume:pages 패턴)
- `book`: 단행본 (Publisher: City 패턴)
- `chapter`: 편집서 챕터 (In EDITOR (ed.) 패턴)
- `cross_ref`: 교차 참조 (see 패턴)

### Step 5: 데이터 검증
- 연도 범위 확인 (1700~2002)
- 필수 필드 확인 (authors, raw_entry)
- 중복 확인

## 파일 구조

```
scripts/
└── parse_references.py    # 파싱 스크립트
```

## 예상 결과

| 항목 | 예상 값 |
|------|---------|
| 총 레코드 | 1,500~2,000 |
| article | ~70% |
| book | ~15% |
| chapter | ~10% |
| cross_ref | ~5% |

## 향후 확장 (선택)

1. **저자 정규화 테이블**
   - authors 테이블 분리
   - reference_authors 관계 테이블

2. **Taxa 연결**
   - genus와 reference 연결
   - fide 정보와 매칭

## 주의사항

- 원본 텍스트(raw_entry)는 항상 보존
- 파싱 실패 시에도 raw_entry로 레코드 생성
- 수동 검토 필요한 항목 표시
