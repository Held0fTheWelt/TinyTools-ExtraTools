# Docify — inline source explain task (PEP 8 comments)

**Language:** Same canonical policy as [`docs/dev/contributing.md`](../../docs/dev/contributing.md#repository-language) — generated **comments** are **English** only; this task adds **procedure** only.

## Purpose

Use the **second Docify CLI** in one of two ways: **PEP 8 block comments** (`#` lines, correct indentation, wrapped width) for a **chosen source range** (for example a dense `if` / `return` block), or a **Google-style function docstring draft** for a single `--function` (summary, `Args:`, `Returns:` with a `Type:` line and indented body, wrapped to 72 characters per docstring line). Neither mode bulk-rewrites the tree; replace TODO prose by hand before merge.

## Preconditions

- Repository root as current working directory (or pass `--repo-root`).
- Python 3.14.x (`ast.unparse` for condition snippets in dry-run output).

## Procedure

1. **Pick a range** — one function body or explicit `--start-line` / `--end-line` (1-based, inclusive).

2. **Dry-run** — review proposed `#` blocks:

   ```bash
   python "./'fy'-suites/docify/tools/python_docstring_synthesize.py" \\
     --file path/to/your_module.py \\
     --start-line 50 --end-line 85
   ```

   Or derive the span from a function name:

   ```bash
   python "./'fy'-suites/docify/tools/python_docstring_synthesize.py" \\
     --file path/to/your_module.py \\
     --function your_callable
   ```

3. **Refine wording** — edit the printed comments for accuracy; the tool emits **two short sentences** per statement where useful (still AST-based; verify against behaviour).

4. **Apply** — when satisfied, repeat with `--apply` (still review `git diff`).

5. **Optional: Google docstring draft** — for one function name (same CLI):

   ```bash
   python "./'fy'-suites/docify/tools/python_docstring_synthesize.py" \\
     --file path/to/your_module.py \\
     --function your_callable \\
     --emit-google-docstring
   ```

   Replace TODO lines with accurate prose, then write with `--apply-docstring`. Validate with a narrow audit root, for example
   `python "./'fy'-suites/docify/tools/python_documentation_audit.py" --root path/to/package --google-docstring-audit --exit-zero`.

6. **Docstrings backlog** — use [`documentation-audit-task.md`](documentation-audit-task.md) for tree-wide missing-docstring counts; use `--google-docstring-audit` when checking layout on symbols that already have text.

7. **Cursor sync** — if you edited [`superpowers/`](superpowers/) router skills, run `python "./'fy'-suites/docify/tools/sync_docify_skills.py"` and commit `.cursor/skills/` updates (see root [`AGENTS.md`](../../AGENTS.md)).

## Completion

The slice is done when comments match real behavior and style checks (for example `ruff`) pass on touched files.

## References

- Inline comment CLI: ``'fy'-suites/docify/tools/python_docstring_synthesize.py`` (`--help`).
- Docstring backlog CLI: ``'fy'-suites/docify/tools/python_documentation_audit.py``.
- Repository language: [`docs/dev/contributing.md`](../../docs/dev/contributing.md#repository-language).
