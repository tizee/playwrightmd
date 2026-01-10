# playwrightmd

Convert HTML to Markdown using Playwright. Handles JavaScript-rendered content, bypasses common bot detection, and extracts clean content from documentation sites.

## Features

- **JavaScript rendering**: Uses Playwright to render SPAs and dynamic content
- **Bot detection bypass**: Handles Cloudflare and similar protections
- **Smart content extraction**: Removes sidebars, navigation, and boilerplate
- **Multiple input modes**: URL, local file, or stdin
- **CSS selector support**: Target specific content areas

## Installation

### Global installation with uv (recommended)

Install globally to run `playwrightmd` directly:

```bash
# From local directory
cd playwrightmd
uv tool install .

# Install Playwright browsers (required once)
# macOS:
uv tool run --from . playwright install chromium

# Linux (includes system dependencies):
uv tool run --from . playwright install --with-deps chromium
```

Then run directly:

```bash
playwrightmd https://example.com -o output.md
```

To uninstall:

```bash
uv tool uninstall playwrightmd
```

### Using uvx (no installation)

Run directly without installing:

```bash
uvx --from . playwrightmd https://example.com -o output.md
```

### Development setup

```bash
# Clone or navigate to project directory
cd playwrightmd

# Install dependencies
uv sync

# Install Playwright browsers
uv run playwright install chromium          # macOS
uv run playwright install --with-deps chromium  # Linux

# Run the tool
uv run playwrightmd https://example.com
```

## Usage

### URL mode

```bash
playwrightmd https://example.com -o output.md
playwrightmd https://docs.python.org/3/tutorial/ -o python_tutorial.md
```

### File mode

```bash
playwrightmd page.html -o output.md
playwrightmd ./downloaded_page.html
```

### Stdin mode

```bash
cat page.html | playwrightmd -o output.md
curl -s https://example.com | playwrightmd > output.md
```

## Options

```
playwrightmd [input] [options]

Arguments:
  input                   URL or file path (omit or use '-' for stdin)

Output:
  -o, --output FILE       Output file (default: stdout for piping)
  --raw                   Output raw HTML without Markdown conversion

Content Selection:
  -s, --selector CSS      CSS selector for main content
  --wait-for SELECTOR     Wait for element before extracting

Browser Control:
  --timeout MS            Page load timeout in ms (default: 30000)
  --headless              Run in headless mode (default: True)
  --no-headless           Run with visible browser window
  --wait-until MODE       Navigation success condition:
                          load, domcontentloaded, networkidle (default), commit

Network:
  --user-agent UA         Custom User-Agent string
  --proxy-url URL         Proxy URL (e.g., 'http://proxy:8080')
  --no-js                 Skip Playwright, use simple HTTP fetch
  --ignore-robots-txt     Ignore robots.txt (Playwright ignores by default)

  -h, --help              Show help message
```

## Examples

### Basic URL fetch

```bash
playwrightmd https://platform.openai.com/docs/api-reference/chat
```

### Target specific content

```bash
playwrightmd https://example.com --selector "article.main-content"
playwrightmd https://blog.example.com --selector "#post-body"
```

### Wait for dynamic content

```bash
playwrightmd https://spa-app.com --wait-for ".content-loaded"
```

### Fast mode (no JavaScript)

```bash
playwrightmd https://simple-page.com --no-js
```

### Longer timeout for slow sites

```bash
playwrightmd https://slow-site.com --timeout 60000
```

### Piping to other commands

```bash
# Output to stdout by default (no -o)
playwrightmd https://example.com | head -20

# Pipe to grep
playwrightmd https://docs.python.org | grep "tutorial"

# Pipe from curl
curl -s https://example.com | playwrightmd > example.md

# Chain with other tools
playwrightmd https://example.com | wc -l
```

### Custom User-Agent

```bash
playwrightmd https://example.com --user-agent "MyBot/1.0"
```

### Using a proxy

```bash
playwrightmd https://example.com --proxy-url "http://proxy.example.com:8080"
playwrightmd https://example.com --proxy-url "socks5://localhost:1080"
```

### Visible browser (for debugging)

