# AGENTS.md - Development Guide for playwrightmd

This guide provides AI coding assistants with essential commands, patterns, and conventions for working in the playwrightmd codebase.

**Quick reference**: Build/run commands • Safety rules • Architecture map • Core functions

---

## Safety Checklist

Before any operation:

- Prefer non-destructive actions; inspect inputs and outputs first
- Use `--no-js` for faster, safer fetches when JS rendering is not required
- Avoid writing output files unless explicitly requested
- Validate CLI args and selectors before changing defaults
- Keep network access minimal; only fetch when required

## NEVER Do These

- Commit code changes unless explicitly requested
- Add new dependencies without a clear need
- Bypass the content cleaning pipeline without a strong reason
- Remove anti-detection protections without replacing them
- Hardcode environment-specific paths

## ALWAYS Do These

- Keep changes minimal and readable
- Update CLI parser and `main()` together when adding options
- Maintain the Input Detection → Fetching → Cleaning → Markdown pipeline
- Explain non-obvious logic with concise English comments
- Prefer simplest approach that preserves current behavior

---

## Quick Reference

### Setup / Install
```bash
uv sync
uv run playwright install chromium
```

### Run Commands
```bash
# URL mode
uv run playwrightmd https://example.com

# File mode
uv run playwrightmd path/to/file.html

# Stdin mode
echo '<html><body><p>Test</p></body></html>' | uv run playwrightmd
```

### Common Flags
```bash
# Target a specific element
uv run playwrightmd https://example.com --selector "article"

# Raw HTML output
uv run playwrightmd https://example.com --raw

# Fast mode (no JS rendering)
uv run playwrightmd https://example.com --no-js
```

---

## Architecture Quick Map

```
playwrightmd/
├── src/
│   └── playwrightmd/
│       └── __init__.py      # All core code (single module)
├── tests/                   # Automated tests
│   ├── test_markdown_detection.py
│   └── test_main_function.py
├── pyproject.toml           # Project config and dependencies
├── uv.lock                  # Locked dependencies
├── pytest.ini               # pytest configuration
├── README.md                # User documentation
├── LICENSE                  # MIT license
├── .python-version          # Python 3.13
└── .gitignore
```

**Decision Tree**:

- Input detection → `detect_input_type()`
- HTML fetching → `get_html_content()` → `fetch_with_playwright()` or `render_local_html()` or HTTP fetch
- Content cleaning → `clean_html()`
- Markdown conversion → `html_to_markdown()`
- Output → `write_output()`

### Language Stack
- **Python**: Single-module CLI tool

---

## Code Style Guidelines

### Python
- Prefer small, single-purpose functions
- Keep I/O at the edges (`main()`, `get_html_content()`, `write_output()`)
- Avoid new global state
- Keep exceptions explicit and actionable

### Comments
- English only
- Explain "why" not "what"
- Add only when logic is non-obvious

---

## Key Functions

- `main()`: CLI entry point, orchestrates pipeline
- `create_parser()`: CLI argument definitions
- `detect_input_type()`: URL/file/stdin detection
- `get_html_content()`: Routes to fetchers (returns tuple: content, is_markdown)
- `is_markdown_file()`: Detects markdown files by extension
- `is_markdown_content_type()`: Detects markdown Content-Type headers
- `fetch_with_playwright()`: JS-rendered fetcher
- `render_local_html()`: Local HTML rendering
- `clean_html()`: Content extraction heuristics
- `html_to_markdown()`: Markdown conversion
- `write_output()`: File/stdout output

---

## Testing Strategy

### Automated Tests
The project uses pytest for automated testing. To run tests:

```bash
# Install dev dependencies
uv sync

# Run all tests
uv run pytest tests/ -v

# Run with coverage report
uv run pytest tests/ --cov=playwrightmd
```

Test coverage includes:
- Input detection logic
- Markdown file/URL detection
- HTML to Markdown conversion
- CLI argument handling

### Manual Validation
For manual testing of core functionality:

```bash
# Standard HTML to Markdown
uv run playwrightmd https://example.com

# Markdown file (should pass through unchanged)
uv run playwrightmd https://raw.githubusercontent.com/openai/openai-python/refs/heads/main/api.md

# Local markdown file
uv run playwrightmd test.md

# HTML file mode
echo '<html><body><p>Test</p></body></html>' > /tmp/test.html
uv run playwrightmd /tmp/test.html

# Stdin mode
echo '<html><body><p>Test</p></body></html>' | uv run playwrightmd

# Target a specific element
uv run playwrightmd https://example.com --selector "article"

# Raw HTML output
uv run playwrightmd https://example.com --raw

# Fast mode (no JS rendering)
uv run playwrightmd https://example.com --no-js
```

---

## Common Development Tasks

### Adding a CLI Option
1. Update `create_parser()`
2. Thread the option through `main()`
3. Add logic in the relevant function
4. Manual test with a real URL and a local file

### Changing Content Extraction
1. Update `clean_html()` heuristics
2. Validate `<main>`, `<article>`, and role-based fallbacks
3. Verify output on a JS-heavy and static page

### Modifying Browser Behavior
1. Update `fetch_with_playwright()` launch/context options
2. Verify headless/headed behavior
3. Confirm anti-detection protections still work

---

## Common Issues

- Browser not found → `uv run playwright install chromium`
- Timeout errors → Increase `--timeout` or use `--wait-until domcontentloaded`
- Missing content → Use `--wait-until networkidle` or `--wait-for` selector
- Bot detection → Try `--proxy-url` or custom `--user-agent`
- Wrong content extracted → Use `--selector` to target main element

---

## Communication Style

- Be concise and technical
- Explain safety implications upfront
- Provide file:line references for code locations
- Suggest validation steps when changes affect output

---

## Resources

- Code: `src/playwrightmd/__init__.py`
- Docs: `README.md`
- Config: `pyproject.toml`, `uv.lock`
