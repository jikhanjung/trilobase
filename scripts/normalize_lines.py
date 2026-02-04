#!/usr/bin/env python3
"""
Normalize trilobite_genus_list.txt to have one genus per line.

Steps:
1. Remove soft hyphens (U+00AD) and join words
2. Merge lines that are continuations of previous line
3. Split lines that contain multiple genera
4. Remove empty lines and garbage lines
"""

import re
import sys

def is_continuation_line(line):
    """Check if line is a continuation of the previous entry."""
    stripped = line.strip()
    if not stripped:
        return False
    # Starts with [ (j.s.s., j.o.s., etc.)
    if stripped.startswith('['):
        return True
    # Starts with lowercase letter
    if stripped[0].islower():
        return True
    # Starts with certain patterns that indicate continuation
    if re.match(r'^(fide|and|or|sensu|emend)', stripped, re.IGNORECASE):
        return True
    # Starts with location/region pattern (continuation of previous entry)
    # e.g., "France; PALAEOLENIDAE; LCAM."
    if re.match(r'^[A-Z][a-z]+[,;]?\s*(?:[A-Z]{3,}|[A-Z][a-z]+)', stripped):
        # But not if it looks like a genus entry (Genus AUTHOR, YEAR)
        if not re.match(r'^[A-Z][a-z]+\s+[A-Z][A-Z]+.*\d{4}', stripped):
            # Check if it looks like location; FAMILY; PERIOD pattern
            if re.match(r'^[A-Z][a-zA-Z\s,]+;\s*[A-Z]+', stripped):
                return True
    # Starts with author name pattern (continuation)
    # e.g., "R. RICHTER, 1909]"
    if re.match(r'^[A-Z]\.\s*[A-Z]+', stripped):
        return True
    # Ends with ] or starts with punctuation
    if stripped.endswith('].') and len(stripped) < 20:
        return True
    # Geographic/stratigraphic continuation
    if re.match(r'^(?:N\.|S\.|E\.|W\.|NW|NE|SW|SE)\s', stripped):
        return True
    return False

def is_garbage_line(line):
    """Check if line contains only garbage characters."""
    stripped = line.strip()
    if not stripped:
        return True
    # Only contains weird characters (broken encoding)
    if re.match(r'^[\s˘ˇ˙˝­\t\r\n]+$', stripped):
        return True
    # Very short line with no alphabetic content
    if len(stripped) < 5 and not re.search(r'[A-Za-z]', stripped):
        return True
    # Line with only whitespace characters
    if not stripped or stripped.isspace():
        return True
    # Line that doesn't contain any Latin letters (likely encoding garbage)
    if not re.search(r'[A-Za-z]{3,}', stripped):
        return True
    return False

def find_genus_split_points(line):
    """Find positions where a new genus entry starts within a line."""
    splits = []

    # Simpler approach: find temporal codes followed by period and new genus
    # Temporal codes: LCAM, MCAM, UCAM, LORD, MORD, UORD, LSIL, USIL, LDEV, MDEV, UDEV,
    #                 MISS, PENN, LPERM, PERM, UPERM, CAM, ORD, SIL, DEV
    # Also: herein (for "fide AUTHOR, herein")

    # Pattern: temporal_code/herein followed by ]. or . then space and GenusName AUTHOR
    # GenusName = Capital + lowercase (at least 2)
    # AUTHOR = ALLCAPS (may have & , in, et al.)
    # Pattern captures: [temporal]. GenusName AUTHOR (rest doesn't matter for split point)

    pattern = r'(?:L?M?U?(?:CAM|ORD|SIL|DEV|PERM)|MISS|PENN|herein)\]?\.\s+([A-Z][a-z]{2,}\s+[A-Z][A-Z])'

    for match in re.finditer(pattern, line):
        pos = match.start(1)
        # Make sure we're not inside brackets at this position
        before = line[:match.start()]
        open_brackets = before.count('[') - before.count(']')
        if open_brackets == 0 and pos not in splits:
            splits.append(pos)

    # Pattern 2: ]. followed by space and GenusName AUTHOR
    pattern2 = r'\]\s*\.?\s+([A-Z][a-z]{2,}\s+[A-Z][A-Z])'

    for match in re.finditer(pattern2, line):
        pos = match.start(1)
        if pos not in splits:
            splits.append(pos)

    return sorted(splits)

def normalize_lines(input_file, output_file):
    with open(input_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Step 1: Remove soft hyphens and normalize
    cleaned_lines = []
    for line in lines:
        # Remove soft hyphen (U+00AD) and join the word
        line = line.replace('\u00ad', '')
        # Also handle other problematic characters
        line = line.replace('\t', ' ')
        cleaned_lines.append(line.rstrip())

    # Step 2: Merge continuation lines
    merged_lines = []
    current_line = ""

    for i, line in enumerate(cleaned_lines):
        if is_garbage_line(line):
            continue

        if is_continuation_line(line) and merged_lines:
            # Append to previous line
            if merged_lines:
                merged_lines[-1] = merged_lines[-1] + ' ' + line.strip()
        else:
            if line.strip():
                merged_lines.append(line.strip())

    # Step 3: Split lines with multiple genera (iteratively until no more splits)
    final_lines = []
    for line in merged_lines:
        segments_to_process = [line]

        while segments_to_process:
            current = segments_to_process.pop(0)
            splits = find_genus_split_points(current)

            if not splits:
                final_lines.append(current)
            else:
                # Split at the first position and re-queue the rest
                pos = splits[0]
                first_part = current[:pos].strip()
                rest_part = current[pos:].strip()

                if first_part:
                    final_lines.append(first_part)
                if rest_part:
                    # Re-queue the rest for potential further splitting
                    segments_to_process.insert(0, rest_part)

    # Write output
    with open(output_file, 'w', encoding='utf-8') as f:
        for line in final_lines:
            f.write(line + '\n')

    print(f"Input lines: {len(lines)}")
    print(f"Output lines: {len(final_lines)}")
    print(f"Removed garbage/empty lines: {len(lines) - len(cleaned_lines) + sum(1 for l in cleaned_lines if is_garbage_line(l))}")

if __name__ == '__main__':
    input_file = 'trilobite_genus_list.txt'
    output_file = 'trilobite_genus_list_normalized.txt'

    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    if len(sys.argv) > 2:
        output_file = sys.argv[2]

    normalize_lines(input_file, output_file)
