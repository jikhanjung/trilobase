# 035. Phase 27: Geographic Regions 계층 구조 도입

**날짜**: 2026-02-12
**상태**: 완료

## 작업 내용

`countries` 테이블의 주권국가/하위지역 혼재 문제를 해결하기 위해
계층형 `geographic_regions` 테이블을 도입하고 전체 스택을 마이그레이션.

## 새 테이블

### `geographic_regions` (자기 참조 계층)

```sql
CREATE TABLE geographic_regions (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    level TEXT NOT NULL,       -- 'country' | 'region'
    parent_id INTEGER,         -- FK → geographic_regions.id (NULL = country)
    cow_ccode INTEGER,         -- COW 코드 (country level만)
    taxa_count INTEGER DEFAULT 0
);
```

- Country: 60개 (COW 주권국가 55 + unmappable 5)
- Region: 502개 (countries 테이블 하위지역 87 + genus_locations.region 텍스트 440, 중복 제거)
- 총 562개 엔트리

### `genus_locations` 변경

- `region_id` 컬럼 추가 (FK → geographic_regions.id)
- 4,841건 전부 매핑 완료 (NULL 0건)
- 기존 `country_id`, `region` 텍스트 필드 보존 (원본 데이터 원칙)

## API 변경

### 수정된 엔드포인트

- `GET /api/genus/<id>` — locations 응답에 `country_id`, `country_name`, `region_id`, `region_name` 반환
- `GET /api/country/<id>` — `geographic_regions` level='country' 기반, `regions` 리스트 포함
- `GET /api/metadata` — countries 통계를 `geographic_regions` 기반으로 변경, `regions` 카운트 추가

### 새 엔드포인트

- `GET /api/region/<id>` — Region 상세 (부모 country 링크, genera 목록)

### Named Query 갱신

- `countries_list` — `geographic_regions WHERE level='country'` 기반으로 변경
- `regions_list` — 신규 추가 (전체 region 목록, country별 정렬)

## UI 변경

- Genus detail: Country > Region 형태로 표시, 둘 다 클릭 가능
- Country detail: Regions 섹션 추가 (하위 region 목록), COW 정보 간소화
- Region detail 모달 신규: 부모 country 링크, taxa_count, genera 목록

## DB 메타데이터

- `schema_descriptions`에 `geographic_regions` 테이블/컬럼 설명 7건 추가
- `genus_locations.region_id` 설명 추가

## 기존 테이블 보존

- `countries`: 유지 (원본 보존)
- `country_cow_mapping`: 유지
- `genus_locations.country_id`, `region`: 유지 (원본 FK/텍스트)

## 스크립트

- `scripts/create_geographic_regions.py` (465 lines) — 마이그레이션 스크립트

## 테스트

- 기존 111개 → 120개 (신규 9개: country detail 5, region detail 4)
- MCP 17개 통과
- **총 137개 전부 통과**
