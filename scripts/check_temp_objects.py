"""
check_temp_objects.py

Checks SQL, Python, and notebook files in delivery/ for debug code,
commented-out blocks, hardcoded local paths, and personal credentials.

Rules per file type:
  .sql   - flags TODO (no colon), FIXME, HACK, DEBUG, commented-out blocks,
           hardcoded paths and credentials
  .py    - flags print(), TODO (no colon), FIXME, HACK, DEBUG,
           hardcoded paths and credentials
  .ipynb - flags hardcoded paths and credentials only
           print() is intentionally excluded - notebooks are exploratory

Used as a pre-commit hook and in CI.
"""

import json
import re
import sys
from pathlib import Path

# --- Pattern sets per file type ---

SQL_DEBUG_PATTERNS = [
    (r"--\s*TODO(?!:)", "TODO comment found (not a placeholder)"),
    (r"--\s*FIXME", "FIXME comment found"),
    (r"--\s*HACK", "HACK comment found"),
    (r"--\s*DEBUG", "DEBUG comment found"),
    (r"LIMIT\s+\d+\s*;?\s*--\s*temp", "temporary LIMIT found"),
    (r"C:\\Users\\", "hardcoded Windows local path found"),
    (r"/Users/[a-zA-Z]+/", "hardcoded macOS local path found"),
    (r"/home/[a-zA-Z]+/", "hardcoded Linux home path found"),
    (r"password\s*=\s*['\"][^'\"]+['\"]", "hardcoded password found"),
    (
        r"account\s*=\s*['\"][a-z0-9\-]+\.snowflakecomputing\.com['\"]",
        "hardcoded Snowflake account URL found",
    ),
]

PYTHON_DEBUG_PATTERNS = [
    (r"^\s*print\s*\(", "print() call found - use logging instead"),
    (r"#\s*TODO(?!:)", "TODO comment found (not a placeholder)"),
    (r"#\s*FIXME", "FIXME comment found"),
    (r"#\s*HACK", "HACK comment found"),
    (r"#\s*DEBUG", "DEBUG comment found"),
    (r"C:\\Users\\", "hardcoded Windows local path found"),
    (r"/Users/[a-zA-Z]+/", "hardcoded macOS local path found"),
    (r"/home/[a-zA-Z]+/", "hardcoded Linux home path found"),
    (r"password\s*=\s*['\"][^'\"]+['\"]", "hardcoded password found"),
    (
        r"account\s*=\s*['\"][a-z0-9\-]+\.snowflakecomputing\.com['\"]",
        "hardcoded Snowflake account URL found",
    ),
]

# print() intentionally excluded - notebooks are exploratory
NOTEBOOK_DEBUG_PATTERNS = [
    (r"C:\\Users\\", "hardcoded Windows local path found"),
    (r"/Users/[a-zA-Z]+/", "hardcoded macOS local path found"),
    (r"/home/[a-zA-Z]+/", "hardcoded Linux home path found"),
    (r"password\s*=\s*['\"][^'\"]+['\"]", "hardcoded password found"),
    (
        r"account\s*=\s*['\"][a-z0-9\-]+\.snowflakecomputing\.com['\"]",
        "hardcoded Snowflake account URL found",
    ),
]

SQL_DEBUG_PATTERNS_COMPILED = [
    (re.compile(p, re.IGNORECASE), msg) for p, msg in SQL_DEBUG_PATTERNS
]
PYTHON_DEBUG_PATTERNS_COMPILED = [
    (re.compile(p, re.IGNORECASE), msg) for p, msg in PYTHON_DEBUG_PATTERNS
]
NOTEBOOK_DEBUG_PATTERNS_COMPILED = [
    (re.compile(p, re.IGNORECASE), msg) for p, msg in NOTEBOOK_DEBUG_PATTERNS
]

# Commented-out block detection for SQL
COMMENTED_BLOCK_PATTERN = re.compile(
    r"((?:^\s*--(?!=)(?!-)[^\n]*\n){4,})", re.MULTILINE
)
SECTION_DIVIDER_PATTERN = re.compile(r"--\s*[=\-]{3,}", re.MULTILINE)

