import re

def main():
    genus_counts = {}
    with open('data/trilobite_genus_list.txt', 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            line = line.strip()
            if not line:
                continue

            # Extract genus name: assumed to be the first word before a space or a bracket
            match = re.match(r'^([A-Z][a-z]+)\s.*', line)
            if match:
                genus_name = match.group(1).strip()
                genus_counts[genus_name] = genus_counts.get(genus_name, 0) + 1
            else:
                # Handle cases where the line might start differently, e.g., with ?
                # Or if it's a very short line without a clear genus name.
                # For now, let's just print these to inspect.
                # print(f"Warning: Could not extract genus from line {i+1}: {line}")
                pass

    duplicates_found = False
    for genus, count in genus_counts.items():
        if count > 1:
            print(f"Duplicate genus entry: {genus} (appears {count} times)")
            duplicates_found = True

    if not duplicates_found:
        print("No duplicate genus entries found.")

if __name__ == '__main__':
    main()
