# Fix Sticky Table Header (UI Bug Fix)

**Date:** 2026-02-09
**Branch:** `feature/scoda-implementation`
**Type:** Bug Fix

## Issue

오른쪽 Genus 목록의 테이블 헤더에서 문제 발견:

1. **반투명 효과**: 헤더 뒤로 데이터 행이 비쳐 보임
2. **상단 여백**: 헤더가 컨테이너 상단에 딱 붙지 않고 공간이 있음
3. **구분 불명확**: 헤더가 떠있다는 시각적 표시 부족

## Changes

### 1. Table Header z-index & Box Shadow 추가

**File:** `static/css/style.css`

```css
/* Genus Table */
.genus-table th {
    position: sticky;
    top: 0;
    background-color: #fff;        /* 명시적으로 불투명 배경 */
    z-index: 10;                   /* 다른 요소 위에 표시 */
    box-shadow: 0 2px 4px rgba(0,0,0,0.05);  /* 그림자 효과 */
    /* ... 기타 속성 ... */
}

/* Manifest Table */
.manifest-table th {
    position: sticky;
    top: 0;
    background-color: #fff;
    z-index: 10;
    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    /* ... 기타 속성 ... */
}
```

### 2. List Container Padding 조정

```css
.list-container {
    flex: 1;
    overflow-y: auto;
    padding: 0 15px 15px 15px;  /* 상단 padding 제거 */
}
```

**변경 전:** `padding: 15px;` (모든 방향 15px)
**변경 후:** `padding: 0 15px 15px 15px;` (상단만 0)

## Results

✅ **헤더 불투명도**: 뒤의 데이터가 완전히 가려짐
✅ **상단 고정**: 헤더가 컨테이너 최상단에 딱 붙음
✅ **시각적 구분**: 그림자 효과로 헤더가 떠있다는 느낌 강조
✅ **스크롤 동작**: sticky 위치가 정확히 작동

## Testing

- [x] Genus 목록 스크롤 시 헤더 고정 확인
- [x] Table View (manifest-driven) 헤더 동작 확인
- [x] 브라우저 새로고침 시 CSS 적용 확인

## Files Modified

- `static/css/style.css`
  - `.genus-table th`: z-index, box-shadow 추가
  - `.manifest-table th`: z-index, box-shadow 추가
  - `.list-container`: padding-top 제거

## Notes

- 같은 이슈가 `.manifest-table th`에도 있을 수 있어 동일하게 처리
- `position: sticky`는 유지하되 z-index로 레이어링 제어
- `background: #fff;` → `background-color: #fff;`로 명시적 변경
