#!/usr/bin/env python3
"""
Geographic Regions 계층 구조 생성 스크립트.

countries 테이블의 국가/지역 혼재를 해결하여
자기참조 계층형 geographic_regions 테이블을 생성한다.

계층: country (parent) → region (child)
향후 확장: continent → country → region

사용법:
    python scripts/create_geographic_regions.py [--dry-run] [--report]
"""
import sqlite3
import argparse
from collections import defaultdict

DB_PATH = 'trilobase.db'

# 국가 이름 변형 → COW 코드 (countries 테이블에 있지만 실제로는 국가의 별명)
# 이들은 region이 아니라 sovereign state 자체의 다른 이름
COUNTRY_ALIASES = {
    'USA': 2,             # United States of America
    'Luxemburg': 212,     # Luxembourg
    'Burma': 775,         # Myanmar
    'Tadzikhistan': 702,  # Tajikistan
}


def create_table(conn):
    """geographic_regions 테이블 생성."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS geographic_regions (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            level TEXT NOT NULL,
            parent_id INTEGER,
            cow_ccode INTEGER,
            taxa_count INTEGER DEFAULT 0,
            FOREIGN KEY (parent_id) REFERENCES geographic_regions(id)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_geo_regions_parent ON geographic_regions(parent_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_geo_regions_level ON geographic_regions(level)")
    conn.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_geo_regions_name_parent
        ON geographic_regions(name, parent_id)
    """)


def populate_countries(conn):
    """Country level 엔트리 생성.

    소스 1: COW 매핑의 고유 주권국가 (55개)
    소스 2: Unmappable 엔트리 (5개) → 독립 country로 처리
    """
    cur = conn.cursor()

    # 1) COW 주권국가: 고유 cow_ccode별로 하나씩
    cur.execute("""
        SELECT DISTINCT cs.cow_ccode, cs.name
        FROM country_cow_mapping ccm
        JOIN cow_states cs ON ccm.cow_ccode = cs.cow_ccode
        WHERE ccm.cow_ccode IS NOT NULL
        ORDER BY cs.name
    """)
    sovereign_states = cur.fetchall()

    country_ids = {}  # cow_ccode → geographic_regions.id
    for cow_ccode, cow_name in sovereign_states:
        cur.execute(
            "INSERT INTO geographic_regions (name, level, parent_id, cow_ccode) VALUES (?, 'country', NULL, ?)",
            (cow_name, cow_ccode)
        )
        country_ids[cow_ccode] = cur.lastrowid

    # 2) Unmappable: cow_ccode IS NULL
    cur.execute("""
        SELECT c.name, c.id
        FROM country_cow_mapping ccm
        JOIN countries c ON ccm.country_id = c.id
        WHERE ccm.cow_ccode IS NULL
        ORDER BY c.name
    """)
    unmappable = cur.fetchall()
    unmappable_ids = {}  # countries.id → geographic_regions.id
    for name, old_country_id in unmappable:
        cur.execute(
            "INSERT INTO geographic_regions (name, level, parent_id, cow_ccode) VALUES (?, 'country', NULL, NULL)",
            (name,)
        )
        unmappable_ids[old_country_id] = cur.lastrowid

    return country_ids, unmappable_ids


def populate_regions_from_countries(conn, country_ids):
    """Source A: countries 테이블의 하위 지역 항목을 region으로 이관.

    manual/prefix 매핑된 항목 중 COUNTRY_ALIASES에 없는 것만.
    """
    cur = conn.cursor()

    cur.execute("""
        SELECT DISTINCT c.id, c.name, ccm.cow_ccode, ccm.notes
        FROM country_cow_mapping ccm
        JOIN countries c ON ccm.country_id = c.id
        WHERE ccm.notes IN ('manual', 'prefix')
        ORDER BY ccm.cow_ccode, c.name
    """)
    rows = cur.fetchall()

    # old_country_id → geographic_regions.id (region level)
    country_to_region = {}
    # (name, parent_geo_id) → geographic_regions.id (dedup용)
    region_lookup = {}

    for old_id, name, cow_ccode, notes in rows:
        if name in COUNTRY_ALIASES:
            # 국가 별명은 region으로 만들지 않음
            continue

        parent_geo_id = country_ids.get(cow_ccode)
        if not parent_geo_id:
            continue

        key = (name, parent_geo_id)
        if key in region_lookup:
            country_to_region[old_id] = region_lookup[key]
            continue

        cur.execute(
            "INSERT INTO geographic_regions (name, level, parent_id, cow_ccode) VALUES (?, 'region', ?, NULL)",
            (name, parent_geo_id)
        )
        geo_id = cur.lastrowid
        region_lookup[key] = geo_id
        country_to_region[old_id] = geo_id

    return country_to_region, region_lookup


