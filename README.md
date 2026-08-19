# Pre-commit tutorial

> This repo is a read-only template maintained by the Permafrost org. Do not
> commit or push changes to it directly. Use the template to create your own
> copy and do all your work there.

This tutorial walks through setting up and running pre-commit hooks on a
Permafrost PoC project. You will start with broken delivery artifacts, run
the hooks, fix what cannot be auto-fixed, and end with a clean commit.

> **Scope:** This tutorial is about code hygiene only. The delivery artifacts
> are intentionally broken for learning purposes and are not meant to be run
> against a real Snowflake environment.
>
> **Estimated time:** 30 minutes.

---

## What this repo contains

```
precommit-tutorial/
  .pre-commit-config.yaml       # Hook configuration
  README.md                     # This file
  delivery/
    python/
      transform.py              # Python script with formatting and debug violations
    sql/
      01_create_objects.sql     # SQL script with style and naming violations
    notebooks/
      analysis.ipynb            # Notebook with outputs, placeholders, and credentials
  scripts/
    check_naming.py             # Custom hook: flags bad object names in SQL
    check_temp_objects.py       # Custom hook: flags debug code across all file types
```

---

## What each hook does

| Hook | Auto-fixes | Flags only |
|---|---|---|
| `sqlfluff-fix` | Casing, indentation, trailing whitespace | `SELECT *`, unfixable rules |
| `sqlfluff-lint` | - | Any remaining SQL violations after fix |
| `black` | All Python formatting | - |
| `isort` | Import ordering in Python files | - |
| `nbstripout` | Strips cell outputs and execution counts | - |
| `nbqa-black` | Python formatting in notebook cells | - |
| `nbqa-isort` | Import ordering in notebook cells | - |
| `nbqa-flake8` | - | Unused imports in notebook cells |
| `check-naming` | - | Bad object names in SQL (e.g. `_v2`, `tmp_`, `_final`) |
| `check-temp-objects` | - | Debug code, hardcoded paths, credentials |

Hooks run in the order listed above.

All hooks are configured in `.pre-commit-config.yaml` at the repo root. You
can add new hooks, remove ones you do not need, adjust file filters, change
tool versions, or add arguments to any hook by editing that file. The custom
hooks in `scripts/` can also be extended - for example, adding new bad name
patterns to `check_naming.py` or new debug code patterns to
`check_temp_objects.py`.

---

## How pre-commit works

Pre-commit runs hooks automatically every time you run `git commit`. It only
scans files that are staged, so you must run `git add` before committing or
the hooks will report "no files to check" and skip.

The first commit in a new repo triggers hook environment setup. Pre-commit
downloads and installs each hook's dependencies into an internal cache. This
only happens once and can take a minute. Subsequent commits are faster.

When a hook fails, the commit is blocked. You will see an error message
explaining what the hook found. Some hooks also rewrite files automatically
as part of the check. When that happens, the commit is still blocked because
the files changed after you staged them. You need to stage the rewritten files
and commit again.

The general cycle is:

1. `git add .` to stage your files.
2. `git commit` to trigger the hooks.
3. If hooks auto-fix files, `git add .` again and retry the commit.
4. If hooks flag manual violations, fix them, `git add .`, and retry the commit.
5. Repeat until all hooks pass and the commit goes through.

> **NOTE:** If you need to bypass the hooks entirely for a single commit, use:
>
>```bash
>git commit -m "your message" --no-verify
>```
>
>Use this sparingly. It skips all checks and should only be used when you
>intentionally need to commit something that would otherwise fail, like the
>broken tutorial artifacts in this repo.

---

## Prerequisites

