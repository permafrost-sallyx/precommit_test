"""
check_naming.py

Checks SQL files for object names that violate Permafrost naming conventions.
Flags names containing version suffixes, temp prefixes, or vague labels.

Used as a pre-commit hook and in CI.
"""

import re
import sys

# Patterns that indicate a name is not ready for delivery.
# Each entry is (regex, plain English message).
BAD_NAME_PATTERNS = [
    (r"\b\w*_v\d+\b", "has a version suffix (_v2, _v3, ...)"),
    (r"\b\w*_final\b", "has a banned suffix (_final)"),
    (r"\b\w*_new\b", "has a banned suffix (_new)"),
    (r"\b\w*_old\b", "has a banned suffix (_old)"),
    (r"\btemp_\w*\b", "has a banned prefix (temp_)"),
    (r"\btmp_\w*\b", "has a banned prefix (tmp_)"),
    (r"\btest_\w*\b", "has a banned prefix (test_)"),
    (r"\bfix_\w*\b", "has a banned prefix (fix_)"),
    (r"\b\w*_test\b", "has a banned suffix (_test)"),
    (r"\b\w*_temp\b", "has a banned suffix (_temp)"),
    (r"\b\w*_copy\b", "has a banned suffix (_copy)"),
    (r"\b\w*_bak\b", "has a banned suffix (_bak)"),
]

# SQL keywords that introduce object names
OBJECT_KEYWORDS = [
    "TABLE",
    "VIEW",
    "SCHEMA",
    "DATABASE",
    "PROCEDURE",
    "FUNCTION",
    "TASK",
    "STAGE",
    "PIPE",
    "STREAM",
    "DYNAMIC TABLE",
    "WAREHOUSE",
    "ROLE",
]

OBJECT_KEYWORD_PATTERN = re.compile(
    r"\b(?:CREATE\s+(?:OR\s+REPLACE\s+)?|DEFINE\s+)"
    r"(?:" + "|".join(OBJECT_KEYWORDS) + r")\s+"
    r"(\S+)",
    re.IGNORECASE,
)

BAD_PATTERNS_COMPILED = [
    (re.compile(p, re.IGNORECASE), msg) for p, msg in BAD_NAME_PATTERNS
]


def check_file(filepath: str) -> list[str]:
    errors = []
    with open(filepath, "r") as f:
        content = f.read()

    for match in OBJECT_KEYWORD_PATTERN.finditer(content):
        name = match.group(1).strip(";").strip()
        for pattern, message in BAD_PATTERNS_COMPILED:
            if pattern.search(name):
                line_num = content[: match.start()].count("\n") + 1
                errors.append(f"{filepath}:{line_num} - '{name}' {message}")
                break
    return errors


def main():
    files = sys.argv[1:]
    if not files:
        print("No files to check.")
        sys.exit(0)

    all_errors = []
    for filepath in files:
        all_errors.extend(check_file(filepath))

    if all_errors:
        print("Naming convention violations found:")
        for error in all_errors:
            print(f"  {error}")
        print(
            "\nObject names must describe what the object contains, not when or "
            "how it was created. Rename the object before submitting for review."
        )
        sys.exit(1)

    print(f"Naming check passed for {len(files)} file(s).")
    sys.exit(0)


if __name__ == "__main__":
    main()
