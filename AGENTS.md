# AGENTS.md - Development Quick Reference

Quick start guide for AI agents working on playwrightmd.

---

## Safety Rules

**NEVER:**
- Commit code unless explicitly requested
- Add dependencies without clear need
- Remove anti-detection protections without replacement
- Hardcode environment-specific paths

**ALWAYS:**
- Keep changes minimal and readable
- Update CLI parser and `main()` together when adding options
- Maintain Input Detection → Fetching → Cleaning → Markdown pipeline
- Explain non-obvious logic with concise English comments

---

## Quick Start

```bash
# Setup
uv sync
uv run playwright install chromium

# Run tests
uv run pytest tests/ -v

# Run tool
uv run playwrightmd https://example.com
uv run playwrightmd page.html output.md
```

---

## Architecture

```
playwrightmd/
├── src/playwrightmd/__init__.py   # Single module with all code
├── tests/                          # pytest tests
├── pyproject.toml                  # Project config
└── uv.lock                         # Locked dependencies
```

**Pipeline:**
`detect_input_type()` → `get_html_content()` → `clean_html()` → `html_to_markdown()` → `write_output()`

---

## Key Functions

| Function | Purpose |
|----------|---------|
| `main()` | CLI entry, orchestrates pipeline |
| `create_parser()` | CLI argument definitions |
| `detect_input_type()` | URL/file/stdin detection |
| `get_html_content()` | Routes to fetchers (returns content, is_markdown) |
| `fetch_with_playwright()` | JS-rendered fetcher |
| `clean_html()` | Content extraction heuristics |
| `html_to_markdown()` | Markdown conversion |
| `truncate_markdown_links()` | URL truncation |
| `write_output()` | File/stdout output |

---

## Code Style

- Small, single-purpose functions
- Keep I/O at edges (`main()`, `get_html_content()`, `write_output()`)
- No new global state
- English comments for non-obvious logic

---

## Adding a CLI Option

1. Add to `create_parser()`
2. Thread through `main()`
3. Add logic in relevant function
4. Add test + manual test

---

## Resources

- Code: `src/playwrightmd/__init__.py`
- Tests: `tests/`
- Docs: `README.md`
