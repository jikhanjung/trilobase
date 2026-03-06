#!/usr/bin/env python3
"""
OCR-extract genus names from Treatise 1959 systematic descriptions.

Pages O172-O525 (PDF pages ~192-545).
Uses Tesseract OCR via pdf2image + pytesseract.

Strategy:
1. Convert each PDF page to image at 300 DPI
2. OCR with Tesseract
3. Parse genus names using pattern matching:
   - "Family FAMILYNAME Author, year" headers
   - "Subfamily SUBFAMILYNAME..." headers
   - Genus entries: "Genusname AUTHOR, year" (bold genus + small-caps author)
4. Save raw OCR text and extracted genera
"""

import json
import re
import sys
import os
from pathlib import Path

def ocr_pages(pdf_path, start_page, end_page, dpi=300, batch_size=5):
    """OCR a range of PDF pages, yielding (page_num, text) tuples."""
    from pdf2image import convert_from_path
    import pytesseract

    for batch_start in range(start_page, end_page + 1, batch_size):
        batch_end = min(batch_start + batch_size - 1, end_page)
        print(f"  OCR pages {batch_start}-{batch_end}...", flush=True)
        try:
            images = convert_from_path(
                pdf_path,
                first_page=batch_start,
                last_page=batch_end,
                dpi=dpi
            )
            for i, img in enumerate(images):
                page_num = batch_start + i
                text = pytesseract.image_to_string(img)
                yield page_num, text
        except Exception as e:
            print(f"  ERROR on pages {batch_start}-{batch_end}: {e}")


def extract_genera_from_text(text):
    """Extract genus names from OCR text of a single page.

    Genus entries in the Treatise follow the pattern:
    GenusName AUTHOR, YEAR [*type species]

    The genus name starts at the beginning of a line or after whitespace,
    is capitalized (first letter upper, rest lower), followed by author in
    CAPS and a 4-digit year.
    """
    genera = []

    # Pattern: Genus name (capitalized word) followed by author (ALL CAPS word)
    # and year (4 digits). The genus name is typically italic in the original.
    # In OCR, it appears as a normal word.
    # Examples from OCR:
    #   "Agnostus BRONGNIART, 1822"
    #   "Fallagnostus Howell, 1935"  (sometimes mixed case for author)
    #   "Acmarhachis RESSER, 1938"

    # Pattern 1: Standard genus entry at start of line or paragraph
    # GenusName AUTHOR, YEAR or GenusName Author, YEAR
    pattern = r'(?:^|\n)\s*([A-Z][a-z]{2,}(?:[a-z]+)?)\s+([A-Z][A-Za-z&\s\.]+?),?\s*(1[789]\d{2})'

    for m in re.finditer(pattern, text):
        genus = m.group(1)
        author = m.group(2).strip()
        year = m.group(3)

        # Filter out non-genus words (common OCR artifacts and section headers)
        skip_words = {
            'Family', 'Subfamily', 'Superfamily', 'Suborder', 'Order', 'Class',
            'Marine', 'Diminutive', 'Cephalon', 'Glabella', 'Longitudinal',
            'Anterior', 'Posterior', 'Surface', 'Pygidium', 'Thorax', 'Axis',
            'Front', 'Dorsal', 'Fig', 'Figure', 'Type', 'Description',
            'Discussion', 'Remarks', 'Occurrence', 'Distribution',
            'Stratigraphic', 'Geographic', 'References', 'Contents',
            'Trilobita', 'Trilobitomorpha', 'Arthropoda', 'General',
            'Lower', 'Middle', 'Upper', 'Cambrian', 'Ordovician',
            'Silurian', 'Devonian', 'Carboniferous', 'Permian',
            'Systematic', 'Descriptions', 'Classification',
            'Paradoxides', 'Prepared', 'Directed', 'Edited',
            'This', 'That', 'These', 'Those', 'Each', 'Both',
            'Such', 'Some', 'Most', 'Many', 'Several',
            'Genae', 'Border', 'Shield', 'Furrow', 'Lobe',
            'Similar', 'Distinct', 'Rather', 'Short', 'Long',
            'Wide', 'Narrow', 'Small', 'Large', 'Very',
            'Smooth', 'Granular', 'Surface', 'Bears', 'Bearing',
            'Reaching', 'Not', 'Width', 'Length', 'Size',
            'Nearly', 'About', 'Half', 'Whole', 'Part',
            'Like', 'Fide', 'According', 'However',
        }

        if genus in skip_words:
            continue

        # Genus names should be 3+ chars, not end in common suffixes for non-genus words
        if len(genus) < 3:
            continue

        # Author should look like a person name (at least partially caps)
        if not any(c.isupper() for c in author):
            continue

        genera.append({
            'name': genus,
            'author': author,
            'year': int(year)
        })

    return genera


