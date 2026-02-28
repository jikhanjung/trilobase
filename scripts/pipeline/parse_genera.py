"""Step 3: Genus entry parsing (improved).

Parses each line of the cleaned genus list into a structured record.
Integrates lessons from fix_formation_misalignment.py, fix_country_id.py,
and fill_temporal_codes.py so that the parsed output is correct from the
start — no post-hoc patches needed.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Geological suffixes indicating a real formation name
FORMATION_SUFFIXES = [
    ' Fm', ' Lst', ' Sh', ' Gp', ' Beds', ' Zone', ' Suite', ' Horizon',
    ' Series', ' Stage', ' Marl', ' Sst', ' Qtz', ' Dol', ' Limestone',
    ' Sandstone', ' Shale', ' Group', ' Congl', ' Volcanics', ' Member',
    ' Mbr', ' Flags', ' Grits', ' Slates', ' Argillite', ' Chert',
    ' Mdst', ' Schiefer', ' Schicten', ' Schichten', ' Cgte',
    ' Quartzite', ' Conglomerate', ' Calc', ' Faunule', ' Grit',
]

# Genuine formations without standard suffixes (from T-5 fix)
FORMATION_WHITELIST = {
    'Andrarum', 'Surkh Bum', 'Sukh Bum', 'Alum Sh', 'Alanis Sh',
    'River Popovka', 'Krekling', 'Huai Luang Sh', 'Herrerias Marl',
    'Donetz Basin', 'Adams Argillite', 'Kiln Mdst', 'Kersdown Chert',
    'White Point Cgte', 'Lingula Flags', 'Lower Lingula Flags',
    'Weston Flags', 'Leenane Grits', "Hell's Mouth Grits",
    'Skiddaw Slates', 'Ty-draw Slates', 'Leimitz Schiefer',
    'Geigen Schiefer', 'Geigen Schiefe', 'Bokkeveld Group',
    'Llanfawr Mdst', 'U Jon-strop Mdst', 'Wiltz Schicten',
    'Peltura-Stufe', 'Maekula-Schichten', 'Herkunfts-Schichten',
    'Alternances Greso Calcaires', 'Alternances Greso-Calcaires',
    'Schistes de Saint-Chinian', 'Schistes non troues',
    'Schistes troues', 'Gres de Marcory',
    'Gres schistes et calcaires', 'Bancos Mixtos',
    'Complejo de Ranaces', 'Chorbusulina wilkesi Faunule',
    'P. forchhammeri Grit', '"Ostrakoden-Kalk"',
    'Bad-Grund/Ober Harz (cuII)', 'Rheinisches Schiefergebirge',
    'Schwarzwald (Black Forrest)', 'Bron-y-Buckley Wood',
    'Chirbet el-Burdsch', 'Chirbet el-Burj', 'Dimeh Salt Plug',
    'Geschiebe glacial erratics', 'glacial boulder', 'glacial erratic',
    'glacial erratic boulders', 'glacial erratics', 'erratic boulders',
}

# Country name normalization (source text variant → canonical name)
COUNTRY_NORMALIZE = {
    'Czech Repubic': 'Czech Republic',
    'N. Ireland': 'N Ireland',
    'NWGreenland': 'NW Greenland',
    'arctic Russia': 'Arctic Russia',
    'eastern Iran': 'Eastern Iran',
    'central Kazakhstan': 'Central Kazakhstan',
    'central Morocco': 'Central Morocco',
    'central Afghanistan': 'Central Afghanistan',
    'southern Kazakhstan': 'S Kazakhstan',
    '" SE Morocco': 'SE Morocco',
    '" Spain': 'Spain',
    'Brasil': 'Brazil',
    'E. Kazakhstan': 'E Kazakhstan',
    'central Kazakhstan': 'Central Kazakhstan',
    'central Morocco': 'Central Morocco',
    'central Afghanistan': 'Central Afghanistan',
    'southern Kazakhstan': 'S Kazakhstan',
    'arctic Russia': 'Arctic Russia',
    'eastern Iran': 'Eastern Iran',
}

# Genus-specific location overrides (parse exceptions)
LOCATION_OVERRIDES: dict[str, str] = {
    'Metagnostus': 'N Germany',
    'Iberocoryphe': 'Spain',
}

# Genus-specific family overrides (not parseable from source text)
FAMILY_OVERRIDES: dict[str, str] = {
    'Melopetasus': 'PROASAPHISCIDAE',  # Manually assigned in reference DB
}

# Valid temporal codes (28 entries from TEMPORAL_RANGES)
VALID_TEMPORAL_CODES = {
    'CAM', 'LCAM', 'MCAM', 'UCAM', 'MUCAM', 'LMCAM',
    'ORD', 'LORD', 'MORD', 'UORD', 'LMORD', 'MUORD',
    'SIL', 'LSIL', 'USIL', 'LUSIL',
    'DEV', 'LDEV', 'MDEV', 'UDEV', 'LMDEV', 'MUDEV', 'EDEV',
    'MISS', 'PENN',
    'PERM', 'LPERM', 'UPERM',
    'INDET',
}

# Temporal code extraction patterns
_CODE_PATTERN = re.compile(
    r'[;.]\s*'
    r'\??'
    r'([A-Z/]+)'
    r'\??'
    r'\s*[.,]?\s*'
    r'(?:\[.*\]\.?)?\s*$'
)
_FALLBACK_CODE_PATTERN = re.compile(
    r'\s+'
    r'\??'
    r'([A-Z/]+)'
    r'\??'
    r'\s*[.,]?\s*'
    r'(?:\[.*\]\.?)?\s*$'
)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class SynonymInfo:
    """Parsed synonym information from a genus entry."""
    type: str           # j.s.s., j.o.s., preocc., replacement, suppressed
    senior_name: str | None = None
    fide_author: str | None = None
    fide_year: str | None = None
    notes: str | None = None


@dataclass
class GenusRecord:
    """Structured genus record parsed from a single text line."""
    name: str
    author: str | None = None
    year: int | None = None
    year_suffix: str | None = None
    type_species: str | None = None
    type_species_author: str | None = None
    formation: str | None = None
    location: str | None = None
    family: str | None = None
    family_qualifier: str | None = None  # 'UNCERTAIN' or 'INDET' or None
    temporal_code: str | None = None
    is_valid: int = 1
    raw_entry: str = ''
    synonyms: list[SynonymInfo] = field(default_factory=list)
    # Derived fields (populated by improved logic)
    country: str | None = None
    region: str | None = None


# ---------------------------------------------------------------------------
# Formation / Location splitting (key improvement from T-5)
# ---------------------------------------------------------------------------

def _has_formation_suffix(text: str) -> bool:
    """Check if text contains a geological formation suffix."""
    for sfx in FORMATION_SUFFIXES:
        if sfx in text or text.endswith(sfx.strip()):
            return True
    return False


def parse_formation_location(text: str | None) -> tuple[str | None, str | None]:
    """Split the text between ] and ; FAMILY; into formation and location.

    Matches original create_database.py behavior: always split on first comma,
    first part = formation, rest = location.  The junction step (junctions.py)
    handles reclassification of country-only entries via Type 1 fix logic.
    """
    if not text:
        return None, None

    text = text.strip()
    if not text:
        return None, None

    if ',' in text:
        first_part, rest = text.split(',', 1)
        return first_part.strip(), rest.strip()
    else:
        return text, None


# ---------------------------------------------------------------------------
# Country / Region extraction (right-to-left, from T-5 fix)
# ---------------------------------------------------------------------------

def extract_country_region(location: str | None,
                           genus_name: str | None = None,
                           ) -> tuple[str | None, str | None]:
    """Extract country (last comma part) and region from location text.

    Returns (country, region) with country normalized.
    """
    if not location:
        return None, None

    # Check genus-specific overrides
    if genus_name and genus_name in LOCATION_OVERRIDES:
        loc = LOCATION_OVERRIDES[genus_name]
        parts = [p.strip() for p in loc.split(',')]
        country = COUNTRY_NORMALIZE.get(parts[-1], parts[-1])
        region = parts[0] if len(parts) > 1 else None
        return country, region

    # Strip quotes
    loc = location.strip().strip('"""\u201c\u201d').strip()

    parts = [p.strip() for p in loc.split(',')]
    country_raw = parts[-1].strip()
    if not country_raw:
        return None, None

    # Check for parenthetical parse error
    if ')' in country_raw and '(' not in country_raw:
        return None, None

    country = COUNTRY_NORMALIZE.get(country_raw, country_raw)
    # Use only the first sub-region part (matching reference DB granularity)
    region = parts[0] if len(parts) > 1 else None

    return country, region


