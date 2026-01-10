# playwrightmd - Agent Documentation

> HTML-to-Markdown converter using Playwright for JavaScript-rendered content

## Quick Overview

**playwrightmd** is a Python CLI tool that converts web pages to clean Markdown. It uses Playwright to render JavaScript-heavy pages (SPAs, React apps, etc.) and extracts clean content by removing navigation, sidebars, and boilerplate.

### Key Capabilities
- Renders JavaScript content via headless Chromium
- Bypasses bot detection (Cloudflare, etc.)
- Smart content extraction (removes nav, sidebars, headers, footers)
- Supports URL, local file, or stdin input
- CSS selector targeting for specific content areas

## Project Structure

```
playwrightmd/
├── src/
│   └── playwrightmd/
│       └── __init__.py      # All core code (single module)
├── pyproject.toml           # Project config and dependencies
├── uv.lock                  # Locked dependencies
├── README.md                # User documentation
├── LICENSE                  # MIT license
├── .python-version          # Python 3.13
└── .gitignore
```

## Architecture

### Single-Module Design

The entire implementation is in `/Users/tizee/projects/project-AI/tools/webfetch.tizee/src/playwrightmd/__init__.py` (~400 lines). This is intentional for a focused CLI tool.

### Data Flow

```
Input Detection → HTML Fetching → Content Cleaning → Markdown Conversion → Output
```

### Core Components

| Function | Purpose |
|----------|---------|
| `main()` | CLI entry point, orchestrates pipeline |
| `detect_input_type()` | Determines if input is URL, file, or stdin |
| `get_html_content()` | Routes to appropriate fetcher based on input type |
| `fetch_with_playwright()` | Fetches URL via headless Chromium with anti-detection |
| `render_local_html()` | Renders local HTML with Playwright for JS execution |
| `clean_html()` | Removes non-content elements (nav, scripts, etc.) |
| `html_to_markdown()` | Converts cleaned HTML to Markdown via markdownify |
| `write_output()` | Writes to file or stdout |
| `create_parser()` | Defines CLI arguments |

### Input Types

```python
class InputType(Enum):
    URL = "url"      # https://... or domain.com
    FILE = "file"    # Local .html file
    STDIN = "stdin"  # Piped input or '-'
```

### Key Dependencies

- **playwright**: Browser automation for JS rendering
- **beautifulsoup4 + lxml**: HTML parsing and content extraction
- **markdownify**: HTML to Markdown conversion

## CLI Options

```
playwrightmd [input] [options]

Arguments:
  input                   URL, file path, or '-' for stdin

Output:
  -o, --output FILE       Output file (default: stdout)
  --raw                   Output raw HTML instead of Markdown

Content Selection:
  -s, --selector CSS      CSS selector for main content
  --wait-for SELECTOR     Wait for element before extracting

Browser Control:
  --timeout MS            Page load timeout (default: 30000)
  --headless/--no-headless  Browser visibility (default: headless)
  --wait-until MODE       Navigation condition: load, domcontentloaded,
                          networkidle (default), commit

Network:
  --user-agent UA         Custom User-Agent
  --proxy-url URL         Proxy server
  --no-js                 Skip Playwright, use HTTP fetch
```

## Content Extraction Heuristics

### Elements Removed
- Scripts, styles, noscript, iframe, svg
- nav, aside, header, footer
- Elements with sidebar/navigation classes or roles
- HTML comments

### Content Priority
1. `<main>` tag
2. `<article>` tag
3. `[role="main"]` element
4. Div with content-related classes (.content, .article, .post, .entry, .main)
5. `<body>` fallback

## Anti-Detection Measures

The tool includes several measures to avoid bot detection:
- Realistic User-Agent string (Chrome on macOS)
- Standard viewport (1920x1080)
- Removes `navigator.webdriver` flag
- Disables automation detection features
- Uses networkidle wait strategy by default

## Development Commands

```bash
# Setup
uv sync
uv run playwright install chromium

# Run directly
uv run playwrightmd https://example.com

# Install globally
uv tool install .
playwrightmd https://example.com
```

## Entry Points

- **CLI**: `playwrightmd` command (defined in pyproject.toml `[project.scripts]`)
- **Code**: `main()` function in `src/playwrightmd/__init__.py`

## Extending the Tool

When modifying this codebase:

1. **Adding new CLI options**: Update `create_parser()` and thread through `main()`
2. **Changing content extraction**: Modify `clean_html()` heuristics
3. **Adding input types**: Extend `InputType` enum and `get_html_content()`
4. **Modifying Markdown output**: Adjust `html_to_markdown()` markdownify options
5. **Browser behavior**: Update `fetch_with_playwright()` launch/context options

## Testing Approach

No test suite currently. To test manually:

```bash
# URL mode
playwrightmd https://example.com

# File mode
echo '<html><body><p>Test</p></body></html>' > test.html
playwrightmd test.html

# Stdin mode
echo '<html><body><p>Test</p></body></html>' | playwrightmd

# With selector
playwrightmd https://example.com --selector "article"

# Raw HTML output
playwrightmd https://example.com --raw

# Fast mode (no JS)
playwrightmd https://example.com --no-js
```

## Common Issues

| Issue | Solution |
|-------|----------|
| Browser not found | Run `uv run playwright install chromium` |
| Timeout errors | Increase `--timeout` or use `--wait-until domcontentloaded` |
| Missing content | Try `--wait-until networkidle` or add `--wait-for` selector |
| Bot detection | Use `--proxy-url` or custom `--user-agent` |
| Wrong content extracted | Use `-s/--selector` to target specific element |
