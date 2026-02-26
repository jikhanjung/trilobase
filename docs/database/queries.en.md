# Example Queries

SQL examples for querying the Trilobase database. For cross-database queries involving geographic or stratigraphic data, attach PaleoCore first:

```sql
ATTACH DATABASE 'db/paleocore.db' AS pc;
```

---

## Basic Queries

### List valid genera

```sql
SELECT name, author, year
FROM taxonomic_ranks
WHERE rank = 'Genus' AND is_valid = 1
LIMIT 10;
```

### Search genera by name pattern

```sql
SELECT name, author, year, family, is_valid
FROM taxonomic_ranks
WHERE rank = 'Genus' AND name LIKE 'Para%'
ORDER BY name;
```

### Count genera by validity

```sql
SELECT
    CASE WHEN is_valid = 1 THEN 'Valid' ELSE 'Invalid' END AS status,
    COUNT(*) AS count
FROM taxonomic_ranks
WHERE rank = 'Genus'
GROUP BY is_valid;
```

---

## Taxonomic Hierarchy

### Full hierarchy of a genus

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

### List families with genus counts

```sql
SELECT name, genera_count
FROM taxonomic_ranks
WHERE rank = 'Family'
ORDER BY genera_count DESC
LIMIT 20;
```

---

## Synonyms

### Find synonyms of a genus

```sql
SELECT
    jr.name AS junior_synonym,
    s.synonym_type,
    sr.name AS senior_synonym,
    s.fide_author,
    s.fide_year
FROM synonyms s
JOIN taxonomic_ranks jr ON s.junior_taxon_id = jr.id
LEFT JOIN taxonomic_ranks sr ON s.senior_taxon_id = sr.id
WHERE sr.name = 'Paradoxides';
```

### Genera with most synonyms

```sql
SELECT
    sr.name AS senior_name,
    COUNT(*) AS synonym_count
FROM synonyms s
JOIN taxonomic_ranks sr ON s.senior_taxon_id = sr.id
GROUP BY s.senior_taxon_id
ORDER BY synonym_count DESC
LIMIT 10;
```

---

## Geographic Queries

### Genera from a specific country

```sql
SELECT g.name, g.author, g.year, gl.region
FROM taxonomic_ranks g
JOIN genus_locations gl ON g.id = gl.genus_id
JOIN pc.countries c ON gl.country_id = c.id
WHERE c.name = 'China'
ORDER BY g.name
LIMIT 20;
```

### Countries with most genera

```sql
SELECT c.name AS country, COUNT(DISTINCT gl.genus_id) AS genera_count
FROM genus_locations gl
JOIN pc.countries c ON gl.country_id = c.id
GROUP BY c.name
ORDER BY genera_count DESC
LIMIT 10;
```

---

## Stratigraphic Queries

### Genera from a specific formation

```sql
SELECT DISTINCT g.name, g.author, g.year
FROM taxonomic_ranks g
JOIN genus_formations gf ON g.id = gf.genus_id
JOIN pc.formations f ON gf.formation_id = f.id
WHERE f.name = 'Wheeler Formation'
ORDER BY g.name;
```

### Genera by time period

```sql
SELECT name, author, year, temporal_code
FROM taxonomic_ranks
WHERE rank = 'Genus' AND is_valid = 1 AND temporal_code = 'MCAM'
ORDER BY name;
```

---

## Bibliography

### References for a genus

```sql
SELECT b.authors, b.year, b.title, b.journal, tb.relationship_type
FROM taxon_bibliography tb
JOIN bibliography b ON tb.bibliography_id = b.id
JOIN taxonomic_ranks t ON tb.taxon_id = t.id
WHERE t.name = 'Paradoxides'
ORDER BY b.year;
```

---

## Temporal Range Codes

| Code | Meaning |
|------|---------|
| LCAM / MCAM / UCAM | Lower / Middle / Upper Cambrian |
| LORD / MORD / UORD | Lower / Middle / Upper Ordovician |
| LSIL / USIL | Lower / Upper Silurian |
| LDEV / MDEV / UDEV | Lower / Middle / Upper Devonian |
| MISS / PENN | Mississippian / Pennsylvanian |
| LPERM / PERM / UPERM | Lower / Middle / Upper Permian |
