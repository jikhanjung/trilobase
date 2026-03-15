"""
extract_pages.py — Treatise PDF 범용 TSF 추출 CLI

Usage:
    # 특정 페이지 범위를 TSF로 출력 (stdout)
    python extract_pages.py data/pdf/Treatise_Mollusca_1960.pdf 192 210

    # 파일로 저장
    python extract_pages.py data/pdf/Treatise_Mollusca_1960.pdf 192 210 -o out.txt

    # 기존 TSF 파일에 추가 삽입 (--insert-before 로 삽입 위치 지정)
    python extract_pages.py data/pdf/Treatise_Cephalopoda_1964.pdf 162 250 \\
        -o data/sources/treatise_cephalopoda_1964.txt \\
        --insert-before "Order ORTHOCERIDA"

    # 원시 텍스트 보기 (TSF 변환 전, 디버깅용)
    python extract_pages.py data/pdf/Treatise_Mollusca_1960.pdf 60 63 --raw

    # 페이지 수 확인
    python extract_pages.py data/pdf/Treatise_Mollusca_1960.pdf --info
"""

import sys
import re
import argparse
import fitz

# ─── temporal codes ────────────────────────────────────────────────────────
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
    (r'\bTert\b', 'NEOG'), (r'\bRec\b', 'REC'),
]

def get_temporal(text):
    for pat, code in TEMPORAL_MAP:
        if re.search(pat, text):
            return code
    return ''

# ─── page text extraction ──────────────────────────────────────────────────
def get_page_text(page, left_frac=0.52):
    """Extract page text handling two-column Treatise layout."""
    w, h = page.rect.width, page.rect.height
    top, bot = h * 0.08, h * 0.95
    left_text  = page.get_text(clip=fitz.Rect(0,   top, w * left_frac, bot))
    right_text = page.get_text(clip=fitz.Rect(w * left_frac, top, w, bot))
    combined = (
        re.sub(r'-\n([a-z])', r'\1', left_text) + '\n' +
        re.sub(r'-\n([a-z])', r'\1', right_text)
    )
    filtered = []
    for line in combined.split('\n'):
        l = line.strip()
        if not l: continue
        if re.match(r'^FIG\.', l) or re.match(r'^Fig\.', l): continue
        if re.match(r'^\d+[a-z]?$', l): continue
        if '© 2009 University of Kansas' in l: continue
        filtered.append(l)
    return '\n'.join(filtered)

# ─── TSF parsing ───────────────────────────────────────────────────────────
RANK_INDENT = {
    'Class': 0, 'Subclass': 2, 'Order': 2, 'Suborder': 4,
    'Superfamily': 4, 'Family': 4, 'Subfamily': 6,
}
RANK_RE  = re.compile(r'^(Class|Subclass|Order|Suborder|Superfamily|Family|Subfamily)\s+([A-Z][A-Za-z]+)\s+(.+)')
GENUS_RE = re.compile(r'^(\??)([A-Z][a-z]+(?:\s+\([A-Z][a-z]+\))?)\s+([A-Z][A-Z\s&.,\'-]+?),\s+(1[0-9]{3})\b')

def _type_species(text):
    m = re.search(r'\[[\*""]([^\];,\n]+)', text)
    if not m:
        return ''
    ts = m.group(1).strip()
    ts = re.split(r'\s*;\s*(?:SD|OD|aD|MD|LD|TD)\b', ts)[0]
    ts = re.split(r'\s*[=!]', ts)[0]
    return ts.strip()[:80]

def _distribution(entry):
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
    return re.sub(r'\s+', ' ', dist).strip()[:200]

