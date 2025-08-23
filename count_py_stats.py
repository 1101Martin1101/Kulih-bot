from pathlib import Path
import sys

IGNORE_DIRS = {'__pycache__', 'venv', '.venv', 'env', '.env'}

def count_file(path: Path):
    text = path.read_text(encoding='utf-8', errors='replace')
    lines = len(text.splitlines())
    chars = len(text)
    return lines, chars

def main(root: Path):
    root = root.resolve()
    self_path = Path(__file__).resolve()
    total_lines = 0
    total_chars = 0
    files = []

    for p in root.rglob('*.py'):
        try:
            if p.resolve() == self_path:
                continue
        except Exception:
            continue
        # skip common virtualenvs / caches
        if any(part in IGNORE_DIRS for part in p.parts):
            continue
        lines, chars = count_file(p)
        files.append((p.relative_to(root), lines, chars))
        total_lines += lines
        total_chars += chars

    for rel, lines, chars in sorted(files):
        print(f"{rel}: {lines} řádků, {chars} znaků")
    print("-" * 40)
    print(f"Celkem: {total_lines} řádků, {total_chars} znaků")

if __name__ == "__main__":
    root_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    main(root_dir)