```bash
playwrightmd https://example.com --no-headless
```

### Fast loading modes

```bash
# Don't wait for all resources
playwrightmd https://example.com --wait-until domcontentloaded

# Fastest, but may miss dynamic content
playwrightmd https://example.com --wait-until commit
```

### Raw HTML output (as HTML downloader)

```bash
# Download rendered HTML (after JS execution)
playwrightmd https://spa-app.com --raw -o page.html

# Pipe raw HTML to other tools
playwrightmd https://example.com --raw | htmlq 'article'

# Compare with curl (playwrightmd renders JS, curl doesn't)
playwrightmd https://react-app.com --raw -o rendered.html
curl -s https://react-app.com -o static.html
```

## How It Works

1. **Input detection**: Determines if input is URL, file, or stdin
2. **Playwright rendering**: Launches headless Chromium with anti-detection measures
3. **Content extraction**: Removes scripts, styles, navigation, sidebars
4. **Markdown conversion**: Uses markdownify with clean formatting

### Navigation lifecycle (`--wait-until`)

The `--wait-until` option controls when Playwright considers the page "loaded" and extracts content:

```
commit ──→ domcontentloaded ──→ load ──→ networkidle
(fastest)                                  (slowest, default)
```

| Mode | Triggered when | Best for |
|------|---------------|----------|
| `commit` | Navigation response received | Quick checks, simple pages |
| `domcontentloaded` | HTML parsed, DOM ready | Static HTML pages |
| `load` | All resources (images, CSS, JS) loaded | Traditional websites |
| `networkidle` | No network requests for 500ms | SPAs, JS-heavy sites (default) |

**Examples:**

```bash
# Fast: just get the initial HTML
playwrightmd https://example.com --wait-until commit

# Medium: wait for DOM but not all resources
playwrightmd https://example.com --wait-until domcontentloaded

# Slow but thorough: wait for all network activity to settle (default)
playwrightmd https://example.com --wait-until networkidle
```

**When to change from default:**
- Use `commit` or `domcontentloaded` for static sites to speed up fetching
- Stick with `networkidle` (default) for React/Vue/Angular apps that load content via JavaScript
- If content is missing, try `networkidle` with a longer `--timeout`

### Anti-detection measures

- Realistic user agent and viewport
- Removes `navigator.webdriver` flag
- Disables automation detection features
- Waits for network idle state

### Content extraction heuristics

Automatically removes:
- `<script>`, `<style>`, `<noscript>`, `<iframe>`, `<svg>`
- `<nav>`, `<aside>`, `<header>`, `<footer>`
- Elements with sidebar/navigation classes
- Elements with navigation/complementary roles

Prioritizes content from:
- `<main>`, `<article>`, `[role="main"]`
- Divs with content-related classes

## Requirements

- Python 3.13+
- Playwright Chromium browser

## Browser Management

Playwright stores browsers in a **shared system cache**, not per-project:

| OS | Location |
|----|----------|
| macOS | `~/Library/Caches/ms-playwright/` |
| Linux | `~/.cache/ms-playwright/` |
| Windows | `%USERPROFILE%\AppData\Local\ms-playwright\` |

This means:
- Install browsers once, use everywhere (global tool, uvx, development all share the same browsers)
- No duplication across different Python environments
- Browser size: ~90MB for Chromium

### `--with-deps` flag (Linux)

On Linux, Chromium requires system libraries (`libnss3`, `libatk1.0`, `libcups2`, etc.). Use `--with-deps` to install them automatically:

```bash
playwright install --with-deps chromium
```

| OS | `--with-deps` needed? |
|----|----------------------|
| macOS | No - system has required libs |
| Windows | No - bundled with browser |
| Linux (Ubuntu/Debian) | Yes - installs apt packages |
| Linux (Docker) | Yes - containers are minimal |

```bash
# Check installed browsers
ls ~/Library/Caches/ms-playwright/   # macOS
ls ~/.cache/ms-playwright/           # Linux

# Remove all Playwright browsers (if needed)
rm -rf ~/Library/Caches/ms-playwright/
```

## License

MIT
