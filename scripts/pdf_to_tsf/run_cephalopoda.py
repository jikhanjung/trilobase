import fitz, re

TEMPORAL_MAP = [
    (r'\bU\.Cam\b', 'UCAM'), (r'\bM\.Cam\b', 'MCAM'), (r'\bL\.Cam\b', 'LCAM'), (r'\bCam\b', 'CAM'),
    (r'\bL\.Ord\b', 'LORD'), (r'\bM\.Ord\b', 'MORD'), (r'\bU\.Ord\b', 'UORD'), (r'\bOrd\b', 'ORD'),
    (r'\bL\.Sil\b', 'LSIL'), (r'\bU\.Sil\b', 'USIL'), (r'\bSil\b', 'SIL'),
    (r'\bL\.Dev\b', 'LDEV'), (r'\bM\.Dev\b', 'MDEV'), (r'\bU\.Dev\b', 'UDEV'), (r'\bDev\b', 'DEV'),
    (r'\bU\.Miss\b', 'UMISS'), (r'\bL\.Miss\b', 'LMISS'), (r'\bMiss\b', 'MISS'),
    (r'\bU\.Penn\b', 'UPENN'), (r'\bL\.Penn\b', 'LPENN'), (r'\bPenn\b', 'PENN'),
    (r'\bU\.Carb\b', 'UCARB'), (r'\bL\.Carb\b', 'LCARB'), (r'\bCarb\b', 'CARB'),
    (r'\bL\.Perm\b', 'LPERM'), (r'\bU\.Perm\b', 'UPERM'), (r'\bPerm\b', 'PERM'),
    (r'\bL\.Trias\b', 'LTRIAS'), (r'\bM\.Trias\b', 'MTRIAS'), (r'\bU\.Trias\b', 'UTRIAS'), (r'\bTrias\b', 'TRIAS'),
    (r'\bL\.Jur\b', 'LJUR'), (r'\bM\.Jur\b', 'MJUR'), (r'\bU\.Jur\b', 'UJUR'), (r'\bJur\b', 'JUR'),
    (r'\bL\.Cret\b', 'LCRET'), (r'\bU\.Cret\b', 'UCRET'), (r'\bCret\b', 'CRET'),
    (r'\bPaleoc\b', 'PALEOG'), (r'\bEoc\b', 'PALEOG'), (r'\bOligo\b', 'PALEOG'),
    (r'\bMio\b', 'NEOG'), (r'\bPlio\b', 'NEOG'), (r'\bPleist\b', 'HOL'),
    (r'\bTert\b', 'NEOG'), (r'\bRec\b', 'REC'),
]

def get_temporal(text):
    for pat, code in TEMPORAL_MAP:
        if re.search(pat, text):
            return code
    return ''

def get_page_text(page):
    w, h = page.rect.width, page.rect.height
    left_text  = page.get_text(clip=fitz.Rect(0, h*0.08, w*0.52, h*0.95))
    right_text = page.get_text(clip=fitz.Rect(w*0.52, h*0.08, w, h*0.95))
    combined = re.sub(r'-\n([a-z])', r'\1', left_text) + '\n' + re.sub(r'-\n([a-z])', r'\1', right_text)
    filtered = []
    for l in combined.split('\n'):
        l = l.strip()
        if not l: continue
        if re.match(r'^FIG\.', l) or re.match(r'^Fig\.', l): continue
        if re.match(r'^\d+[a-z]?$', l): continue
        if '© 2009 University of Kansas' in l: continue
        filtered.append(l)
    return '\n'.join(filtered)

RANK_INDENT = {'Class':0,'Subclass':2,'Order':2,'Suborder':4,
               'Superfamily':4,'Family':4,'Subfamily':6}
RANK_RE = re.compile(r'^(Class|Subclass|Order|Suborder|Superfamily|Family|Subfamily)\s+([A-Z][A-Za-z]+)\s+(.+)')
GENUS_RE = re.compile(r'^(\??)([A-Z][a-z]+(?:\s+\([A-Z][a-z]+\))?)\s+([A-Z][A-Z\s&.,\'-]+?),\s+(1[0-9]{3})\b')

def get_type_species(text):
    m = re.search(r'\[[\*""]([^\];,\n]+)', text)
    if m:
        ts = m.group(1).strip()
        ts = re.split(r'\s*;\s*(?:SD|OD|aD|MD|LD|TD)\b', ts)[0]
        ts = re.split(r'\s*[=!]', ts)[0]
        return ts.strip()[:80]
    return ''

def get_distribution(entry):
    entry = re.sub(r'--+(?:FIG|Fig)\..*', '', entry, flags=re.DOTALL)
    entry = re.sub(r'\s*\(\d+(?:[a-z*]?(?:,\s*\d+)*(?:\s*,\s*p\.\s*\d+)?)?\)', '', entry)
    strat = r'(?:\?)?(?:L\.|M\.|U\.)?(?:Cam|Ord|Sil|Dev|Miss|Penn|Carb|Perm|Trias|Jur|Cret|Paleoc|Eoc|Oligo|Mio|Plio|Pleist|Tert|Rec)[\b.]'
    matches = list(re.finditer(strat, entry))
    if not matches:
        return ''
    last_m = matches[-1]
    pre = entry[:last_m.start()]
    dist_start = max(0, pre.rfind('.') + 1) if '.' in pre else 0
    dist = entry[dist_start:].strip().rstrip('.')
    dist = re.sub(r'\s+', ' ', dist).strip()
    return dist[:200]