# ---------------------------------------------------------------------------
# Synonym parsing
# ---------------------------------------------------------------------------

_SYNONYM_PATTERNS = [
    # j.s.s. of X, fide AUTHOR, YEAR (at start of brackets)
    (re.compile(
        r'\[j\.s\.s\.?\s*of\s+([^,\]]+)'
        r'(?:,\s*fide\s+(.+?))?'
        r'\]',
        re.IGNORECASE,
    ), 'j.s.s.'),
    # j.s.s. of X after semicolon (e.g., "[preocc., not replaced; j.s.s. of X, fide ...]")
    (re.compile(
        r';\s*(?:possibly\s+)?j\.s\.s\.?\s*of\s+([^,\]]+)'
        r'(?:,\s*fide\s+(.+?))?'
        r'\]',
        re.IGNORECASE,
    ), 'j.s.s.'),
    # "possibly j.s.s." at start of bracket or after content
    # Note: "possibly s.s.s." (senior synonym) should NOT create opinion on THIS genus
    (re.compile(
        r'\[(?:[^\]]*?;\s*)?possibly\s+(?:a\s+)?j\.s\.s\.?\s*of\s+([^,\]]+)'
        r'(?:,\s*fide\s+(.+?))?'
        r'\]',
        re.IGNORECASE,
    ), 'j.s.s.'),
    # NOTE: s.s.s./s.o.s. patterns are NOT in this list.
    # They are handled in _extract_synonyms() post-processing to enrich
    # preocc. entries without creating standalone opinions (D1).
    # j.o.s. of X (at start of brackets, or after preocc./semicolon)
    (re.compile(
        r'\[j\.o\.s\.?\s*of\s+([^\]]+)\]',
        re.IGNORECASE,
    ), 'j.o.s.'),
    # j.o.s. after semicolon or preocc. context (e.g., "[preocc.; j.o.s. of X]")
    (re.compile(
        r';\s*j\.o\.s\.?\s*of\s+([^,\]]+)'
        r'\]',
        re.IGNORECASE,
    ), 'j.o.s.'),
    # NOTE: "and thus j.o.s." pattern is handled via _SYNONYM_OVERRIDES (D2).
    # preocc., replaced by X
    (re.compile(
        r'\[preocc\.\s*(?:\(.*?\))?,?\s*replaced\s+by\s+([^\]]+)\]',
        re.IGNORECASE,
    ), 'preocc.'),
    # preocc. after semicolon (within brackets), replaced by X
    # e.g., "[replacement name for Platymetopus; preocc., replaced by Amphilichas]"
    (re.compile(
        r';\s*preocc\.\s*(?:\(.*?\))?,?\s*replaced\s+by\s+([^\]]+)\]',
        re.IGNORECASE,
    ), 'preocc.'),
    # preocc., not replaced (no replacement name)
    # Note: "never replaced" entries don't get preocc. opinions in reference DB
    (re.compile(
        r'\[preocc\.\s*(?:\(.*?\))?,?\s*not\s+replaced',
        re.IGNORECASE,
    ), 'preocc.'),
    # replacement name for X (at start of brackets or after semicolon)
    # "for" is required to avoid false positives from typos like "foe" (Taihangshaniashania)
    (re.compile(
        r'(?:\[|;\s*)replacement\s+name\s+for\s+([^\]]+)\]',
        re.IGNORECASE,
    ), 'replacement'),
    # D5: suppressed (with "in favour of X" — only match "in favour of", not bare "for")
    (re.compile(
        r'\[suppressed[^\]]*?in\s+favour\s+of\s+([A-Za-z]+)',
        re.IGNORECASE,
    ), 'suppressed'),
    # suppressed (without "in favour of" — no senior name)
    (re.compile(
        r'\[suppressed[^\]]*\]',
        re.IGNORECASE,
    ), 'suppressed'),
]