def populate_regions_from_genus_locations(conn, country_ids, region_lookup):
    """Source B: genus_locations.region 텍스트에서 region 엔트리 생성.

    각 (region_text, sovereign_country) 쌍에 대해 하나의 region 엔트리.
    Source A에서 이미 만든 것과 중복이면 스킵.
    """
    cur = conn.cursor()

    # genus_locations에서 고유 (country_id, region) 쌍 추출
    # country_id → cow_ccode 변환이 필요
    cur.execute("""
        SELECT DISTINCT gl.country_id, gl.region, ccm.cow_ccode
        FROM genus_locations gl
        JOIN country_cow_mapping ccm ON gl.country_id = ccm.country_id
        WHERE gl.region IS NOT NULL AND gl.region != ''
        ORDER BY ccm.cow_ccode, gl.region
    """)
    rows = cur.fetchall()

    new_count = 0
    skip_count = 0
    # region_text_lookup: (region_text, cow_ccode) → geographic_regions.id
    region_text_lookup = {}

    for old_country_id, region_text, cow_ccode in rows:
        # COUNTRY_ALIASES 처리: USA의 region은 USA가 아니라 US의 cow_ccode 사용
        if old_country_id in _alias_country_ids:
            cow_ccode = COUNTRY_ALIASES[_alias_country_names[old_country_id]]

        if cow_ccode is None:
            # unmappable country의 region
            # unmappable country를 parent로 사용
            parent_geo_id = _unmappable_ids.get(old_country_id)
            if not parent_geo_id:
                continue
        else:
            parent_geo_id = country_ids.get(cow_ccode)
            if not parent_geo_id:
                continue

        # 이미 텍스트 기준으로 처리했으면 스킵
        text_key = (region_text, parent_geo_id)
        if text_key in region_text_lookup:
            continue

        # Source A에서 이미 만들었으면 재사용
        key = (region_text, parent_geo_id)
        if key in region_lookup:
            region_text_lookup[text_key] = region_lookup[key]
            skip_count += 1
            continue

        cur.execute(
            "INSERT INTO geographic_regions (name, level, parent_id, cow_ccode) VALUES (?, 'region', ?, NULL)",
            (region_text, parent_geo_id)
        )
        geo_id = cur.lastrowid
        region_lookup[key] = geo_id
        region_text_lookup[text_key] = geo_id
        new_count += 1

    return new_count, skip_count, region_text_lookup


def add_region_id_column(conn):
    """genus_locations에 region_id 컬럼 추가."""
    cur = conn.cursor()
    # 이미 있는지 확인
    cur.execute("PRAGMA table_info(genus_locations)")
    columns = [row[1] for row in cur.fetchall()]
    if 'region_id' not in columns:
        cur.execute("ALTER TABLE genus_locations ADD COLUMN region_id INTEGER REFERENCES geographic_regions(id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_genus_locations_region ON genus_locations(region_id)")


