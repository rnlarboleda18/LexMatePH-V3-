import sys

def check_balance(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    stack = []
    lines = content.split('\n')
    
    for i, line in enumerate(lines):
        for j, char in enumerate(line):
            if char in '{[(':
                stack.append((char, i+1, j+1))
            elif char in '}])':
                if not stack:
                    print(f"Extra closing '{char}' at line {i+1}, col {j+1}")
                    print(f"Context: {line.strip()}")
                    return
                top, l, c = stack.pop()
                if (char == '}' and top != '{') or \
                   (char == ']' and top != '[') or \
                   (char == ')' and top != '('):
                    print(f"Mismatched '{char}' at line {i+1}, col {j+1}. Expected closing for '{top}' from line {l}, col {c}")
                    print(f"Context: {line.strip()}")
                    return

    if stack:
        print(f"Unclosed brackets left:")
        for char, l, c in stack:
            print(f"'{char}' from line {l}, col {c}")
            print(f"Context: {lines[l-1].strip()}")
    else:
        print("SUCCESS: All brackets balanced!")

if __name__ == '__main__':
    check_balance(r"c:\Users\rnlar\.gemini\antigravity\scratch\LexMatePH v3\src\frontend\src\features\lexify\LexifyDashboard.jsx")