def _parse_fide(fide_text: str) -> tuple[str | None, str | None]:
    """Parse 'AUTHOR et al., 1990' → (author, year)."""
    if not fide_text:
        return None, None
    fide_text = fide_text.strip().rstrip('.')
    m = re.match(r'(.+?),\s*(\d{4}[a-z]?)\s*$', fide_text)
    if m:
        return m.group(1).strip(), m.group(2)
    return fide_text.strip(), None


def _clean_senior_name(raw: str | None) -> str | None:
    """Extract just the genus name from captured senior name text.

    Handles patterns like:
      "Platynotus CONRAD, 1838" → "Platynotus"
      "Selenoharpes (=Scotoharpes)" → "Scotoharpes"
      "Bronteus and by Goldius" → "Bronteus"
      "Calymene, by ICZN" → "Calymene"
      "either Koneprusia or Isoprusia" → "Koneprusia"  (D4)
    """
    if not raw:
        return None
    raw = raw.strip()
    if not raw:
        return None

    # Handle "(=Name)" or "(= Name)" pattern: use the = name
    eq_m = re.search(r'\(=\s*([A-Za-z]+)\)', raw)
    if eq_m:
        return eq_m.group(1)

    # D4: Handle "either X or Y" → take X (first alternative)
    either_m = re.match(r'either\s+([A-Z][a-z]+)', raw)
    if either_m:
        return either_m.group(1)

    # Take just the first word (genus name), stripping non-alpha chars
    first_word = raw.split()[0].strip('(),;')
    if first_word and first_word[0].isupper() and first_word.isalpha():
        return first_word

    return raw


