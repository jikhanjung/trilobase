---
name: pdf-to-taxonomy
description: Read taxonomy content from a paleontological PDF one page at a time and convert it to taxonomy source text format. Supports iterative page-by-page processing.
user-invocable: true
allowed-tools: Read, Bash, Write, Edit, Grep, Glob
argument-hint: <pdf_path> <page_number>
---

# PDF to Taxonomy Source Text

Read taxonomy content from a paleontological PDF one page at a time and convert it to taxonomy source text format. Supports iterative page-by-page processing.

## Usage

```
/pdf-to-taxonomy <pdf_path> <page_number>
```

- `pdf_path`: Path to the PDF file (relative to project root or absolute)
- `page_number`: The page to process

## Instructions

### Step 1: Read the page

Read the specified page using the Read tool with the `pages` parameter.

**If the text extraction result is empty, garbled, or clearly incomplete** (e.g., no recognizable taxonomy text despite the page being expected to contain it), fall back to **vision mode**: re-read the same page as an image using the Read tool (PDF pages render as images). Examine the image visually and extract the taxonomy text from what you see.

### Step 2: Check for page-spanning entries

If the last taxonomic entry on the page appears to be **cut off** (e.g., a genus name with no closing bracket, an incomplete synonym line, or a family heading with no genera yet), peek at the **next page** (page_number + 1) to capture the rest of that entry. Only take what's needed to complete the cut-off entry — the rest of the next page will be processed in a subsequent run.

### Step 3: Identify taxonomy content

Look for Systematic Paleontology sections containing:
- Order, Suborder, Superfamily, Family, Subfamily, Genus entries
- Authority citations: `Author, Year` or `AUTHOR, YEAR`
- Type species in brackets: `[type species name]`
- Synonym notes: junior subjective/objective synonyms, preoccupied names
- Temporal/stratigraphic information, formation names, localities

Skip non-taxonomy content (discussion, figures, plates, descriptions, diagnoses, remarks).

### Step 4: Convert to taxonomy source text format

The output format uses indentation to show hierarchy:

```
Order ORDERNAME Author, Year
  Suborder SUBORDERNAME Author, Year
    Superfamily Superfamilyoidea Author, Year
      Family FAMILYNAME Author, Year
        Subfamily SUBFAMILYNAME Author, Year
          GenusName AUTHOR, YEAR [type species] | Formation, Locality | TEMPORAL_CODE
            = SynonymName (synonym note)
```

**Format rules:**
- Each rank level is indented by 2 spaces from its parent
- Higher ranks (Order through Subfamily): `RankName TAXONNAME Author, Year`
- Genus entries: `GenusName AUTHOR, YEAR [type species] | Formation, Locality | TEMPORAL_CODE`
- Synonym lines start with `= ` under the senior taxon, indented one level deeper
- Synonym notes use abbreviated forms: `j.s.s.` (junior subjective synonym), `j.o.s.` (junior objective synonym), `preocc.` (preoccupied)
- `fide AUTHOR, YEAR` = "according to AUTHOR, YEAR"
- Use `?` prefix for questionable assignments (e.g., `?GenusName`)

**Temporal codes** (use when period info is available):
- LCAM/MCAM/UCAM = Lower/Middle/Upper Cambrian
- LORD/MORD/UORD = Lower/Middle/Upper Ordovician
- LSIL/USIL = Lower/Upper Silurian
- LDEV/MDEV/UDEV = Lower/Middle/Upper Devonian
- MISS/PENN = Mississippian/Pennsylvanian
- LPERM/PERM/UPERM = Lower/Middle/Upper Permian

### Step 5: Reference existing source files

If needed, read one or more of these for format examples:
- `data/sources/jell_adrain_2002.txt` — Genus-level with type species, formations, temporal codes
- `data/sources/adrain_2011.txt` — Suprafamilial classification (Order → Family)
- `data/sources/treatise_2004_ch4.txt` — Mixed ranks with subfamilies

### Step 6: Output the result

- On the **first page** of a new PDF, include a YAML front matter header:
  ```
  ---
  reference: Author(s), Year. Title. Journal, volume, pages
  scope:
    - taxon: TaxonName
      coverage: comprehensive (or partial)
  notes: |
    Any relevant notes about the source
  ---
  ```
- Then output the extracted taxonomy lines for this page.
- If the taxonomy continues beyond this page, end with: `# continues on page N`
- If the page had no taxonomy content, say so.

### Step 7: Prompt for continuation

After outputting the result, ask: **"다음 페이지(N)를 계속 처리할까요?"** so the user can iterate page by page through the PDF.

## Example Output (first page)

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
# continues on page 15
```

## Example Output (subsequent page)

```
  Latergenus BROWN, 1998 [lateralis] | Later Fm, Morocco | UORD
  Newgenus DOE, 2001 [novus] | New Fm, Bolivia | LORD
Family OTHERFAMILYIDAE Jones, 1990
  Othergenus JONES, 1990 [primus] | Other Fm, Australia | MCAM
# continues on page 16
```
