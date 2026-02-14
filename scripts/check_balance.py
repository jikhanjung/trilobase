
import sys

def check_balance(file_path):
    unbalanced_lines = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f, 1):
            s_open = line.count('[')
            s_close = line.count(']')
            p_open = line.count('(')
            p_close = line.count(')')

            if s_open != s_close or p_open != p_close:
                unbalanced_lines.append(f"Line {i}: {line.strip()}")
    return unbalanced_lines

if __name__ == '__main__':
    file_to_check = 'data/trilobite_genus_list.txt'
    
    # Path to the current directory is passed as an argument by the tool, but for script execution,
    # it's usually relative to where the script is run. Assume it's in the same directory.

    unbalanced = check_balance(file_to_check)
    if unbalanced:
        print("Found unbalanced brackets or parentheses in the following lines:")
        for line in unbalanced:
            print(line)
    else:
        print("All brackets and parentheses are balanced.")