# D6: Manual synonym overrides keyed by (genus_name, keyword_in_line)
# Only applies when BOTH the genus name AND the keyword match.
_SYNONYM_OVERRIDES: list[tuple[str, str, list[SynonymInfo]]] = [
    ('Ogygia', 'suppressed', [SynonymInfo(type='suppressed', senior_name='Ogygiocaris')]),
    ('Gortania', 'replacement name', [SynonymInfo(type='replacement', senior_name='Microphthalmus')]),
    ('Hausmannia', 'unnecessary replacement', [SynonymInfo(type='preocc.', senior_name='Odontochile')]),  # D2
]

# D1: s.s.s./s.o.s. extraction patterns (supplementary — enrich preocc., not standalone)
# These match WITHIN bracket content (after bracket is already extracted)
_SSS_PATTERN = re.compile(
    r'(?:^|;\s*)(?:possibly\s+)?s\.s\.s\.?\s*of\s*([^,\]]+)',
    re.IGNORECASE,
)
_SOS_PATTERN = re.compile(
    r'(?:^|;\s*)s\.o\.s\.?\s*of\s+([^,\]]+)',
    re.IGNORECASE,
)


def _extract_synonyms(line: str, genus_name: str | None = None) -> list[SynonymInfo]:
    """Extract all synonym records from a genus line."""
    # D6: Check for manual overrides (match genus name AND keyword in line)
    if genus_name:
        for ovr_name, ovr_keyword, ovr_syns in _SYNONYM_OVERRIDES:
            if genus_name == ovr_name and ovr_keyword in line.lower():
                return [SynonymInfo(type=s.type, senior_name=s.senior_name,
                                    fide_author=s.fide_author, fide_year=s.fide_year,
                                    notes=s.notes)
                        for s in ovr_syns]

    results: list[SynonymInfo] = []
    seen_types: set[str] = set()  # Avoid duplicate suppressed matches

    for pattern, syn_type in _SYNONYM_PATTERNS:
        for m in pattern.finditer(line):
            # Skip duplicate suppressed matches (first pattern with capture,
            # second without — only use first if it matched)
            if syn_type == 'suppressed':
                if 'suppressed' in seen_types:
                    continue
                seen_types.add('suppressed')

            info = SynonymInfo(type=syn_type)
            # Extract and clean senior name
            raw_name = m.group(1).strip() if m.lastindex and m.lastindex >= 1 else None
            info.senior_name = _clean_senior_name(raw_name)

            # For j.s.s., extract fide from group 2
            if syn_type == 'j.s.s.' and m.lastindex and m.lastindex >= 2 and m.group(2):
                fide_author, fide_year = _parse_fide(m.group(2))
                info.fide_author = fide_author
                info.fide_year = fide_year

            results.append(info)

    # D1: s.s.s./s.o.s. enrichment — extract senior name from bracket content
    # and apply to existing preocc. entry (don't create standalone opinions).
    preocc_no_senior = [r for r in results if r.type == 'preocc.' and not r.senior_name]
    if preocc_no_senior:
        for bracket_m in re.finditer(r'\[([^\]]+)\]', line):
            bracket = bracket_m.group(1)
            for pat in (_SSS_PATTERN, _SOS_PATTERN):
                sm = pat.search(bracket)
                if sm:
                    senior = _clean_senior_name(sm.group(1).strip())
                    if senior:
                        preocc_no_senior[0].senior_name = senior
                        break
            if preocc_no_senior[0].senior_name:
                break

    # Enrich suppressed entries without senior name using j.s.s./j.o.s. info
    supp_no_senior = [r for r in results if r.type == 'suppressed' and not r.senior_name]
    if supp_no_senior:
        informative = [r for r in results
                       if r.type in ('j.s.s.', 'j.o.s.') and r.senior_name]
        if informative:
            supp_no_senior[0].senior_name = informative[0].senior_name

    # Dedup by (type, senior_name) — overlapping regex patterns can double-match
    # (e.g., Boeckaspis: "possibly j.s.s." matched by both after-semicolon and
    # possibly-j.s.s. patterns)
    seen_pairs: set[tuple[str, str | None]] = set()
    deduped: list[SynonymInfo] = []
    for info in results:
        key = (info.type, info.senior_name)
        if key not in seen_pairs:
            seen_pairs.add(key)
            deduped.append(info)

    return deduped


