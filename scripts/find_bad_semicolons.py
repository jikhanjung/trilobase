import re

def main():
    with open('trilobite_genus_list_structural_fixed.txt', 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            line = line.strip()
            if not line:
                continue

            # Split by semicolon
            fields = line.split(';')

            if len(fields) > 3:
                # Find the main part of the line (before any notes)
                note_start = line.find('[')
                if note_start == -1:
                    # If there's no note, but more than 3 fields, it's a problem
                    print(f"Line {i+1}: {line}")
                    continue

                # The part of the line before the note
                main_part = line[:note_start]

                # Count semicolons in the main part
                main_semicolons = main_part.count(';')

                # If there are more than 2 semicolons in the main part, it's a problem
                if main_semicolons > 2:
                    print(f"Line {i+1}: {line}")

if __name__ == '__main__':
    main()
