---
name: pdf-to-taxonomy
description: Extract taxonomy content from a paleontological PDF and convert it to a TSF (Taxonomic Source Format) file. Supports both batch (page range) and single-page modes.
user-invocable: true
allowed-tools: Read, Bash, Write, Edit, Grep, Glob
argument-hint: <pdf_path> [<start_page>-<end_page>]
---

# PDF to Taxonomic Source

Extract taxonomy content from a paleontological PDF and convert it to a TSF (Taxonomic Source Format) file saved to `data/sources/`.

## Usage

```
/pdf-to-taxonomy <pdf_path> [<start_page>-<end_page>]
```

- `pdf_path`: Path to the PDF file (relative to project root or absolute)
- `start_page-end_page`: Page range to process (optional; if omitted, auto-detect taxonomy sections)

## Instructions

### Step 1: Determine page range

If no page range is given, scan the PDF to find systematic paleontology sections:

```python
python3 -c "
import fitz, re
doc = fitz.open('<pdf_path>')
hits = []
for i, page in enumerate(doc):
    text = page.get_text()
    if re.search(r'systematic paleontology|systematic description', text, re.I):
        hits.append(i + 1)
print('Systematic sections at pages:', hits)
print('Total pages:', len(doc))
"
```

Also check the table of contents (pages 1–20) to identify the scope and structure of the volume.

If the range is large (>50 pages), confirm with the user before proceeding, or ask which sections to prioritize.

### Step 2: Batch-extract text from page range

Treatise volumes use a two-column layout. Use **clip-based extraction** to avoid column mixing:

```python
python3 << 'EOF'
import fitz, re

def extract_page_text(page):
    w = page.rect.width
    h = page.rect.height
    top = h * 0.08   # skip header
    bot = h * 0.95   # skip footer/footnotes
    left  = page.get_text(clip=fitz.Rect(0,      top, w*0.52, bot))
    right = page.get_text(clip=fitz.Rect(w*0.52, top, w,      bot))
    text = left + '\n' + right
    # fix hyphenated line breaks ("descrip-\ntion" → "description")
    text = re.sub(r'-\n([a-z])', r'\1', text)
    # filter noise
    lines = []
    for line in text.split('\n'):
        l = line.strip()
        if not l: continue
        if '© ' in l and 'University' in l: continue   # copyright notices
        if re.match(r'^FIG\.\s+\d+', l): continue      # figure captions
        if re.match(r'^\d+$', l): continue              # standalone page numbers
        lines.append(l)
    return '\n'.join(lines)

doc = fitz.open('<pdf_path>')
for page_num in range(<start_page> - 1, <end_page>):  # 0-indexed
    page = doc[page_num]
    print(f"\n=== PAGE {page_num + 1} ===")
    print(extract_page_text(page))
EOF
```

**Notes:**
- Full-width headers (section titles spanning both columns) may be clipped — this is acceptable noise.
- Some pages contain stratigraphic range bar charts that produce garbled text ("Cambrian\nOrdovician\n..."). Ignore this noise; vision mode can identify and skip charts visually.

**Vision mode fallback** — use the Read tool with the `pages` parameter if any of these apply to a page:
- Extracted text is under 100 characters (likely scanned)
- Less than 50% alphabetic characters (OCR failure)
- No genus name patterns detected despite expected taxonomy content

**Treatise page numbering:** Each Part has a letter prefix (e.g., `I169` = Part I p.169, `K223` = Part K p.223). To map book page numbers to PDF page numbers, find one known section and calculate the fixed offset for that Part.

**Genus entry reconstruction:** Genus entries often span multiple lines in PDF columns. Accumulate lines until the next genus or rank line begins:

```python
GENUS_START = re.compile(
    r'^(\??)([A-Z][a-z]+(?:\s+\([A-Z][a-z]+\))?)\s+'
    r'([A-Z][A-Z\s&.,\'-]+?),\s+(1[0-9]{3})\b'
)
# accumulate continuation lines until next genus/rank starts
```

### Step 3: Identify taxonomy content