# ---------------------------------------------------------------------------
# Temporal code extraction (integrates fill_temporal_codes.py fallback)
# ---------------------------------------------------------------------------

def _extract_temporal_code(raw_entry: str) -> str | None:
    """Extract temporal code from raw entry text, with fallback pattern."""
    # Standard: preceded by ; or .
    m = _CODE_PATTERN.search(raw_entry)
    if m:
        candidate = m.group(1)
        parts = candidate.split('/')
        if all(p in VALID_TEMPORAL_CODES for p in parts):
            return candidate

    # Fallback: preceded by whitespace only (no semicolon)
    m = _FALLBACK_CODE_PATTERN.search(raw_entry)
    if m:
        candidate = m.group(1)
        parts = candidate.split('/')
        if all(p in VALID_TEMPORAL_CODES for p in parts):
            return candidate

    return None


# ---------------------------------------------------------------------------
# Main entry parser
# ---------------------------------------------------------------------------

def parse_entry(line: str) -> GenusRecord | None:
    """Parse a single genus entry line into a GenusRecord.

    Integrates formation/location fix, country extraction, and
    temporal code fallback.
    """
    line = line.strip()
    if not line:
        return None

    rec = GenusRecord(name='', raw_entry=line)

    # --- Genus name (first word) ---
    m = re.match(r'^([A-ZÀ-Ža-zà-ž]+)', line)
    if not m:
        return None
    rec.name = m.group(1)

    # --- Author and year ---
    m = re.match(r'^[A-ZÀ-Ža-zà-ž]+\s+(.+?),\s*(\d{4})([a-z])?', line)
    if m:
        rec.author = m.group(1).strip()
        rec.year = int(m.group(2))
        rec.year_suffix = m.group(3)

    # --- Type species (first [...] that isn't a synonym) ---
    type_match = re.search(r'\[([^\]]+)\]', line)
    if type_match:
        tc = type_match.group(1)
        if not tc.startswith(('j.s.s.', 'j.o.s.', 'preocc.', 'replacement',
                              'suppressed', 'unnecessary')):
            sp_match = re.match(r'^([A-Z][a-z]+ [a-z]+)\s+([A-Z].+)$', tc)
            if sp_match:
                rec.type_species = sp_match.group(1)
                rec.type_species_author = sp_match.group(2)
            else:
                rec.type_species = tc

    # --- Family and temporal code (last two ;-separated fields) ---
    # Standard: ; FAMILY; TEMPORAL.
    # Also handles: ?FAMILY, ??FAMILY, FAMILY?, UNCERTAIN, INDET, etc.
    family_temporal = re.search(
        r';\s*(\?{0,2}[A-Z]+(?:IDAE|INAE)?\??)(?:\s+(?:FAMILY\s+)?UNCERTAIN|\s*\([^)]*\))?\s*;\s*\??([A-Z/]+)\??\s*[.,]?\s*(?:\[|$)',
        line
    )
    # Fallback: family after ] or , or : (missing leading ;)
    if not family_temporal:
        family_temporal = re.search(
            r'[,:\]]\s*(\?{0,2}[A-Z]+(?:IDAE|INAE)\??)(?:\s+(?:FAMILY\s+)?UNCERTAIN)?\s*;\s*\??([A-Z/]+)\??\s*[.,]?\s*(?:\[|$)',
            line
        )
    # Fallback: INDET followed by . or ; then temporal ("; INDET.; LCAM." or "; INDET. LCAM.")
    if not family_temporal:
        family_temporal = re.search(
            r';\s*(INDET)\s*\.?[;\s]+([A-Z/]+)\s*\.?\s*(?:\[|$)',
            line
        )
    # Fallback: INDET with parenthetical note ("; INDET (fide ...); ?ORD.")
    if not family_temporal:
        family_temporal = re.search(
            r';\s*(INDET)\s*[.;]?\s*\([^)]*\)\s*[;,]?\s*\??([A-Z/]+)\??\s*\.?\s*(?:\[|$)',
            line
        )
    # Fallback: SUBORDER FAMILY UNCERTAIN at end of line (no temporal code)
    if not family_temporal:
        family_temporal = re.search(
            r';\s*([A-Z]+)\s+(?:FAMILY\s+)?UNCERTAIN\s*\.?\s*$',
            line
        )
    # Fallback: INDET/UNCERTAIN with no temporal code (entry ends with "UNCERTAIN." or "INDET.")
    if not family_temporal:
        family_temporal = re.search(
            r';\s*(INDET|UNCERTAIN|[A-Z]+(?:IDAE|INAE))\s*\.?\s*$',
            line
        )
    # Fallback: lowercase "indet." as family (e.g., "; indet. juvenile?; LCAM.")
    if not family_temporal:
        m = re.search(r';\s*(indet)\s*\..*?;\s*\??([A-Z/]+)\??\s*\.', line)
        if m:
            family_temporal = m

    if family_temporal:
        rec.family = family_temporal.group(1).upper()  # Normalize to uppercase
        if family_temporal.lastindex and family_temporal.lastindex >= 2:
            code_candidate = family_temporal.group(2)
            parts = code_candidate.split('/')
            if all(p in VALID_TEMPORAL_CODES for p in parts):
                rec.temporal_code = code_candidate

        # Determine family_qualifier (INDET, UNCERTAIN)
        if rec.family == 'INDET':
            rec.family_qualifier = 'INDET'
        elif rec.family == 'UNCERTAIN':
            rec.family_qualifier = 'UNCERTAIN'
        elif rec.family and not rec.family.endswith(('IDAE', 'INAE')) \
                and rec.family not in ('NEKTASPIDA',) \
                and not rec.family.startswith('?'):
            # Non-family name (suborder?) — check if FAMILY UNCERTAIN follows
            if re.search(r';\s*' + re.escape(rec.family) + r'\s+(?:FAMILY\s+)?UNCERTAIN',
                         line, re.IGNORECASE):
                rec.family_qualifier = 'UNCERTAIN'

    # Apply family overrides (for entries not parseable from source text)
    if not rec.family and rec.name in FAMILY_OVERRIDES:
        rec.family = FAMILY_OVERRIDES[rec.name]

    # --- If no temporal code from structured parse, try regex on raw ---
    if not rec.temporal_code:
        rec.temporal_code = _extract_temporal_code(line)

    # --- Formation / Location (between ] and ; FAMILY;) ---
    # Match family patterns including ?FAMILY, ??FAMILY, FAMILY?, UNCERTAIN, INDET
    loc_match = re.search(
        r'\]\s*([^;]+?);\s*\?{0,2}[A-Z]+(?:IDAE|INAE)?\??(?:\s+(?:FAMILY\s+)?UNCERTAIN|\s*\([^)]*\))?;',
        line,
    )
    # Fallback: location before ; INDET
    if not loc_match:
        loc_match = re.search(
            r'\]\s*([^;]+?);\s*INDET\b',
            line,
        )
    if loc_match:
        loc_str = loc_match.group(1).strip()
        # Fix H: strip residual bracket content that leaked from type species
        loc_str = re.sub(r'[^\]]*\]\s*', '', loc_str).strip()
        fm, loc = parse_formation_location(loc_str)
        rec.formation = fm
        rec.location = loc
    else:
        # Try alternative: some entries have no type species bracket
        # e.g. entries with [suppressed ...] only
        pass

    # --- Country / Region extraction ---
    if rec.location:
        rec.country, rec.region = extract_country_region(
            rec.location, rec.name
        )
    elif rec.formation and not _has_formation_suffix(rec.formation) and rec.formation not in FORMATION_WHITELIST:
        # Formation might actually be a country (Type 1 fix case)
        # Check if it looks like a country name (will be validated in junction step)
        pass

    # --- Synonyms ---
    rec.synonyms = _extract_synonyms(line, rec.name)

    # --- Validity ---
    # Match the reference DB behavior:
    # 1. Original narrow regex (bracket-initial) for j.s.s./j.o.s./suppressed/preocc.
    # 2. Additional patterns for specific nomenclatural acts
    _orig_jss = re.search(
        r'\[j\.s\.s\.?\s*of\s+([^,\]]+)(?:,\s*fide\s+([^,\]]+))?(?:,\s*(\d{4}))?\]',
        line, re.IGNORECASE
    )
    _orig_jos = re.search(
        r'\[j\.o\.s\.?\s*of\s+([^\]]+)\]',
        line, re.IGNORECASE
    )
    # Match "suppressed" anywhere in the line (not just bracket-initial)
    # to catch mid-bracket uses like "[s.o.s. of X, but suppressed in favour of Y]"
    _orig_suppressed = re.search(r'\bsuppressed\b', line, re.IGNORECASE)
    _orig_preocc = re.search(r'\[preocc\.', line, re.IGNORECASE)

    if _orig_jss or _orig_jos or _orig_suppressed or _orig_preocc:
        rec.is_valid = 0

    # Additional invalidity patterns (from fix scripts and reference DB analysis)
    _invalid_patterns = [
        'unnecessary replacement',
        'unnecessary emendation',
        'error for ',
        'misspelling of ',
        'see note 2',               # Rafinesque nomina dubia (9 genera)
        'inappropriate emendation',
        'unjustified emendation',
        'incorrect spelling of',
        'invalid spelling emendation',
        'not a trilobite',
        'inappropriate proposal',
        'rejected by iczn',          # s.o.s. rejected (Gortania)
    ]
    lower_line = line.lower()
    if any(p in lower_line for p in _invalid_patterns):
        rec.is_valid = 0

    # Replacement name that is itself preoccupied or j.o.s.
    # (e.g., "[replacement name for X; preocc., replaced by Y]")
    if re.search(r'\breplacement\s+name\b.*?;\s*(?:preocc\.|j\.o\.s\.)',
                 line, re.IGNORECASE):
        rec.is_valid = 0

    # Edge-case overrides (verified against reference DB)
    _VALIDITY_OVERRIDES = {
        'Deucalion': 1,     # Valid despite "nomen dubium and j.s.s." in brackets
        'Nitidocare': 0,    # Truncated entry, invalid in reference
    }
    if rec.name in _VALIDITY_OVERRIDES:
        rec.is_valid = _VALIDITY_OVERRIDES[rec.name]

    return rec