You need Python 3.11+ and Git. If you do not have Python 3.11+, install it
from [python.org](https://www.python.org/downloads/) before continuing.

---

## Step 0: Create your own copy from the template

This repo is a GitHub template. Do not clone it directly. Create your own
copy first and do all your work there.

1. Go to `https://github.com/permafrost/precommit-tutorial`.
2. Click "Use this template" and select "Create a new repository".
3. Set yourself or your personal account as the owner and give the repo a name.
4. Clone your new repo locally and cd into it:

```bash
git clone https://github.com/<your-account>/<your-repo-name>.git
cd <your-repo-name>
```

All steps from here on are run from inside your cloned repo.

---

## Step 1: Set up a virtual environment

A virtual environment keeps the tools for this project separate from your
system Python. Pick one of the two approaches below.

### Option A: Python native venv

```bash
python -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate
pip install pre-commit
```

### Option B: uv (recommended)

uv is faster than pip and handles both the environment and package installs
in one tool. Install it if you do not have it:

```bash
curl -Ls https://astral.sh/uv/install.sh | sh
```

Create and activate the environment, then install pre-commit:

```bash
uv venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate
uv pip install pre-commit
```

> **NOTE:** You need to activate the environment every time you open a new terminal
> session before running any `pre-commit` commands.

---

## Step 2: Install the hooks

Run this once from the repo root. It reads `.pre-commit-config.yaml` and
registers each hook into `.git/hooks/` so they fire automatically on every
`git commit`. Pre-commit also downloads and caches the environment for each
hook the first time it runs - this can take a minute but only happens once.

```bash
pre-commit install
```

---

## Step 3: Run hooks across all files

Run all hooks across all files at once:

```bash
pre-commit run --all-files
```

You will see output from every hook. The following hooks rewrite files
automatically: `sqlfluff-fix`, `black`, `isort`, `nbstripout`, `nbqa-black`,
and `nbqa-isort`. The remaining hooks flag violations that need manual fixes,
including `nbqa-flake8` which flags unused imports in notebook cells.
Run it a second time after the auto-fixes to see only what remains:

```bash
pre-commit run --all-files
```

> **Note:** You can also target a single file if you want to focus on one
> thing at a time:
> ```bash
> pre-commit run --files delivery/sql/01_create_objects.sql
> ```

---

## Step 4: Fix the remaining violations by hand

Work through each file below. Fix everything in one file before moving to the
next.

### 01_create_objects.sql

**`sqlfluff-lint`** flagged one violation that `sqlfluff-fix` could not rewrite:

- `SELECT *` in the view definition. Replace it with an explicit column list:

```sql
CREATE OR REPLACE VIEW vw_orders AS
    SELECT
        order_id,
        customer_id,
        order_date,
        amount,
        status
    FROM stg_orders
    WHERE status = 'COMPLETE';
```

**`check-naming`** flagged three bad object names:

- `stg_orders_v2` has a version suffix `_v2`. Rename it to `stg_orders`.
- `vw_orders_final` has a banned suffix `_final`. Rename it to `vw_orders`.
- `tmp_order_summary` has a banned prefix `tmp_`. Rename it to `order_summary`.

Update every reference to each name in the file.

**`check-temp-objects`** flagged a block of four consecutive commented-out lines
above the view definition. Remove the block entirely. Do not replace it with a
single long comment line as `sqlfluff-lint` will flag it for exceeding the line
length limit.

---

### transform.py

**`check-temp-objects`** flagged four issues:

- A block of four or more consecutive commented-out lines at the top of the
  file. Remove the block.

- `print()` calls throughout the file. Replace them with `logging`. Add
  `import logging` at the top of the file and replace each call like this:

  ```python
  # before
  print("loading data from table: " + table_name)

  # after
  import logging

  logging.basicConfig(level=logging.INFO)
  logger = logging.getLogger(__name__)

  logger.info("loading data from table: %s", table_name)
  ```

- A `# HACK` comment. Remove the comment and the workaround, or fix the
  underlying issue.

- A hardcoded Snowflake account URL and password in the `__main__` block.
  Remove the hardcoded values. On Permafrost projects, connection params come
  from a Snowflake CLI connection. See `SNOWCLI_SETUP.md` for setup
  instructions.

---

### analysis.ipynb

**`check-temp-objects`** flagged `print()` calls in cells 1 and 2. Notebooks
are exploratory so `print()` is allowed, but `check-temp-objects` flags them
as a reminder to review before delivery. Remove them if the output is not
needed, or leave them if the cell output is intentional.

**`nbqa-flake8`** flagged unused imports in cell 1. `json` and `os` are
imported but never used. Remove them.

---

## Step 5: Confirm everything passes and commit

Once each file passes on its own, do a final check across all files together:

```bash
pre-commit run --all-files
```

If everything passes, stage and commit:

```bash
git add .
git commit -m "initial delivery artifacts"
```

The hooks fire one more time on the staged files. All of them should pass and
the commit goes through.