Scan the extracted text for Systematic Paleontology sections containing:
- Order, Suborder, Superfamily, Family, Subfamily, Genus entries
- Authority citations: `Author, Year` or `AUTHOR, YEAR`
- Type species in brackets: `[type species name]`
- Synonym notes: junior subjective/objective synonyms, preoccupied names
- Temporal/stratigraphic information, distribution text

Skip non-taxonomy content (discussion, figures, plates, descriptions, diagnoses, remarks, introductions).

### Step 4: Convert to taxonomic source format

The output is a **TSF (Taxonomic Source Format)** document. It uses indentation to show hierarchy:

```
Order ORDERNAME Author, Year
  Suborder SUBORDERNAME Author, Year
    Superfamily Superfamilyoidea Author, Year
      Family FAMILYNAME Author, Year
        Subfamily SUBFAMILYNAME Author, Year
          GenusName AUTHOR, YEAR [type species] | distribution/range text | TEMPORAL_CODE
            = SynonymName (synonym note)
```

**Format rules:**
- Each rank level is indented by 2 spaces from its parent
- Higher ranks (Order through Subfamily): `RankName TAXONNAME Author, Year`
- Genus entries: `GenusName AUTHOR, YEAR [type species] | distribution/range text | TEMPORAL_CODE` (middle field is source-preserving; omit if not available)
- Synonym lines start with `= ` under the senior taxon, indented one level deeper
- Synonym notes use abbreviated forms: `j.s.s.` (junior subjective synonym), `j.o.s.` (junior objective synonym), `preocc.` (preoccupied)
- `fide AUTHOR, YEAR` = "according to AUTHOR, YEAR"
- Use `?` prefix for questionable assignments (e.g., `?GenusName`)

**Temporal codes** (use when period info is available):

Paleozoic:
- CAM / LCAM/MCAM/UCAM / MUCAM = Cambrian / Lower/Middle/Upper / Middle-Upper
- ORD / LORD/MORD/UORD = Ordovician / Lower/Middle/Upper
- SIL / LSIL/USIL = Silurian / Lower/Upper
- DEV / LDEV/MDEV/UDEV = Devonian / Lower/Middle/Upper
- CARB / LCARB/UCARB = Carboniferous / Lower/Upper
- MISS / PENN = Mississippian / Pennsylvanian
- LPERM/PERM/UPERM = Lower/Middle/Upper Permian

Mesozoic:
- LTRIAS/MTRIAS/UTRIAS = Lower/Middle/Upper Triassic (also LTRI/MTRI/UTRI)
- LJUR/MJUR/UJUR = Lower/Middle/Upper Jurassic
- LCRET/CRET/UCRET = Lower/Cretaceous/Upper Cretaceous

Cenozoic:
- PALEOG = Paleogene
- NEOG = Neogene
- MIO = Miocene
- HOL = Holocene
- REC = Recent

### Step 5: Use batch extraction scripts for Treatise volumes

For large Treatise volumes, use the ready-made scripts in `scripts/pdf_to_tsf/` instead of writing extraction code from scratch:

**Core library** — `scripts/pdf_to_tsf/treatise_extractor.py`
- `get_page_text(page)` — two-column clip-based extraction with noise filtering
- `parse_section(raw_text)` — converts raw text to TSF lines (handles RANK_RE, GENUS_START, type species, distribution, temporal codes)
- `process_pdf(pdf_path, page_ranges, header_yaml, output_path)` — end-to-end extraction
- CLI: `python treatise_extractor.py <pdf> <start> <end>` — prints raw page text for debugging

**General-purpose CLI** — `scripts/pdf_to_tsf/extract_pages.py`
```bash
# Print info (total pages)
python scripts/pdf_to_tsf/extract_pages.py data/pdf/MyTreatise.pdf --info

# Preview raw text (debugging)
python scripts/pdf_to_tsf/extract_pages.py data/pdf/MyTreatise.pdf 50 55 --raw

# Extract and write TSF to file
python scripts/pdf_to_tsf/extract_pages.py data/pdf/MyTreatise.pdf 50 120 -o data/sources/my_treatise.txt

# Insert extracted TSF before a pattern in an existing file
python scripts/pdf_to_tsf/extract_pages.py data/pdf/MyTreatise.pdf 30 49 \
    -o data/sources/my_treatise.txt \
    --insert-before "Order SOMEORDER"
```