# ---------------------------------------------------------------------------
# Batch parser
# ---------------------------------------------------------------------------

def parse_all(lines: list[str]) -> list[GenusRecord]:
    """Parse all genus lines, returning list of GenusRecord."""
    records: list[GenusRecord] = []
    errors: list[tuple[int, str]] = []
    for i, line in enumerate(lines, 1):
        try:
            rec = parse_entry(line)
            if rec and rec.name:
                records.append(rec)
            else:
                errors.append((i, line[:80]))
        except Exception as e:
            errors.append((i, f'{e}: {line[:60]}'))

    if errors:
        print(f'  [parse_genera] {len(errors)} parse errors:')
        for lineno, msg in errors[:5]:
            print(f'    Line {lineno}: {msg}')
        if len(errors) > 5:
            print(f'    ... and {len(errors) - 5} more')

    # Post-process: Type 3 formation→region reclassification.
    # When formation has no geological suffix and is not in FORMATION_WHITELIST,
    # it's actually a region/location, not a formation name.
    # Fix G: two conditions — (1) original: has country, no region;
    #         (2) new: no location at all (single text between ] and ; FAMILY;)
    type3_count = 0
    for rec in records:
        if rec.formation \
                and not _has_formation_suffix(rec.formation) \
                and rec.formation not in FORMATION_WHITELIST:
            # Reclassify if: (a) has country but no region (original),
            # or (b) entire text is in formation with no location (no comma)
            if (rec.country and not rec.region) or rec.location is None:
                if rec.location:
                    rec.location = f'{rec.formation}, {rec.location}'
                else:
                    rec.location = rec.formation
                old_fm = rec.formation
                rec.formation = None
                # Re-extract country/region from updated location
                rec.country, rec.region = extract_country_region(
                    rec.location, rec.name
                )
                type3_count += 1
    if type3_count:
        print(f'  [parse_genera] {type3_count} Type 3 formation→region reclassifications')

    # Post-process: NOTE 8 homonym handling.
    # Second occurrence of a genus name with "[see NOTE 8]" is the
    # junior homonym and should be marked invalid.
    seen_names: set[str] = set()
    for rec in records:
        if rec.name in seen_names:
            if 'see note 8' in rec.raw_entry.lower():
                rec.is_valid = 0
        else:
            seen_names.add(rec.name)

    return records