def parse_to_tsf(pages_text_list):
    lines_out = []
    rank_stack = []
    full_text = '\n'.join(pages_text_list)
    lines = full_text.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        rm = RANK_RE.match(line)
        if rm:
            rk, name, rest = rm.groups()
            am = re.match(r'([A-Za-z][A-Za-z\s&.,\']+?(?:\s+in\s+[A-Za-z]+)?),\s*(1[0-9]{3})', rest)
            ay = f"{am.group(1).strip()}, {am.group(2)}" if am else rest.split('[')[0].strip()[:60]
            indent = ' ' * RANK_INDENT.get(rk, 4)
            lines_out.append(f"{indent}{rk} {name} {ay}")
            while rank_stack and RANK_INDENT.get(rank_stack[-1],0) >= RANK_INDENT.get(rk,0):
                rank_stack.pop()
            rank_stack.append(rk)
            i += 1
            continue
        gm = GENUS_RE.match(line)
        if gm:
            q, gname, author, year = gm.group(1), gm.group(2), gm.group(3).strip().rstrip(','), gm.group(4)
            entry_lines = [line]
            j = i + 1
            while j < len(lines):
                nxt = lines[j].strip()
                if not nxt: break
                if RANK_RE.match(nxt) or GENUS_RE.match(nxt): break
                entry_lines.append(nxt)
                j += 1
            full_entry = ' '.join(entry_lines)
            ts = get_type_species(full_entry)
            ts_str = f" [*{ts}]" if ts else ""
            dist = get_distribution(full_entry)
            temp = get_temporal(dist)
            dist = re.sub(r'\s+', ' ', dist).strip()
            last_rk = rank_stack[-1] if rank_stack else 'Family'
            g_indent = ' ' * (RANK_INDENT.get(last_rk, 4) + 2)
            if dist or temp:
                lines_out.append(f"{g_indent}{q}{gname} {author}, {year}{ts_str} | {dist} | {temp}")
            else:
                lines_out.append(f"{g_indent}{q}{gname} {author}, {year}{ts_str}")
            i = j
            continue
        if re.match(r'INCERTAE\s+SEDIS', line, re.I):
            last_rk = rank_stack[-1] if rank_stack else 'Family'
            indent = ' ' * RANK_INDENT.get(last_rk, 4)
            lines_out.append(f"{indent}# INCERTAE SEDIS")
        i += 1
    return '\n'.join(lines_out)

# Process Cephalopoda
ceph_pdf = '/mnt/d/projects/trilobase/data/pdf/Treatise_Cephalopoda_1964.pdf'
doc = fitz.open(ceph_pdf)
total = len(doc)

sections = [
    (162, 192, "Subclass ENDOCERATOIDEA / Order ELLESMEROCERIDA (pages K133-K164)"),
    (193, 230, "Order ENDOCERIDA (pages K165-K202)"),
    (231, 250, "Subclass ACTINOCERATOIDEA / Order ACTINOCERIDA (pages K203-K222)"),
    (251, 547, "Subclass NAUTILOIDEA + Subclass BACTRITOIDEA - Systematic Descriptions (pages K223-K519)"),
]

all_parts = []
for start, end, comment in sections:
    print(f"Processing pages {start}-{end}... ", end='', flush=True)
    page_texts = []
    for pg in range(start, min(end+1, total+1)):
        page_texts.append(get_page_text(doc[pg-1]))
    tsf = parse_to_tsf(page_texts)
    genus_count = len([l for l in tsf.split('\n') if re.match(r'\s{6,}[A-Z?]', l) and re.search(r',\s*1[0-9]{3}', l)])
    print(f"{genus_count} genera")
    all_parts.append(f"\n# {'─'*60}\n# {comment}\n# {'─'*60}\n")
    all_parts.append(tsf)

doc.close()

HEADER = '''---
reference: Teichert, C., Kummel, B., Sweet, W.C., Stenzel, H.B., Furnish, W.M., Glenister, B.F., Erben, H.K., Moore, R.C., & Nodine Zeller, D.E., 1964. Cephalopoda - General Features, Endoceratoidea, Actinoceratoidea, Nautiloidea, Bactritoidea. In: Moore, R.C. (ed.), Treatise on Invertebrate Paleontology, Part K, Mollusca 3. Geological Society of America and University of Kansas Press, Lawrence, Kansas. xxviii+519 p.
scope:
  - taxon: Nautiloidea
    coverage: comprehensive
  - taxon: Endoceratoidea
    coverage: comprehensive
  - taxon: Actinoceratoidea
    coverage: comprehensive
  - taxon: Bactritoidea
    coverage: comprehensive
notes: |
  Treatise on Invertebrate Paleontology Part K (Mollusca 3 - Cephalopoda), 1964.
  Covers nautiloid cephalopods: Endoceratoidea, Actinoceratoidea, Nautiloidea
  (Orders: Ellesmerocerida, Orthocerida, Pseudorthocerida, Endocerida,
  Tarphycerida, Oncocerida, Discosorida, Ascocerida, Barrandeocerida,
  Nautilida), and Bactritoidea.
  Does NOT cover Ammonoidea (Part L) or Coleoidea (Part M).
  Systematic descriptions begin at K223.
  NOTE: This file was extracted semi-automatically from the PDF.
  Distribution text and temporal codes may require manual review.
source_pdf: data/pdf/Treatise_Cephalopoda_1964.pdf
format: TSF
version: "0.1"
---
'''

output = HEADER + '\n'.join(all_parts) + '\n'
out_path = '/mnt/d/projects/trilobase/data/sources/treatise_cephalopoda_1964.txt'
with open(out_path, 'w') as f:
    f.write(output)
print(f"\nTotal lines: {len(output.splitlines())}")
print(f"Written to: {out_path}")
