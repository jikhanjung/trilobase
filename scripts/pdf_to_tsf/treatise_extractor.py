"""
Treatise on Invertebrate Paleontology - Full TSF Extractor
Handles two-column pages, genus entry reconstruction, and TSF output.
"""
import fitz, re, sys

# ── Temporal code mapping ──────────────────────────────────────────────────
TEMPORAL_MAP = [
    (r'\bL\.Cam\b', 'LCAM'), (r'\bM\.Cam\b', 'MCAM'), (r'\bU\.Cam\b', 'UCAM'), (r'\bCam\b', 'CAM'),
    (r'\bL\.Ord\b', 'LORD'), (r'\bM\.Ord\b', 'MORD'), (r'\bU\.Ord\b', 'UORD'), (r'\bOrd\b', 'ORD'),
    (r'\bL\.Sil\b', 'LSIL'), (r'\bU\.Sil\b', 'USIL'), (r'\bSil\b', 'SIL'),
    (r'\bL\.Dev\b', 'LDEV'), (r'\bM\.Dev\b', 'MDEV'), (r'\bU\.Dev\b', 'UDEV'), (r'\bDev\b', 'DEV'),
    (r'\bU\.Miss\b', 'UMISS'), (r'\bL\.Miss\b', 'LMISS'), (r'\bMiss\b', 'MISS'),
    (r'\bU\.Penn\b', 'UPENN'), (r'\bL\.Penn\b', 'LPENN'), (r'\bPenn\b', 'PENN'),
    (r'\bU\.Carb\b', 'UCARB'), (r'\bL\.Carb\b', 'LCARB'), (r'\bCarb\b', 'CARB'),
    (r'\bL\.Perm\b', 'LPERM'), (r'\bU\.Perm\b', 'UPERM'), (r'\bPerm\b', 'PERM'),
    (r'\bL\.Trias\b', 'LTRIAS'), (r'\bM\.Trias\b', 'MTRIAS'), (r'\bU\.Trias\b', 'UTRIAS'),
    (r'\bTrias\b', 'TRIAS'),
    (r'\bL\.Jur\b', 'LJUR'), (r'\bM\.Jur\b', 'MJUR'), (r'\bU\.Jur\b', 'UJUR'), (r'\bJur\b', 'JUR'),
    (r'\bL\.Cret\b', 'LCRET'), (r'\bU\.Cret\b', 'UCRET'), (r'\bCret\b', 'CRET'),
    (r'\bPaleoc\b', 'PALEOG'), (r'\bEoc\b', 'PALEOG'), (r'\bOligo\b', 'PALEOG'),
    (r'\bMio\b', 'NEOG'), (r'\bPlio\b', 'NEOG'), (r'\bPleist\b', 'HOL'),
    (r'\bTert\b', 'NEOG'),
    (r'\bRec\b', 'REC'),
]

def get_temporal(text):
    for pat, code in TEMPORAL_MAP:
        if re.search(pat, text):
            return code
    return ''

# ── Page text extraction ───────────────────────────────────────────────────
def extract_column_text(page, left_frac=0.52):
    """Extract left and right column text separately."""
    w = page.rect.width
    h = page.rect.height
    # Margins: skip top ~8% (header) and bottom ~5% (footer/footnote)
    top = h * 0.08
    bot = h * 0.95
    
    left_clip  = fitz.Rect(0, top, w * left_frac, bot)
    right_clip = fitz.Rect(w * left_frac, top, w, bot)
    
    lt = page.get_text(clip=left_clip)
    rt = page.get_text(clip=right_clip)
    return lt, rt

def fix_hyphens(text):
    """Join hyphenated line-breaks."""
    return re.sub(r'-\n([a-z])', r'\1', text)

def clean_block(text):
    """Remove figure captions, page numbers, copyright."""
    lines = []
    for line in text.split('\n'):
        l = line.strip()
        if not l: continue
        if re.match(r'^FIG\.\s+\d+', l): continue
        if re.match(r'^Fig\.\s+\d+', l): continue
        if re.match(r'^\d+[a-z]?$', l): continue  # bare page number
        if '© 2009 University of Kansas' in l: continue
        if re.match(r'^\d+\s+Paleontologist', l): continue
        lines.append(l)
    return '\n'.join(lines)

def get_page_text(page):
    """Get full page text in reading order (left col then right col)."""
    lt, rt = extract_column_text(page)
    combined = fix_hyphens(lt) + '\n' + fix_hyphens(rt)
    return clean_block(combined)

# ── TSF parsing ────────────────────────────────────────────────────────────
RANK_RE = re.compile(
    r'^(Class|Subclass|Order|Suborder|Superfamily|Family|Subfamily)\s+'
    r'([A-Z][A-Za-z]+)\s+(.+)$'
)

RANK_INDENT = {
    'Class': 0, 'Subclass': 2, 'Order': 2, 'Suborder': 4,
    'Superfamily': 4, 'Family': 4, 'Subfamily': 6
}

# Genus start pattern: CapWord or CapWord (SubWord) + ALL_CAPS_AUTHOR + , + YEAR
GENUS_START = re.compile(
    r'^(\??)([A-Z][a-z]+(?:\s+\([A-Z][a-z]+\))?)\s+'
    r'([A-Z][A-Z\s&.,\'-]+?),\s+(1[0-9]{3})\b'
)

def get_type_species(text):
    m = re.search(r'\[[\*""]([^\];]+)', text)
    if m:
        ts = m.group(1).strip()
        ts = re.split(r'\s*;\s*(?:SD|OD|aD|MD|LD|TD)\b', ts)[0]
        ts = re.split(r'\s*[=!]', ts)[0]
        return ts.strip()
    return ''

