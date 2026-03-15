import fitz, re

# ── helpers ───────────────────────────────────────────────────────────────
TEMPORAL_MAP = [
    (r'\bL\.Cam\b', 'LCAM'), (r'\bM\.Cam\b', 'MCAM'), (r'\bU\.Cam\b', 'UCAM'), (r'\bCam\b', 'CAM'),
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
    # start from last strat marker, extend back to last sentence boundary
    last_m = matches[-1]
    pre = entry[:last_m.start()]
    # find last sentence boundary (period after content)
    sb = re.search(r'[.]\s+([^.]+)$', pre)
    if sb:
        dist_start = pre.rfind('.') + 1
    else:
        dist_start = max(0, last_m.start() - 20)
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
            # Accumulate entry lines
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
            # current indent based on rank stack
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

# ── Process Mollusca ─────────────────────────────────────────────────────
mol_pdf = '/mnt/d/projects/trilobase/data/pdf/Treatise_Mollusca_1960.pdf'
doc = fitz.open(mol_pdf)
total = len(doc)

sections = [
    (60, 63, "SCAPHOPODA (Class SCAPHOPODA; pages I37-I40)"),
    (72, 99, "AMPHINEURA (Class AMPHINEURA; pages I49-I74)"),
    (100, 108, "MONOPLACOPHORA (Class MONOPLACOPHORA; pages I77-I85)"),
    (192, 332, "GASTROPODA - Systematic Descriptions (pages I169-I309)"),
    (333, 355, "SUPPLEMENT - Paleozoic Caenogastropoda & Opisthobranchia (pages I310-I332)"),
]

all_parts = []
counts = {}
for start, end, comment in sections:
    print(f"Processing {comment[:50]}... ", end='', flush=True)
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
reference: Knight, J.B., Cox, L.R., Keen, A.M., Smith, A.G., Batten, R.L., Yochelson, E.L., Ludbrook, N.H., Robertson, R., Yonge, C.M., & Moore, R.C., 1960. Mollusca 1. In: Moore, R.C. (ed.), Treatise on Invertebrate Paleontology, Part I. Geological Society of America and University of Kansas Press, Lawrence, Kansas. xxiii+351 p.
scope:
  - taxon: Scaphopoda
    coverage: comprehensive
  - taxon: Amphineura
    coverage: comprehensive
  - taxon: Monoplacophora
    coverage: comprehensive
  - taxon: Gastropoda
    coverage: comprehensive
    notes: Archaeogastropoda and some mainly Paleozoic Caenogastropoda and Opisthobranchia
notes: |
  Treatise on Invertebrate Paleontology Part I (Mollusca 1), 1960.
  Covers Scaphopoda, Amphineura (Polyplacophora + Aplacophora),
  Monoplacophora, and Gastropoda (Archaeogastropoda, some Paleozoic
  Caenogastropoda, Opisthobranchia).
  Systematic descriptions: pages I37-I332.
  NOTE: This file was extracted semi-automatically from the PDF.
  Distribution text and temporal codes may require manual review.
source_pdf: data/pdf/Treatise_Mollusca_1960.pdf
format: TSF
version: "0.1"
---
'''

output = HEADER + '\n'.join(all_parts) + '\n'
out_path = '/mnt/d/projects/trilobase/data/sources/treatise_mollusca_1960.txt'
with open(out_path, 'w') as f:
    f.write(output)
print(f"\nTotal lines: {len(output.splitlines())}")
print(f"Written to: {out_path}")