def parse_to_tsf(page_texts):
    """Convert extracted page texts to TSF format lines."""
    lines_out  = []
    rank_stack = []
    lines = '\n'.join(page_texts).split('\n')
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
            lines_out.append(f"{'  ' * RANK_INDENT.get(rk, 2)}{rk} {name} {ay}")
            while rank_stack and RANK_INDENT.get(rank_stack[-1], 0) >= RANK_INDENT.get(rk, 0):
                rank_stack.pop()
            rank_stack.append(rk)
            i += 1
            continue

        gm = GENUS_RE.match(line)
        if gm:
            q, gname = gm.group(1), gm.group(2)
            author, year = gm.group(3).strip().rstrip(','), gm.group(4)
            # Accumulate entry until next genus/rank/blank
            entry_lines = [line]
            j = i + 1
            while j < len(lines):
                nxt = lines[j].strip()
                if not nxt: break
                if RANK_RE.match(nxt) or GENUS_RE.match(nxt): break
                entry_lines.append(nxt)
                j += 1
            full = ' '.join(entry_lines)
            ts   = _type_species(full)
            dist = _distribution(full)
            temp = get_temporal(dist)
            dist = re.sub(r'\s+', ' ', dist).strip()
            last_rk  = rank_stack[-1] if rank_stack else 'Family'
            g_indent = '  ' * (RANK_INDENT.get(last_rk, 2) + 1)
            ts_str   = f" [*{ts}]" if ts else ""
            if dist or temp:
                lines_out.append(f"{g_indent}{q}{gname} {author}, {year}{ts_str} | {dist} | {temp}")
            else:
                lines_out.append(f"{g_indent}{q}{gname} {author}, {year}{ts_str}")
            i = j
            continue

        if re.match(r'INCERTAE\s+SEDIS', line, re.I):
            last_rk = rank_stack[-1] if rank_stack else 'Family'
            lines_out.append(f"{'  ' * RANK_INDENT.get(last_rk, 2)}# INCERTAE SEDIS")
        i += 1

    return '\n'.join(lines_out)

# ─── main ──────────────────────────────────────────────────────────────────
def main():
    p = argparse.ArgumentParser(
        description='Extract TSF taxonomy from a Treatise on Invertebrate Paleontology PDF.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument('pdf', help='Path to the Treatise PDF')
    p.add_argument('start', nargs='?', type=int, help='First page (1-indexed)')
    p.add_argument('end',   nargs='?', type=int, help='Last page (1-indexed, inclusive)')
    p.add_argument('-o', '--output', help='Output file (default: stdout)')
    p.add_argument('--insert-before', metavar='PATTERN',
                   help='Insert extracted TSF before first line matching PATTERN in the output file')
    p.add_argument('--raw', action='store_true',
                   help='Print raw extracted text instead of TSF (for debugging)')
    p.add_argument('--info', action='store_true',
                   help='Show PDF page count and exit')
    args = p.parse_args()

    doc = fitz.open(args.pdf)
    total = len(doc)

    if args.info:
        print(f"{args.pdf}: {total} pages")
        doc.close()
        return

    if args.start is None or args.end is None:
        p.error("start and end page numbers are required (unless --info is used)")

    start = max(1, args.start)
    end   = min(total, args.end)

    page_texts = [get_page_text(doc[pg - 1]) for pg in range(start, end + 1)]
    doc.close()

    if args.raw:
        result = '\n'.join(f"# PAGE {start + i}\n{t}" for i, t in enumerate(page_texts))
    else:
        result = parse_to_tsf(page_texts)
        # Clean up FIG. artifacts
        result = re.sub(r'\.\s*--\s*FIG\..*?(?=\s*\||\s*$)', '', result, flags=re.MULTILINE)
        result = re.sub(r'  +', ' ', result)

    if args.output:
        if args.insert_before:
            with open(args.output) as f:
                existing_lines = f.readlines()
            pat = args.insert_before
            idx = next(
                (i for i, ln in enumerate(existing_lines) if pat in ln),
                None
            )
            if idx is None:
                print(f"Warning: pattern '{pat}' not found in {args.output}. Appending.", file=sys.stderr)
                new_lines = existing_lines + ['\n', result + '\n']
            else:
                new_lines = existing_lines[:idx] + [result + '\n\n'] + existing_lines[idx:]
            with open(args.output, 'w') as f:
                f.writelines(new_lines)
            print(f"Inserted {len(result.splitlines())} lines before '{pat}' in {args.output}")
        else:
            with open(args.output, 'w') as f:
                f.write(result + '\n')
            print(f"Written {len(result.splitlines())} lines to {args.output}")
    else:
        print(result)


if __name__ == '__main__':
    main()
