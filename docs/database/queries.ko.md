# 쿼리 예제

Trilobase 데이터베이스 쿼리 SQL 예제 모음. 지리/층서 데이터를 포함하는 교차 데이터베이스 쿼리는 PaleoCore를 먼저 연결하세요:

```sql
ATTACH DATABASE 'db/paleocore.db' AS pc;
```

---

## 기본 쿼리

### 유효 속 목록

```sql
SELECT name, author, year
FROM taxonomic_ranks
WHERE rank = 'Genus' AND is_valid = 1
LIMIT 10;
```

### 이름 패턴으로 속 검색

```sql
SELECT name, author, year, family, is_valid
FROM taxonomic_ranks
WHERE rank = 'Genus' AND name LIKE 'Para%'
ORDER BY name;
```

### 유효/무효 속 수 집계

```sql
SELECT
    CASE WHEN is_valid = 1 THEN '유효' ELSE '무효' END AS 상태,
    COUNT(*) AS 건수
FROM taxonomic_ranks
WHERE rank = 'Genus'
GROUP BY is_valid;
```

---

## 분류 계층

### 속의 전체 계층 구조

```sql
SELECT
    g.name AS genus,
    f.name AS family,
    sf.name AS superfamily,
    o.name AS "order"
FROM taxonomic_ranks g
LEFT JOIN taxonomic_ranks f ON g.parent_id = f.id
LEFT JOIN taxonomic_ranks sf ON f.parent_id = sf.id
LEFT JOIN taxonomic_ranks o ON sf.parent_id = o.id
WHERE g.name = 'Paradoxides';
```

### 속 수 기준 과 목록

```sql
SELECT name, genera_count
FROM taxonomic_ranks
WHERE rank = 'Family'
ORDER BY genera_count DESC
LIMIT 20;
```

---

## 동의어

### 특정 속의 동의어 찾기

```sql
SELECT
    jr.name AS 이차동의어,
    s.synonym_type AS 유형,
    sr.name AS 선취동의어,
    s.fide_author,
    s.fide_year
FROM synonyms s
JOIN taxonomic_ranks jr ON s.junior_taxon_id = jr.id
LEFT JOIN taxonomic_ranks sr ON s.senior_taxon_id = sr.id
WHERE sr.name = 'Paradoxides';
```

### 동의어가 가장 많은 속

```sql
SELECT
    sr.name AS 선취명,
    COUNT(*) AS 동의어수
FROM synonyms s
JOIN taxonomic_ranks sr ON s.senior_taxon_id = sr.id
GROUP BY s.senior_taxon_id
ORDER BY 동의어수 DESC
LIMIT 10;
```

---

## 지리 쿼리

### 특정 국가의 속

```sql
SELECT g.name, g.author, g.year, gl.region
FROM taxonomic_ranks g
JOIN genus_locations gl ON g.id = gl.genus_id
JOIN pc.countries c ON gl.country_id = c.id
WHERE c.name = 'China'
ORDER BY g.name
LIMIT 20;
```

### 속이 가장 많은 국가

```sql
SELECT c.name AS 국가, COUNT(DISTINCT gl.genus_id) AS 속수
FROM genus_locations gl
JOIN pc.countries c ON gl.country_id = c.id
GROUP BY c.name
ORDER BY 속수 DESC
LIMIT 10;
```

---

## 층서 쿼리

### 특정 지층의 속

```sql
SELECT DISTINCT g.name, g.author, g.year
FROM taxonomic_ranks g
JOIN genus_formations gf ON g.id = gf.genus_id
JOIN pc.formations f ON gf.formation_id = f.id
WHERE f.name = 'Wheeler Formation'
ORDER BY g.name;
```

### 시대별 속

```sql
SELECT name, author, year, temporal_code
FROM taxonomic_ranks
WHERE rank = 'Genus' AND is_valid = 1 AND temporal_code = 'MCAM'
ORDER BY name;
```

---

## 참고문헌

### 특정 속의 참고문헌

```sql
SELECT b.authors, b.year, b.title, b.journal, tb.relationship_type
FROM taxon_bibliography tb
JOIN bibliography b ON tb.bibliography_id = b.id
JOIN taxonomic_ranks t ON tb.taxon_id = t.id
WHERE t.name = 'Paradoxides'
ORDER BY b.year;
```

---

## 시대 범위 코드

| 코드 | 의미 |
|------|------|
| LCAM / MCAM / UCAM | 하부 / 중부 / 상부 캄브리아기 |
| LORD / MORD / UORD | 하부 / 중부 / 상부 오르도비스기 |
| LSIL / USIL | 하부 / 상부 실루리아기 |
| LDEV / MDEV / UDEV | 하부 / 중부 / 상부 데본기 |
| MISS / PENN | 미시시피기 / 펜실베이니아기 |
| LPERM / PERM / UPERM | 하부 / 중부 / 상부 페름기 |