def populate_region_ids(conn, country_ids, country_to_region, region_lookup, unmappable_ids):
    """genus_locations.region_id 채우기."""
    cur = conn.cursor()

    # 모든 genus_locations 행 조회
    cur.execute("""
        SELECT gl.id, gl.country_id, gl.region, ccm.cow_ccode, ccm.notes
        FROM genus_locations gl
        JOIN country_cow_mapping ccm ON gl.country_id = ccm.country_id
    """)
    rows = cur.fetchall()

    mapped = 0
    unmapped = 0

    for gl_id, old_country_id, region_text, cow_ccode, mapping_notes in rows:
        region_id = None

        # 1) unmappable country인 경우
        if cow_ccode is None:
            parent_geo_id = unmappable_ids.get(old_country_id)
            if parent_geo_id and region_text:
                key = (region_text, parent_geo_id)
                region_id = region_lookup.get(key, parent_geo_id)
            elif parent_geo_id:
                region_id = parent_geo_id

        # 2) COUNTRY_ALIASES인 경우 (USA, Burma 등)
        elif old_country_id in _alias_country_ids:
            alias_cow = COUNTRY_ALIASES[_alias_country_names[old_country_id]]
            parent_geo_id = country_ids.get(alias_cow)
            if region_text and parent_geo_id:
                key = (region_text, parent_geo_id)
                region_id = region_lookup.get(key, parent_geo_id)
            elif parent_geo_id:
                region_id = parent_geo_id

        # 3) exact match country (주권국가 그 자체)
        elif mapping_notes == 'exact':
            parent_geo_id = country_ids.get(cow_ccode)
            if region_text and parent_geo_id:
                key = (region_text, parent_geo_id)
                region_id = region_lookup.get(key, parent_geo_id)
            elif parent_geo_id:
                region_id = parent_geo_id

        # 4) manual/prefix (countries 테이블의 하위 지역)
        else:
            # old_country_id 자체가 region으로 변환됨
            geo_region_id = country_to_region.get(old_country_id)
            if region_text:
                # 하위 지역 아래에 또 sub-region이 있는 경우
                # → sovereign state 바로 아래 region으로 찾기
                parent_geo_id = country_ids.get(cow_ccode)
                if parent_geo_id:
                    key = (region_text, parent_geo_id)
                    region_id = region_lookup.get(key, geo_region_id)
            else:
                region_id = geo_region_id

        if region_id:
            cur.execute("UPDATE genus_locations SET region_id = ? WHERE id = ?", (region_id, gl_id))
            mapped += 1
        else:
            unmapped += 1

    return mapped, unmapped


def update_taxa_counts(conn):
    """taxa_count 계산."""
    cur = conn.cursor()

    # Region level: 직접 연결된 genus 수
    cur.execute("""
        UPDATE geographic_regions SET taxa_count = (
            SELECT COUNT(DISTINCT gl.genus_id)
            FROM genus_locations gl
            WHERE gl.region_id = geographic_regions.id
        ) WHERE level = 'region'
    """)

    # Country level: 자신에 직접 연결된 + 하위 region 전부
    cur.execute("""
        UPDATE geographic_regions SET taxa_count = (
            SELECT COUNT(DISTINCT gl.genus_id)
            FROM genus_locations gl
            WHERE gl.region_id = geographic_regions.id
               OR gl.region_id IN (
                   SELECT gr.id FROM geographic_regions gr
                   WHERE gr.parent_id = geographic_regions.id
               )
        ) WHERE level = 'country'
    """)


def report(conn):
    """결과 리포트."""
    cur = conn.cursor()

    cur.execute("SELECT level, COUNT(*) FROM geographic_regions GROUP BY level ORDER BY level")
    levels = cur.fetchall()

    cur.execute("SELECT COUNT(*) FROM geographic_regions")
    total = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM genus_locations WHERE region_id IS NOT NULL")
    mapped = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM genus_locations WHERE region_id IS NULL")
    unmapped = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM genus_locations")
    total_gl = cur.fetchone()[0]

    print("\n=== Geographic Regions 결과 ===")
    for level, cnt in levels:
        print(f"  {level}: {cnt}건")
    print(f"  총계: {total}건")

    print(f"\n=== genus_locations.region_id 매핑 ===")
    print(f"  매핑 완료: {mapped}/{total_gl} ({mapped/total_gl*100:.1f}%)")
    if unmapped:
        print(f"  미매핑: {unmapped}건")

    # Top countries by taxa_count
    cur.execute("""
        SELECT name, taxa_count FROM geographic_regions
        WHERE level = 'country' AND taxa_count > 0
        ORDER BY taxa_count DESC LIMIT 15
    """)
    print(f"\n=== Top 15 Countries ===")
    for name, cnt in cur.fetchall():
        print(f"  {name}: {cnt}")

    # Regions per country (top 5)
    cur.execute("""
        SELECT p.name, COUNT(r.id) as region_cnt
        FROM geographic_regions r
        JOIN geographic_regions p ON r.parent_id = p.id
        WHERE r.level = 'region'
        GROUP BY p.id
        ORDER BY region_cnt DESC
        LIMIT 10
    """)
    print(f"\n=== Top 10 Countries by Region Count ===")
    for name, cnt in cur.fetchall():
        print(f"  {name}: {cnt} regions")

    # Unmapped genus_locations details
    if unmapped > 0:
        cur.execute("""
            SELECT c.name, gl.region, COUNT(*) cnt
            FROM genus_locations gl
            JOIN countries c ON gl.country_id = c.id
            WHERE gl.region_id IS NULL
            GROUP BY c.name, gl.region
            ORDER BY cnt DESC
            LIMIT 10
        """)
        rows = cur.fetchall()
        if rows:
            print(f"\n=== 미매핑 상위 10건 ===")
            for name, region, cnt in rows:
                print(f"  {name} / {region}: {cnt}건")