# Commented-out block detection for Python
PYTHON_COMMENTED_BLOCK_PATTERN = re.compile(r"((?:^\s*#[^\n]*\n){4,})", re.MULTILINE)


def check_sql_file(filepath: str) -> list[str]:
    errors = []
    with open(filepath, "r") as f:
        content = f.read()

    for line_num, line in enumerate(content.splitlines(), start=1):
        for pattern, message in SQL_DEBUG_PATTERNS_COMPILED:
            if pattern.search(line):
                errors.append(f"{filepath}:{line_num} - {message}")

    for match in COMMENTED_BLOCK_PATTERN.finditer(content):
        block = match.group(0)
        if SECTION_DIVIDER_PATTERN.search(block):
            continue
        lines_in_block = [l.strip() for l in block.splitlines() if l.strip()]
        if all(re.match(r"--\s*TODO:", l, re.IGNORECASE) for l in lines_in_block):
            continue
        errors.append(
            f"{filepath} - contains a block of 4 or more consecutive commented-out "
            "lines. Remove old code before submitting for review."
        )

    return errors


def check_python_file(filepath: str) -> list[str]:
    errors = []
    with open(filepath, "r") as f:
        content = f.read()

    for line_num, line in enumerate(content.splitlines(), start=1):
        for pattern, message in PYTHON_DEBUG_PATTERNS_COMPILED:
            if pattern.search(line):
                errors.append(f"{filepath}:{line_num} - {message}")

    for match in PYTHON_COMMENTED_BLOCK_PATTERN.finditer(content):
        block = match.group(0)
        lines_in_block = [l.strip() for l in block.splitlines() if l.strip()]
        # Skip blocks that are all TODO: placeholders or section dividers
        if all(
            re.match(r"#\s*TODO:", l, re.IGNORECASE) or re.match(r"#\s*[=\-]{3,}", l)
            for l in lines_in_block
        ):
            continue
        errors.append(
            f"{filepath} - contains a block of 4 or more consecutive commented-out "
            "lines. Remove old code before submitting for review."
        )

    return errors


def check_notebook_file(filepath: str) -> list[str]:
    errors = []
    try:
        with open(filepath, "r") as f:
            nb = json.load(f)
    except json.JSONDecodeError:
        errors.append(f"{filepath} - could not parse notebook as JSON")
        return errors

    cells = nb.get("cells", [])
    for cell_idx, cell in enumerate(cells):
        source = "".join(cell.get("source", []))
        cell_type = cell.get("cell_type", "unknown")

        for line_num, line in enumerate(source.splitlines(), start=1):
            for pattern, message in NOTEBOOK_DEBUG_PATTERNS_COMPILED:
                if pattern.search(line):
                    errors.append(
                        f"{filepath} - cell {cell_idx + 1} ({cell_type}), "
                        f"line {line_num}: {message}"
                    )

        if cell.get("outputs"):
            errors.append(
                f"{filepath} - cell {cell_idx + 1} has outputs. "
                "Run nbstripout before committing."
            )

        if cell.get("execution_count") is not None:
            errors.append(
                f"{filepath} - cell {cell_idx + 1} has a non-null execution_count. "
                "Run nbstripout before committing."
            )

    return errors


def main():
    files = sys.argv[1:]
    if not files:
        print("No files to check.")
        sys.exit(0)

    all_errors = []
    for filepath in files:
        ext = Path(filepath).suffix.lower()
        if ext == ".sql":
            all_errors.extend(check_sql_file(filepath))
        elif ext == ".py":
            all_errors.extend(check_python_file(filepath))
        elif ext == ".ipynb":
            all_errors.extend(check_notebook_file(filepath))

    if all_errors:
        print("Debug or temporary code found:")
        for error in all_errors:
            print(f"  {error}")
        print(
            "\nRemove debug code, commented-out blocks, and hardcoded paths "
            "before submitting for review."
        )
        sys.exit(1)

    print(f"Temp/debug check passed for {len(files)} file(s).")
    sys.exit(0)


if __name__ == "__main__":
    main()
