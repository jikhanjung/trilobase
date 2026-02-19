# Phase 6: Family Normalization

**날짜:** 2026-02-04

## 작업 내용

Family 데이터 정리 및 정규화 작업 완료.

### 1. Family 파일 분석

`trilobite_family_list.txt` 파일 구조:
- 369줄 (완전한 형식 179줄 + 이름만 있는 줄 185줄 + 기타)
- 형식: `FamilyName AUTHOR, YEAR genera_list.`

### 2. 발견된 문제점

1. **Soft hyphen 잔재**: `\u00ad` 문자 남아 있음
2. **제어 문자**: `0x02` (STX) 등 PDF 추출 과정에서 발생한 제어 문자
3. **한 줄에 여러 Family**: 일부 줄에 2개 이상 Family가 붙어 있음
4. **연도 오타**: "184" (HAWLE & CORDA - 1847이어야 함)
5. **Family 오타**: DORYPGIDAE → DORYPYGIDAE, CHENGKOUASPIDIDAE → CHENGKOUASPIDAE

### 3. 해결 방법

- `scripts/normalize_families.py` 스크립트 작성
- 제어 문자 제거 (STX, soft hyphen 등)
- 한 줄에 여러 Family 파싱 지원
- 연도 패턴 3-4자리 허용
- Taxa 테이블 오타 자동 수정

### 4. 결과

| 항목 | 값 |
|------|-----|
| 파싱된 Families | 181 |
| Genus-to-Family 매핑 | 4,819 |
| Taxa 연결됨 | 4,660/4,771 (97.7%) |

미연결 Taxa:
- 342: Family 정보 없음 (원본 데이터에 없음)
- 74: UNCERTAIN
- 29: INDET
- 8: NEKTASPIDA

### 5. 생성된 테이블

```sql
CREATE TABLE families (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    name_normalized TEXT,
    author TEXT,
    year TEXT,
    genera_count INTEGER DEFAULT 0,
    taxa_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 6. Top 10 Families by Taxa Count

| Family | Author | Year | Taxa |
|--------|--------|------|------|
| Proetidae | SALTER | 1864 | 346 |
| Asaphidae | BURMEISTER | 1843 | 185 |
| Ptychopariidae | MATTHEW | 1887 | 183 |
| Styginidae | VOGDES | 1890 | 115 |
| Solenopleuridae | ANGELIN | 1854 | 102 |
| Cheiruridae | SALTER | 1864 | 101 |
| Olenidae | BURMEISTER | 1843 | 86 |
| Ellipsocephalidae | MATTHEW | 1887 | 83 |
| Proasaphiscidae | W.ZHANG | 1963 | 80 |
| Remopleurididae | HAWLE & CORDA | 184* | 77 |

*연도 불완전 (1847이어야 함)

## 다음 작업

- Order 데이터 추가: Family → Order 계층 구조
- genera 테이블 생성 고려
