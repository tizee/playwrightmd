# playwrightmd

Convert HTML to Markdown using Patchright, a Playwright-compatible browser automation library. Handles JavaScript-rendered content, bypasses common bot detection, and extracts clean content from documentation sites.

## Features

- **[Cloudflare Markdown for Agents](https://developers.cloudflare.com/fundamentals/reference/markdown-for-agents/)**: Automatically fetches pre-converted markdown from Cloudflare-enabled sites (~80% token reduction, no browser needed)
- **FxTwitter API for X/Twitter**: Transparently fetches tweets and articles from x.com/twitter.com via FxTwitter API — bypasses anti-scraping without browser launch
- **HTTP prefetch with Patchright fallback**: Lightweight HTTP fetch first, Patchright only when JS rendering is needed
- **JavaScript rendering**: Uses Patchright to render SPAs and dynamic content
- **Bot detection bypass**: Handles Cloudflare and similar protections
- **YAML frontmatter**: Automatically extracts page metadata (title, author, published date, description) from Open Graph, JSON-LD, and meta tags — prepended as YAML frontmatter for structured agent consumption
- **Smart content extraction**: Advanced readability rules — removes sidebars, navigation, ads, metadata, and boilerplate using 600+ patterns
- **Auto-retry for SPA content**: Detects empty content from client-side rendered pages (Next.js, React) and automatically retries with `networkidle` wait strategy
- **Absolute URL resolution**: Converts relative links to absolute URLs in markdown output
- **Multiple input modes**: URL, local file, or stdin
- **CSS selector support**: Target specific content areas
- **Markdown detection**: Automatically skips conversion for raw markdown files/URLs
- **Link truncation**: Truncate long URLs in markdown links

## Installation

### Install from source with uv (recommended)

Install globally from a source checkout to run `playwrightmd` directly:

```bash
git clone https://github.com/tizee/playwrightmd.git
cd playwrightmd
uv tool install --force --upgrade .
```

Install patched Chromium the first time:

```bash
# macOS:
uv tool run --from . patchright install chromium

# Linux (includes system dependencies):
uv tool run --from . patchright install --with-deps chromium
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

# Install patched Chromium the first time
uv run patchright install chromium          # macOS
uv run patchright install --with-deps chromium  # Linux

# Run the tool
uv run playwrightmd https://example.com
```

## Usage

### URL mode

```bash
# Standard HTML to Markdown conversion
playwrightmd https://example.com output.md
playwrightmd https://example.com -o output.md
playwrightmd https://docs.python.org/3/tutorial/ python_tutorial.md

# Raw markdown URL (automatically skips conversion)
playwrightmd https://raw.githubusercontent.com/openai/openai-python/refs/heads/main/api.md openai_api.md
```

### File mode

```bash
# HTML to Markdown conversion
playwrightmd page.html output.md
playwrightmd page.html -o output.md
playwrightmd ./downloaded_page.html

# Local markdown file (passes through unchanged)
playwrightmd document.md unchanged.md
playwrightmd ./notes.markdown
```

### Stdin mode

```bash
cat page.html | playwrightmd output.md
cat page.html | playwrightmd -o output.md
curl -s https://example.com | playwrightmd > output.md
```

## Options

```
playwrightmd [input] [output] [options]

Arguments:
  input                   URL or file path (omit or use '-' for stdin)
  output                  Output file (optional, default: stdout)

Output:
  -o, --output FILE       Output file (alternative to positional argument)
  --raw                   Output raw HTML without Markdown conversion
  --no-frontmatter        Suppress YAML frontmatter in markdown output
  --truncate-link [N]     Truncate URLs longer than N display width
                          (default: 42 when flag is used)

Content Selection:
  -s, --selector CSS      CSS selector for main content
  --wait-for SELECTOR     Wait for element before extracting

Browser Control:
  --timeout MS            Page load timeout in ms (default: 30000)
  --headless              Run in headless mode (default: True)
  --no-headless           Run with visible browser window
  --wait-until MODE       Navigation success condition:
                          load, domcontentloaded (default), networkidle, commit

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

### Truncate long links

```bash
# Truncate URLs longer than 42 display width (default)
playwrightmd https://example.com --truncate-link

# Custom truncate length
playwrightmd https://example.com --truncate-link 30

# Output to file with truncated links
playwrightmd https://example.com output.md --truncate-link
```

**Note:** Uses `wcwidth` for proper Unicode/CJK character width calculation. A CJK character counts as 2 display width units.

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
2. **Markdown detection**: Automatically identifies if input is already a markdown file/URL
3. **HTTP prefetch** (URLs only): Lightweight fetch with `Accept: text/markdown, text/html` header. If the server returns markdown (e.g., Cloudflare Markdown for Agents), use it directly — no browser launched
4. **Playwright fallback** (URLs only): If prefetch returns HTML and JS rendering is needed, launches headless Chromium with anti-detection measures. Auto-retries with `networkidle` if content is empty
5. **Content extraction**: Removes scripts, styles, navigation, sidebars (for HTML only)
6. **Markdown conversion**: Uses markdownify with clean formatting (for HTML only)
7. **Metadata extraction**: Extracts title, author, published date, etc. from Open Graph, JSON-LD, and meta tags
8. **Frontmatter**: Prepends YAML frontmatter with extracted metadata (for URL inputs)

### Markdown Detection

playwrightmd automatically detects when input is already in markdown format and skips the conversion process entirely, preserving the original content. Detection works by:

- **File extensions**: Recognizes common markdown extensions: `.md`, `.markdown`, `.mdown`, `.mkdn`, `.mkd`, `.mdwn`, `.mdtxt`, `.mdtext`, `.rmd`
- **URL pattern matching**: Detects raw markdown files hosted on services like GitHub Raw
- **Content-Type headers**: Verifies markdown content type from HTTP responses

When markdown is detected:
- No HTML parsing or cleaning is performed
- No Playwright browser is launched (faster execution)
- The original markdown content is passed through unchanged

### Cloudflare Markdown for Agents

For sites with [Cloudflare Markdown for Agents](https://developers.cloudflare.com/fundamentals/reference/markdown-for-agents/) enabled, playwrightmd automatically receives pre-converted markdown via HTTP content negotiation — no browser launch needed.

```bash
# Cloudflare blog returns markdown directly (~27KB vs ~465KB HTML)
playwrightmd https://blog.cloudflare.com/markdown-for-agents/

# Cloudflare developer docs
playwrightmd https://developers.cloudflare.com/workers/
```

**How it works:**
- Every URL fetch starts with a lightweight HTTP prefetch that sends `Accept: text/markdown, text/html`
- If the server returns `Content-Type: text/markdown`, the content is used directly (Playwright is never launched)
- The `X-Markdown-Tokens` header, if present, is logged to stderr for token budget estimation
- If the server returns HTML, playwrightmd falls back to Playwright for JS rendering (unless `--no-js` is set)

**Benefits:**
- ~80% token reduction compared to HTML-to-markdown conversion
- Near-instant response (no browser startup overhead)
- Works transparently — no extra flags needed

### X/Twitter Support (FxTwitter API)

For x.com and twitter.com URLs, playwrightmd uses the [FxTwitter API](https://github.com/FixTweet/FxTwitter) to fetch content without triggering anti-scraping measures — no browser needed.

```bash
# Fetch a tweet
playwrightmd https://x.com/elonmusk/status/1234567890

# Fetch an X article
playwrightmd https://x.com/elonmusk/article/1234567890
```

**How it works:**
1. URL is detected as x.com or twitter.com with `/status/` or `/article/` path
2. Extracts username and tweet/article ID from URL
3. Calls `api.fxtwitter.com` API directly
4. Returns formatted markdown with frontmatter (author, source, etc.)
5. If API fails, falls back to Playwright

**Output includes:**
- Full tweet text with formatting (italic, mentions, links)
- Photos as markdown images
- Article content (headers, paragraphs, lists, code blocks)
- YAML frontmatter with author info

**Benefits:**
- No browser launch needed for x.com content
- Bypasses rate limiting and anti-scraping
- Works for both tweets and long-form articles
- Preserves formatting (italic, mentions, links)

### YAML Frontmatter

playwrightmd automatically extracts page metadata and prepends it as YAML frontmatter to the markdown output:

```yaml
---
title: "Can LLMs Be Computers?"
author: "Christos Tzamos"
published: "2026-03-11T00:00:00.000Z"
description: "We build a computer inside a transformer."
site: "Percepta"
source: "https://percepta.ai/blog/can-llms-be-computers"
image: "https://percepta.ai/blog/turing-hero-og.png"
---

## TL;DR
...
```

**Metadata sources** (priority order per field):

| Field | Sources (first non-empty wins) |
|-------|-------------------------------|
| title | `og:title` > `<title>` > JSON-LD `headline` > `twitter:title` |
| author | `article:author` > `meta[name=author]` > JSON-LD `author` |
| published | `article:published_time` > JSON-LD `datePublished` |
| description | `og:description` > `meta[name=description]` > JSON-LD > `twitter:description` |
| site | `og:site_name` > JSON-LD `publisher` |
| image | `og:image` |
| source | Always set from the input URL |

**Behavior:**
- Frontmatter is added for all URL-fetched HTML pages by default
- Only fields with values are included (no empty fields)
- Twitter/X posts already include frontmatter via FxTwitter API
- Cloudflare Markdown responses are passed through as-is (no frontmatter added)
- Use `--no-frontmatter` to suppress frontmatter output:

```bash
playwrightmd https://example.com --no-frontmatter
```

### Auto-retry for SPA/Next.js Pages

When Playwright fetches a page with `domcontentloaded` (the default) and the resulting markdown is empty, playwrightmd automatically retries with `networkidle`. This handles client-side rendered pages (Next.js, React, Vue) where content is injected by JavaScript hydration after the initial HTML loads.

```
domcontentloaded (fast) → empty? → retry with networkidle (thorough)
```

A hint is logged to stderr when retry occurs:

```
Content empty after domcontentloaded, retrying with networkidle…
```

This only triggers when:
- The default `domcontentloaded` strategy is used (not overridden by `--wait-until`)
- The extracted markdown content is empty or whitespace-only

### Navigation lifecycle (`--wait-until`)

The `--wait-until` option controls when Playwright considers the page "loaded" and extracts content:

```
commit ──→ domcontentloaded ──→ load ──→ networkidle
(fastest)    (default)                    (slowest)
```

| Mode | Triggered when | Best for |
|------|---------------|----------|
| `commit` | Navigation response received | Quick checks, simple pages |
| `domcontentloaded` | HTML parsed, DOM ready | Most websites (default) |
| `load` | All resources (images, CSS, JS) loaded | Traditional websites |
| `networkidle` | No network requests for 500ms | SPAs, JS-heavy sites |

**Examples:**

```bash
# Fast: just get the initial HTML
playwrightmd https://example.com --wait-until commit

# Default: wait for DOM ready (good balance of speed and completeness)
playwrightmd https://example.com --wait-until domcontentloaded

# Slow but thorough: wait for all network activity to settle
playwrightmd https://example.com --wait-until networkidle
```

**When to change from default:**
- Use `commit` for quick checks on simple static pages
- Use `networkidle` for React/Vue/Angular apps that load content via JavaScript
- If content is missing, try `networkidle` with a longer `--timeout`

### Anti-detection measures

- Realistic user agent and viewport
- Removes `navigator.webdriver` flag
- Disables automation detection features

### Content extraction heuristics

Content cleaning rules provide consistent, high-quality extraction:

**Removes:**
- Scripts, styles, noscript, iframes (except video embeds)
- Navigation, sidebars, headers, footers
- Ads, banners, promo content
- Comments sections, author bios
- Newsletter signups, social share buttons
- Hidden/visibility:hidden elements
- Print-only elements
- Tables of contents, tag lists
- Breadcrumbs, pagination

**Content detection:**
- Prioritized selectors: `#post`, `.post-content`, `article`, `main`, etc.
- Content scoring based on text density, paragraph count, link density
- Footnote and citation detection
- Heading normalization (H1 → H2, remove title-matching headings)

**URL handling:**
- Relative URLs converted to absolute using base URL
- Supports href, src, and srcset attributes
- Preserves video embeds (YouTube, Vimeo)

### Anti-detection measures

- Realistic user agent and viewport
- Removes `navigator.webdriver` flag
- Disables automation detection features
- Elements with sidebar/navigation classes
- Elements with navigation/complementary roles

Prioritizes content from:
- `<main>`, `<article>`, `[role="main"]`
- Divs with content-related classes

## Requirements

- Python 3.13+
- Patchright Chromium browser

## Browser Management

Patchright stores browsers in the Playwright-compatible **shared system cache**, not per-project:

| OS | Location |
|----|----------|
| macOS | `~/Library/Caches/ms-playwright/` |
| Linux | `~/.cache/ms-playwright/` |
| Windows | `%USERPROFILE%\AppData\Local\ms-playwright\` |

This means:
- Install browsers once, use everywhere (global tool, uvx, development all share the same browsers)
- No duplication across different Python environments
- Browser size: ~90MB for Chromium

If `playwrightmd` reports `Browser not found` even though `~/Library/Caches/ms-playwright/` already contains Chromium, the installed global tool environment may be using an older Patchright version that expects a different Chromium revision. Avoid downloading another old revision by upgrading/reinstalling the global tool environment:

```bash
cd /path/to/playwrightmd
uv tool install --force --upgrade .
playwrightmd https://example.com
```

### `--with-deps` flag (Linux)

On Linux, Chromium requires system libraries (`libnss3`, `libatk1.0`, `libcups2`, etc.). Use `--with-deps` to install them automatically:

```bash
patchright install --with-deps chromium
```

| OS | `--with-deps` needed? |
|----|----------------------|
| macOS | No - system has required libs |
| Windows | No - bundled with browser |
| Linux (Ubuntu/Debian) | Yes - installs apt packages |
| Linux (Docker) | Yes - containers are minimal |

```bash
# Inspect browser cache directories
ls ~/Library/Caches/ms-playwright/   # macOS
ls ~/.cache/ms-playwright/           # Linux

# Remove all cached browsers (if needed)
rm -rf ~/Library/Caches/ms-playwright/
```

## License

MIT
