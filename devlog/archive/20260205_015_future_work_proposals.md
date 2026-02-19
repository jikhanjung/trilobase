# 향후 작업 제안사항

**날짜:** 2026-02-05

## 현재 상태

Phase 1~12 완료:
- 데이터 정제 및 정규화
- 계층적 분류 체계 구축 (Class~Genus)
- 웹 인터페이스 (트리뷰, 목록, 상세정보)
- Bibliography 테이블 (2,130건)

---

## 제안 1: 데이터 연결

### 1.1 Bibliography ↔ Taxa 연결

**목적:** Genus의 원기재 논문 및 참고문헌 연결

**방법:**
- Genus의 author/year를 bibliography와 매칭
- `genus_bibliography` 관계 테이블 생성
- fide 정보 (synonyms 테이블)와 bibliography 연결

**예상 스키마:**
```sql
CREATE TABLE genus_bibliography (
    id INTEGER PRIMARY KEY,
    genus_id INTEGER REFERENCES taxonomic_ranks(id),
    bibliography_id INTEGER REFERENCES bibliography(id),
    relation_type TEXT,  -- 'original', 'revision', 'fide'
    notes TEXT
);
```

**난이도:** 중 (저자명 변형 매칭 필요)

### 1.2 Temporal Code 정규화

**목적:** 지질시대 코드를 정규화하여 시대별 검색 가능하게

**방법:**
- taxonomic_ranks.temporal_code → temporal_ranges.id 연결
- 복합 코드 처리 (예: "LCAM-MCAM")

**난이도:** 하

---

## 제안 2: 웹 인터페이스 확장

### 2.1 검색 기능

**목적:** 다양한 기준으로 taxa 검색

**기능:**
- Genus 이름 검색 (부분 일치)
- Author 검색
- Location/Country 검색
- Formation 검색
- 지질시대 검색

**UI:**
- 상단 검색바 또는 별도 검색 페이지
- 자동완성 (선택적)

**난이도:** 중

### 2.2 Bibliography 브라우저

**목적:** 참고문헌 탐색 및 검색

**기능:**
- 참고문헌 목록 페이지
- 저자별/연도별 필터
- 연결된 Genus 표시 (1.1 완료 후)

**UI:**
- 별도 페이지 또는 탭
- 페이지네이션

**난이도:** 중

### 2.3 통계 대시보드

**목적:** 데이터 시각화

**기능:**
- 시대별 Genus 분포 차트
- 지역별 분포 지도/차트
- Family별 genus 수 차트
- 유효/무효 taxa 비율

**라이브러리:** Chart.js 또는 D3.js

**난이도:** 중~상

---

## 제안 3: 데이터 품질 개선

### 3.1 Formation 정규화

**목적:** 유사/중복 formation 정리

**현황:**
- formations 테이블: 2,009건
- 중복/유사 항목 다수 예상

**방법:**
- 유사도 기반 그룹핑
- 수동 검토 및 병합
- normalized_name 필드 활용

**난이도:** 중 (수동 검토 필요)

### 3.2 Type Species 파싱 개선

**목적:** type_species 필드 구조화

**현황:**
- type_species: 원본 텍스트
- type_species_author: 부분적으로 파싱됨

**방법:**
- 종명과 저자 분리 개선
- 종명 정규화 (이명 처리)

**난이도:** 중

---

## 제안 4: 배포 및 공개

### 4.1 웹 애플리케이션 배포

**옵션:**
- Railway / Render (무료 티어)
- Heroku
- 자체 서버

**고려사항:**
- SQLite → PostgreSQL 마이그레이션 (선택적)
- 환경 변수 설정

**난이도:** 하~중

### 4.2 데이터 내보내기

**목적:** 연구자들이 데이터 활용할 수 있도록

**형식:**
- CSV export
- JSON export
- Darwin Core 형식 (선택적)

**난이도:** 하

---

## 우선순위 제안

| 순위 | 작업 | 이유 |
|------|------|------|
| 1 | 검색 기능 | 사용성 크게 향상 |
| 2 | Temporal Code 정규화 | 비교적 간단, 활용도 높음 |
| 3 | Bibliography 브라우저 | 기존 데이터 활용 |
| 4 | Bibliography ↔ Taxa 연결 | 학술적 가치 |
| 5 | 통계 대시보드 | 시각적 효과 |
| 6 | 데이터 내보내기 | 공개/공유 |

---

## 참고

이 문서는 제안사항 정리용이며, 실제 구현 시 별도 계획 문서(P##) 작성 권장.
