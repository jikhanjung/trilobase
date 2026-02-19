# UI 필터 및 네비게이션 개선

**날짜:** 2026-02-05

## 작업 내용

### 1. Genus 목록 유효성 필터

Family 선택 시 유효한 genus만 표시하거나 모두 표시할 수 있는 체크박스 추가.

**기능:**
- "Valid only" 체크박스 (기본값: 체크됨)
- 체크 시: 유효한 genus만 표시
- 해제 시: 모든 genus 표시 (무효 taxa는 기울임체)
- 현재 표시 상태 통계 표시

**예시:**
```
Showing 150 valid genera (35 invalid hidden)
Showing all 185 genera (150 valid, 35 invalid)
```

### 2. 트리뷰 Expand/Collapse All

트리 패널 헤더에 전체 펼치기/접기 버튼 추가.

**버튼:**
- ⇕ (Expand All) - 모든 노드 펼치기
- ⇳ (Collapse All) - 모든 노드 접기

### 3. Synonymy 링크

Genus 상세정보의 Synonymy 섹션에서 senior taxon으로 이동할 수 있는 링크 추가.

**기능:**
- Senior taxon 이름 클릭 시 해당 taxon의 상세정보 모달로 이동
- senior_taxon_id가 NULL인 경우 (4건) 텍스트만 표시

## 수정된 파일

- `templates/index.html` - Expand/Collapse 버튼 추가
- `static/js/app.js`
  - 필터 상태 관리 (showOnlyValid, currentGenera)
  - toggleValidFilter(), renderGeneraTable() 함수 추가
  - expandAll(), collapseAll() 함수 추가
  - Synonymy 링크 렌더링
- `static/css/style.css`
  - genera-stats 스타일
  - 버튼 그룹 스타일
  - synonym-link 스타일
- `app.py` - synonyms API에 senior_taxon_id 추가

## 코드 변경 요약

**app.py:**
```python
'synonyms': [{
    'id': s['id'],
    'senior_taxon_id': s['senior_taxon_id'],  # 추가
    'senior_name': s['senior_name'] or s['senior_taxon_name'],
    ...
}]
```

**app.js:**
```javascript
// 필터 상태
let currentGenera = [];
let showOnlyValid = true;

// 필터링된 테이블 렌더링
function renderGeneraTable() { ... }

// 트리 전체 펼치기/접기
function expandAll() { ... }
function collapseAll() { ... }
```
