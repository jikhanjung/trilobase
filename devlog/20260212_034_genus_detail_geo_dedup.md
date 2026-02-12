# 034. Genus Detail Geographic Information 중복 제거

**날짜**: 2026-02-12
**파일**: `static/js/app.js`

## 작업 내용

Genus detail 모달의 Geographic Information 섹션에서 raw 필드와 relation 테이블 데이터가 중복 표시되던 문제를 수정.

### Before (4행 중복)
```
Geographic Information
  Formation:  Kunda Stage          ← raw 필드 (plain text)
  Location:   Tallinn, Estonia     ← raw 필드 (plain text)
  Countries:  Estonia (Tallinn)    ← relation 테이블 (클릭 링크)
  Formations: Kunda Stage (MORD)   ← relation 테이블 (클릭 링크)
```

### After (최대 2행, 중복 없음)
```
Geographic Information
  Country:    Estonia (Tallinn)    ← relation 링크 우선
  Formation:  Kunda Stage (MORD)   ← relation 링크 우선
```

## 로직

1. `g.locations` 있으면 → "Country:" 행에 클릭 링크 (region 포함)
2. `g.locations` 없고 `g.location` 있으면 → "Location:" 행에 plain text 폴백
3. `g.formations` 있으면 → "Formation:" 행에 클릭 링크 (period 포함)
4. `g.formations` 없고 `g.formation` 있으면 → "Formation:" 행에 plain text 폴백
5. 둘 다 없으면 → Geographic Information 섹션 자체 숨김

## 테스트

- 기존 111개 테스트 전체 통과
