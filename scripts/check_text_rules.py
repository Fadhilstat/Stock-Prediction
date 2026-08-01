"""Check project text for characters that are not allowed by the style guide."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {".py", ".md", ".toml", ".yaml", ".yml", ".txt"}
FORBIDDEN = {"\u2014": "em dash"}
IGNORED_PARTS = {".git", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache"}


def main() -> int:
    violations: list[str] = []

    for path in PROJECT_ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        if any(part in IGNORED_PARTS for part in path.parts):
            continue

        text = path.read_text(encoding="utf-8")
        for character, name in FORBIDDEN.items():
            for line_number, line in enumerate(text.splitlines(), start=1):
                if character in line:
                    relative_path = path.relative_to(PROJECT_ROOT)
                    violations.append(f"{relative_path}:{line_number}: contains {name}")

    if violations:
        print("Text rule violations found:")
        for violation in violations:
            print(violation)
        return 1

    print("Text rules passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
