import re

def is_plausible_family(name):
    """Check if a string is a plausible family name."""
    if not name:
        return False
    # Must be at least 3 chars long
    if len(name) < 3:
        return False
    # Should not contain brackets or periods
    if '[' in name or '.' in name:
        return False
    # Should not be a time period abbreviation (all caps, 2-5 letters)
    if re.match(r'^[A-Z]{2,5}$', name):
        return False
    # Should mostly be letters, but can contain ?
    if not re.match(r'^[A-Z\?]+$', name, re.IGNORECASE):
        return False
    return True

def main():
    families = set()
    with open('trilobite_genus_list.txt', 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            fields = line.split(';')
            
            if len(fields) >= 2:
                # The family is likely the second to last field
                potential_family = fields[-2].strip()
                
                if is_plausible_family(potential_family):
                    families.add(potential_family)

    with open('/home/jikhanjung/.gemini/tmp/9ab5c556c3b91c41cf630161e311e17cae018ba30d81ee0422c042979bed0f96/extracted_families_plausible.txt', 'w', encoding='utf-8') as f:
        for family in sorted(list(families)):
            f.write(family + '\n')

if __name__ == '__main__':
    main()