# Phase 10: Formation/Location Relation 테이블 완료

**날짜:** 2026-02-05

## 목표

`formation`, `location` 필드를 synonym처럼 별도의 relation 테이블로 분리하여 다대다 관계 지원

## 작업 수행 내역

### Step 1: 데이터베이스 백업
```bash
cp trilobase.db trilobase_backup_phase10.db
```

### Step 2: Relation 테이블 생성

```sql
CREATE TABLE genus_formations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    genus_id INTEGER NOT NULL,
    formation_id INTEGER NOT NULL,
    is_type_locality INTEGER DEFAULT 0,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (genus_id) REFERENCES taxonomic_ranks(id),
    FOREIGN KEY (formation_id) REFERENCES formations(id),
    UNIQUE(genus_id, formation_id)
);

CREATE TABLE genus_locations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    genus_id INTEGER NOT NULL,
    country_id INTEGER NOT NULL,
    region TEXT,
    is_type_locality INTEGER DEFAULT 0,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (genus_id) REFERENCES taxonomic_ranks(id),
    FOREIGN KEY (country_id) REFERENCES countries(id),
    UNIQUE(genus_id, country_id, region)
);
```

### Step 3: 기존 데이터 마이그레이션

```sql
-- genus_formations
INSERT INTO genus_formations (genus_id, formation_id)
SELECT tr.id, tr.formation_id
FROM taxonomic_ranks tr
WHERE tr.rank = 'Genus' AND tr.formation_id IS NOT NULL;

-- genus_locations (region 파싱 포함)
INSERT INTO genus_locations (genus_id, country_id, region)
SELECT tr.id, tr.country_id,
       CASE
           WHEN INSTR(tr.location, ',') > 0
           THEN TRIM(SUBSTR(tr.location, 1, INSTR(tr.location, ',') - 1))
           ELSE NULL
       END as region
FROM taxonomic_ranks tr
WHERE tr.rank = 'Genus' AND tr.country_id IS NOT NULL;
```

### Step 4: 인덱스 생성

```sql
CREATE INDEX idx_genus_formations_genus ON genus_formations(genus_id);
CREATE INDEX idx_genus_formations_formation ON genus_formations(formation_id);
CREATE INDEX idx_genus_locations_genus ON genus_locations(genus_id);
CREATE INDEX idx_genus_locations_country ON genus_locations(country_id);
```

### Step 5: 검증

- genus_formations: 4,854건 ✓
- genus_locations: 4,841건 ✓
- 참조 무결성 오류: 0건 ✓

## 결과

### 새로 생성된 테이블

| 테이블 | 레코드 수 | 설명 |
|--------|----------|------|
| genus_formations | 4,854 | Genus-Formation 다대다 관계 |
| genus_locations | 4,841 | Genus-Country 다대다 관계 |

### 데이터 보존

- `taxonomic_ranks.formation` - 원본 텍스트 유지
- `taxonomic_ranks.location` - 원본 텍스트 유지
- `taxonomic_ranks.formation_id` - 기존 참조 유지
- `taxonomic_ranks.country_id` - 기존 참조 유지

### 최종 테이블 목록

| 테이블/뷰 | 레코드 수 | 설명 |
|-----------|----------|------|
| taxonomic_ranks | 5,338 | 통합 분류 체계 (Class~Genus) |
| synonyms | 1,055 | 동의어 관계 |
| genus_formations | 4,854 | Genus-Formation 관계 |
| genus_locations | 4,841 | Genus-Country 관계 |
| formations | 2,009 | 지층 정보 |
| countries | 151 | 국가 정보 |
| temporal_ranges | 28 | 지질시대 코드 |
| taxa (뷰) | 5,113 | 하위 호환성 뷰 |

## 샘플 쿼리

### 특정 Genus의 모든 Formation 조회
```sql
SELECT g.name as genus, f.name as formation
FROM taxonomic_ranks g
JOIN genus_formations gf ON g.id = gf.genus_id
JOIN formations f ON gf.formation_id = f.id
WHERE g.name = 'Paradoxides';
```

### 특정 Formation의 모든 Genus 조회
```sql
SELECT g.name as genus, g.author, g.year
FROM taxonomic_ranks g
JOIN genus_formations gf ON g.id = gf.genus_id
JOIN formations f ON gf.formation_id = f.id
WHERE f.name LIKE '%Burgess%';
```

### 특정 국가의 모든 Genus 조회
```sql
SELECT g.name as genus, gl.region
FROM taxonomic_ranks g
JOIN genus_locations gl ON g.id = gl.genus_id
JOIN countries c ON gl.country_id = c.id
WHERE c.name = 'China';
```

## 백업 파일

- `trilobase_backup_phase10.db` - 작업 전 백업 (롤백용)