**Volume-specific runners** (regenerate full source files from scratch):
- `scripts/pdf_to_tsf/run_mollusca.py` — Treatise Part I (Mollusca 1960), pages 60–355 → `data/sources/treatise_mollusca_1960.txt`
- `scripts/pdf_to_tsf/run_cephalopoda.py` — Treatise Part K (Cephalopoda 1964), pages 162–547 → `data/sources/treatise_cephalopoda_1964.txt`

**When to use scripts vs. manual extraction:**
- **Use scripts** for full Treatise volumes where systematic descriptions span many pages (>20 pages). Start with `extract_pages.py --raw` on a sample range to verify column detection, then run the full range.
- **Use manual extraction** for short papers, articles, or when the PDF layout differs significantly from the standard two-column Treatise format.

For the full TSF specification, see `docs/Taxonomic Source Format Specification v0.1.md`.

If needed, read one or more of these for format examples:
- `data/sources/jell_adrain_2002.txt` — Trilobita: genus-level with type species, formations, temporal codes
- `data/sources/adrain_2011.txt` — Trilobita: suprafamilial classification (Order → Family)
- `data/sources/treatise_1997_ch4.txt` — Trilobita: mixed ranks with subfamilies
- `data/sources/treatise_1997_ch5.txt` — Trilobita: mixed ranks with subfamilies (continued)
- `data/sources/treatise_brachiopoda_1965_vol1.txt` — Brachiopoda: Treatise style, older Paleozoic
- `data/sources/treatise_graptolite_2023.txt` — Graptolita: modern Treatise style
- `data/sources/treatise_chelicerata_1955.txt` — Chelicerata: mixed rank hierarchy
- `data/sources/treatise_ostracoda_1961.txt` — Ostracoda: genus-level, Paleozoic to Recent
- `data/sources/treatise_ammonoidea_1957.txt` — Ammonoidea: Mesozoic temporal codes

### Step 6: Determine output filename and write file

Derive the output filename from the PDF name (e.g., `Treatise_Mollusca_1960.pdf` → `treatise_mollusca_1960.txt`). Save to `data/sources/`.

- If the file does **not** exist: create it with the YAML front matter header first, then the taxonomy body.
- If the file **already exists** (resuming a partial run): append to it, skipping the front matter.

**YAML front matter** (new files only):
```
---
reference: Author(s), Year. Title. Publisher, pages
scope:
  - taxon: TaxonName
    coverage: comprehensive (or partial)
notes: |
  Any relevant notes about the source
---
```

Use the Write tool to create the file, or the Edit tool to append.

### Step 7: Report and confirm

After writing, report:
- Output file path
- Page range processed
- Number of genera/families extracted (approximate)
- Any pages skipped (no taxonomy content) or that needed vision fallback
- If the range was large and only partially done, suggest the next range to continue

## Example Output

```
---
reference: Smith, J.A., 2020. Revision of the family Exampleidae. Journal of Paleontology, 94(3), 456-478
scope:
  - taxon: Exampleidae
    coverage: comprehensive
---

Family EXAMPLEIDAE Smith, 2020
  Exampleus SMITH, 2020 [typicus] | Example Fm, Utah, USA | UCAM
  Oldgenus JONES, 1985 [antiquus] | Old Fm, Nevada, USA | MCAM
    = Badgenus (j.s.s., fide SMITH, 2020)
  ?Maybegenus WANG, 1990 [dubius] | Mystery Fm, Yunnan, China | LCAM
Family OTHERFAMILYIDAE Jones, 1990
  Othergenus JONES, 1990 [primus] | Other Fm, Australia | MCAM
  Latergenus BROWN, 1998 [lateralis] | Later Fm, Morocco | UORD
```