def extract_family_context(text):
    """Extract Family/Subfamily headers from OCR text."""
    contexts = []

    # Family header pattern
    fam_pattern = r'Family\s+([A-Z]{3,}(?:[A-Z]+)?(?:IDAE|idae))\s+([A-Za-z&\s\.]+?),?\s*(1[789]\d{2})'
    for m in re.finditer(fam_pattern, text):
        contexts.append({
            'rank': 'family',
            'name': m.group(1),
            'author': m.group(2).strip(),
            'year': int(m.group(3)),
            'pos': m.start()
        })

    # Subfamily header pattern
    subfam_pattern = r'Subfamily\s+([A-Z]{3,}(?:[A-Z]+)?(?:INAE|inae))\s+([A-Za-z&\s\.]+?),?\s*(1[789]\d{2})'
    for m in re.finditer(subfam_pattern, text):
        contexts.append({
            'rank': 'subfamily',
            'name': m.group(1),
            'author': m.group(2).strip(),
            'year': int(m.group(3)),
            'pos': m.start()
        })

    return sorted(contexts, key=lambda x: x['pos'])


def main():
    pdf_path = "data/Treatise 1959.pdf"

    # Systematic descriptions: O172-O525
    # PDF page offset: O-page + 20 ≈ PDF page (O172 = ~PDF 192)
    # Actually from our tests: PDF page 192 = O173
    # So offset is about +19 (O_page + 19 = PDF_page) or PDF 191 = O172
    start_pdf_page = 191  # O172
    end_pdf_page = 545    # O525 + some buffer

    print(f"OCR processing pages {start_pdf_page}-{end_pdf_page} from {pdf_path}")
    print(f"This will take a while (~350 pages at 300 DPI)...")

    all_genera = []
    all_contexts = []
    page_texts = {}

    for page_num, text in ocr_pages(pdf_path, start_pdf_page, end_pdf_page, dpi=300, batch_size=10):
        page_texts[page_num] = text

        # Extract genera from this page
        genera = extract_genera_from_text(text)
        for g in genera:
            g['page'] = page_num
        all_genera.extend(genera)

        # Extract family/subfamily context
        contexts = extract_family_context(text)
        for c in contexts:
            c['page'] = page_num
        all_contexts.extend(contexts)

    # Deduplicate genera (same name appearing on multiple pages, e.g., figures)
    seen = set()
    unique_genera = []
    for g in all_genera:
        key = g['name']
        if key not in seen:
            seen.add(key)
            unique_genera.append(g)

    # Save raw results
    output = {
        'source': 'Treatise on Invertebrate Paleontology, Part O (1959)',
        'method': 'Tesseract OCR at 300 DPI',
        'pages_processed': f'{start_pdf_page}-{end_pdf_page}',
        'total_genera_found': len(unique_genera),
        'total_raw_matches': len(all_genera),
        'family_headers_found': len(all_contexts),
        'genera': unique_genera,
        'family_headers': all_contexts,
    }

    output_path = 'data/treatise_1959_genera_ocr.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\nResults saved to {output_path}")
    print(f"Unique genera found: {len(unique_genera)}")
    print(f"Raw matches (before dedup): {len(all_genera)}")
    print(f"Family/subfamily headers found: {len(all_contexts)}")

    # Show first 30 genera as sample
    print(f"\nFirst 30 genera:")
    for g in unique_genera[:30]:
        print(f"  {g['name']} {g['author']}, {g['year']} (p.{g['page']})")


if __name__ == '__main__':
    main()
