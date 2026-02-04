def main():
    # Read the list of unknown families
    with open('/home/jikhanjung/.gemini/tmp/9ab5c556c3b91c41cf630161e311e17cae018ba30d81ee0422c042979bed0f96/unknown_families_in_genus_list_final_clean.txt', 'r', encoding='utf-8') as f:
        unknown_families = f.read().splitlines()

    # Clean the list
    cleaned_families = set()
    for family in unknown_families:
        # Remove leading/trailing ?, strip whitespace
        cleaned_name = family.strip().replace('?', '')
        if cleaned_name and cleaned_name.upper() == cleaned_name: # Ensure it's a plausible family name (all caps)
            cleaned_families.add(cleaned_name)
            
    # Add NEKTASPIDA
    cleaned_families.add('NEKTASPIDA')

    # Read existing families
    with open('trilobite_family_list.txt', 'r', encoding='utf-8') as f:
        existing_families = set(line.strip() for line in f) # Strip newlines when reading existing

    # Find the new families to add
    new_families = sorted(list(cleaned_families - existing_families))

    # Append new families to the list
    with open('trilobite_family_list.txt', 'a', encoding='utf-8') as f:
        for family in new_families:
            f.write('\n' + family) # Ensure Python writes the newline
            
    print(f"Added {len(new_families)} new families to trilobite_family_list.txt")

if __name__ == '__main__':
    main()