def get_distribution(entry):
    """Get the stratigraphic/geographic distribution string."""
    # Remove figure reference
    entry = re.sub(r'--+FIG\..*', '', entry, flags=re.DOTALL)
    entry = re.sub(r'--+Fig\..*', '', entry, flags=re.DOTALL)
    # Remove parenthetical references like (4), (103, p.7)
    entry = re.sub(r'\s*\(\d+(?:,\s*[a-z0-9.\s]+)?\)', '', entry)
    
    # Stratigraphy patterns: L.Ord., Cam., Rec., etc.
    strat = r'(?:\?|\.)?(?:L\.|M\.|U\.)?(?:Cam|Ord|Sil|Dev|Miss|Penn|Carb|Perm|Trias|Jur|Cret|Paleoc|Eoc|Oligo|Mio|Plio|Pleist|Tert|Rec)\b'
    matches = list(re.finditer(strat, entry))
    if not matches:
        return ''
    # Take from the LAST stratigraphic mention backwards
    last_pos = matches[-1].start()
    # Find the sentence start - look for period + space before last_pos
    pre = entry[:last_pos]
    m2 = re.search(r'(?:^|[.\n])\s*([^.\n]+)$', pre)
    if m2:
        dist_start = last_pos - len(m2.group(0)) + len(m2.group(0)) - len(m2.group(1))
    else:
        dist_start = max(0, last_pos - 5)
    
    dist = entry[dist_start:].strip()
    # Clean
    dist = re.sub(r'\s+', ' ', dist).strip().rstrip('.')
    # Cap length
    if len(dist) > 200:
        dist = dist[:200]
    return dist

def current_genus_indent(rank_stack):
    """Given current rank stack, return indent for genus."""
    if not rank_stack:
        return '          '
    last_rank = rank_stack[-1]
    base = RANK_INDENT.get(last_rank, 4)
    return ' ' * (base + 2)

def parse_section(raw_text):
    """Convert raw Treatise text to TSF lines."""
    out = []
    rank_stack = []
    
    # Split into pseudo-paragraphs on blank lines or new entries
    # First, try to reconstruct genus entries that span multiple lines
    # We'll process line by line but track entry context
    
    lines = raw_text.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        
        # Check higher rank
        rm = RANK_RE.match(line)
        if rm:
            rk, name, rest = rm.groups()
            # Extract author/year from rest
            am = re.match(r'([A-Za-z][A-Za-z\s&.,\']+?(?:\s+in\s+[A-Za-z]+)?),\s*(1[0-9]{3})', rest)
            if am:
                ay = f"{am.group(1).strip()}, {am.group(2)}"
            else:
                ay = rest.split('[')[0].strip()[:60]
            indent = ' ' * RANK_INDENT.get(rk, 4)
            out.append(f"{indent}{rk} {name} {ay}")
            # Update rank stack
            while rank_stack and RANK_INDENT.get(rank_stack[-1], 0) >= RANK_INDENT.get(rk, 0):
                rank_stack.pop()
            rank_stack.append(rk)
            i += 1
            continue
        
        # Check genus start
        gm = GENUS_START.match(line)
        if gm:
            q = gm.group(1)
            gname = gm.group(2)
            author = gm.group(3).strip().rstrip(',')
            year = gm.group(4)
            
            # Accumulate the full entry (until next genus/rank or blank line)
            entry_lines = [line]
            j = i + 1
            while j < len(lines):
                nxt = lines[j].strip()
                if not nxt:
                    j += 1
                    break
                if RANK_RE.match(nxt):
                    break
                if GENUS_START.match(nxt):
                    break
                entry_lines.append(nxt)
                j += 1
            
            full_entry = ' '.join(entry_lines)
            
            ts = get_type_species(full_entry)
            ts_str = f" [*{ts}]" if ts else ""
            
            dist = get_distribution(full_entry)
            temp = get_temporal(dist) if dist else ''
            
            dist = re.sub(r'\s+', ' ', dist).strip()
            
            indent = current_genus_indent(rank_stack)
            
            if dist or temp:
                out.append(f"{indent}{q}{gname} {author}, {year}{ts_str} | {dist} | {temp}")
            else:
                out.append(f"{indent}{q}{gname} {author}, {year}{ts_str}")
            
            i = j
            continue
        
        # INCERTAE SEDIS section header
        if re.match(r'INCERTAE\s+SEDIS', line, re.I):
            indent = current_genus_indent(rank_stack)[:-2]
            out.append(f"{indent}# INCERTAE SEDIS")
            i += 1
            continue
        
        i += 1
    
    return '\n'.join(out)

def process_pdf(pdf_path, page_ranges, header_yaml, output_path):
    """Main function to extract TSF from a Treatise PDF."""
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    
    all_text_parts = []
    for (start, end, section_comment) in page_ranges:
        if section_comment:
            all_text_parts.append(f"\n# {section_comment}\n")
        for pg in range(start, min(end+1, total_pages+1)):
            page = doc[pg-1]
            pt = get_page_text(page)
            if pt.strip():
                all_text_parts.append(pt)
    
    doc.close()
    
    raw = '\n'.join(all_text_parts)
    tsf_body = parse_section(raw)
    
    output = header_yaml + '\n\n' + tsf_body + '\n'
    
    with open(output_path, 'w') as f:
        f.write(output)
    
    print(f"Written {len(output.splitlines())} lines to {output_path}")

if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('pdf')
    p.add_argument('start', type=int)
    p.add_argument('end', type=int)
    args = p.parse_args()
    
    doc = fitz.open(args.pdf)
    for pg in range(args.start, args.end+1):
        if pg <= len(doc):
            text = get_page_text(doc[pg-1])
            print(f"\n=== PAGE {pg} ===")
            print(text[:1500])
    doc.close()