# Module-level state for cross-function access
_alias_country_ids = set()    # countries.id of COUNTRY_ALIASES entries
_alias_country_names = {}     # countries.id → alias name
_unmappable_ids = {}          # countries.id → geographic_regions.id


def main():
    parser = argparse.ArgumentParser(description='Geographic Regions 계층 구조 생성')
    parser.add_argument('--dry-run', action='store_true', help='변경 없이 결과만 확인')
    parser.add_argument('--report', action='store_true', help='리포트만 출력')
    args = parser.parse_args()

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")

    global _alias_country_ids, _alias_country_names, _unmappable_ids

    if args.report:
        report(conn)
        conn.close()
        return

    # 기존 테이블 확인
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='geographic_regions'")
    if cur.fetchone():
        print("geographic_regions 테이블이 이미 존재합니다.")
        print("재생성하려면 먼저 삭제하세요: DROP TABLE geographic_regions")
        conn.close()
        return

    # COUNTRY_ALIASES의 countries.id 조회
    for alias_name, cow_ccode in COUNTRY_ALIASES.items():
        cur.execute("SELECT id FROM countries WHERE name = ?", (alias_name,))
        row = cur.fetchone()
        if row:
            _alias_country_ids.add(row[0])
            _alias_country_names[row[0]] = alias_name

    print("=== Step 1: 테이블 생성 ===")
    create_table(conn)

    print("=== Step 2: Country level 생성 ===")
    country_ids, _unmappable_ids = populate_countries(conn)
    print(f"  주권국가: {len(country_ids)}건, unmappable: {len(_unmappable_ids)}건")

    print("=== Step 3: Region level 생성 (Source A: countries 테이블) ===")
    country_to_region, region_lookup = populate_regions_from_countries(conn, country_ids)
    print(f"  countries → region 변환: {len(country_to_region)}건")

    print("=== Step 4: Region level 생성 (Source B: genus_locations.region) ===")
    new_count, skip_count, region_text_lookup = populate_regions_from_genus_locations(
        conn, country_ids, region_lookup
    )
    print(f"  신규 region: {new_count}건, 기존과 중복 스킵: {skip_count}건")

    print("=== Step 5: genus_locations.region_id 컬럼 추가 ===")
    add_region_id_column(conn)

    print("=== Step 6: genus_locations.region_id 채우기 ===")
    mapped, unmapped = populate_region_ids(
        conn, country_ids, country_to_region, region_lookup, _unmappable_ids
    )
    print(f"  매핑: {mapped}건, 미매핑: {unmapped}건")

    print("=== Step 7: taxa_count 계산 ===")
    update_taxa_counts(conn)

    report(conn)

    if args.dry_run:
        print("\n[DRY RUN] 변경 사항을 롤백합니다.")
        conn.rollback()
    else:
        conn.commit()
        print("\n[COMMITTED] 변경 사항이 저장되었습니다.")

    conn.close()


if __name__ == '__main__':
    main()
