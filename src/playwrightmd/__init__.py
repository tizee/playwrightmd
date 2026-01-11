#!/usr/bin/env python3
"""
playwrightmd - Convert HTML to Markdown using Playwright

Supports three input modes:
  - URL: playwrightmd https://example.com -o output.md
  - File: playwrightmd page.html -o output.md
  - Stdin: cat page.html | playwrightmd -o output.md
"""

import argparse
import sys
from enum import Enum
from pathlib import Path
from typing import TextIO

from bs4 import BeautifulSoup
from markdownify import markdownify as md
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout


class InputType(Enum):
    URL = "url"
    FILE = "file"
    STDIN = "stdin"


def detect_input_type(input_arg: str | None) -> InputType:
    """Detect whether input is a URL, file path, or stdin."""
    if input_arg is None or input_arg == "-":
        return InputType.STDIN
    if input_arg.startswith(("http://", "https://")):
        return InputType.URL
    if Path(input_arg).exists():
        return InputType.FILE
    # Assume URL if it looks like a domain
    if "." in input_arg and not input_arg.startswith("/"):
        return InputType.URL
    raise ValueError(f"Cannot determine input type for: {input_arg}")


DEFAULT_USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

WAIT_UNTIL_CHOICES = ["load", "domcontentloaded", "networkidle", "commit"]


def fetch_with_playwright(
    url: str,
    timeout: int = 30000,
    wait_for: str | None = None,
    user_agent: str | None = None,
    proxy_url: str | None = None,
    headless: bool = True,
    wait_until: str = "networkidle",
) -> str:
    """Fetch URL using Playwright and return rendered HTML."""
    with sync_playwright() as p:
        launch_args = {
            "headless": headless,
            "args": ["--disable-blink-features=AutomationControlled"],
        }

        if proxy_url:
            launch_args["proxy"] = {"server": proxy_url}

        browser = p.chromium.launch(**launch_args)

        # Create context with realistic browser fingerprint
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=user_agent or DEFAULT_USER_AGENT,
            locale="en-US",
            timezone_id="America/New_York",
        )

        page = context.new_page()

        # Remove webdriver detection
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        """)

        try:
            page.goto(url, timeout=timeout, wait_until=wait_until)

            # Additional wait for networkidle if using faster initial load
            if wait_until in ["commit", "domcontentloaded", "load"]:
                try:
                    page.wait_for_load_state("networkidle", timeout=timeout)
                except PlaywrightTimeout:
                    pass  # Continue with what we have

            if wait_for:
                page.wait_for_selector(wait_for, timeout=timeout)

            html = page.content()
        finally:
            context.close()
            browser.close()

    return html


def render_local_html(
    html_content: str,
    timeout: int = 30000,
    headless: bool = True,
    wait_until: str = "networkidle",
) -> str:
    """Render local HTML with Playwright to execute any JavaScript."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page()

        try:
            page.set_content(html_content, timeout=timeout, wait_until=wait_until)
            rendered_html = page.content()
        finally:
            browser.close()

    return rendered_html


def clean_html(html: str, selector: str | None = None) -> str:
    """Remove scripts, styles, and other non-content elements."""
    soup = BeautifulSoup(html, "lxml")

    # If user specified a selector, use it directly
    if selector:
        main_content = soup.select_one(selector)
        if not main_content:
            raise ValueError(f"Selector '{selector}' not found in page")
    else:
        # Remove unwanted elements first
        for tag in soup.find_all(["script", "style", "noscript", "iframe", "svg"]):
            tag.decompose()

        # Remove navigation elements (sidebars, navs, etc.)
        for tag in soup.find_all(["nav", "aside"]):
            tag.decompose()

        # Remove elements with common sidebar/nav class patterns
        for tag in soup.find_all(class_=lambda c: c and any(
            pattern in " ".join(c).lower() for pattern in
            ["sidebar", "side-bar", "sidenav", "side-nav", "toc", "table-of-contents", "menu", "navigation"]
        ) if c else False):
            tag.decompose()

        # Remove elements with sidebar/nav role
        for tag in soup.find_all(attrs={"role": lambda r: r in ["navigation", "complementary", "menu"]}):
            tag.decompose()

        # Remove header/footer
        for tag in soup.find_all(["header", "footer"]):
            tag.decompose()

        # Remove comments
        from bs4 import Comment
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()

        # Try to find main content area
        main_content = (
            soup.find("main")
            or soup.find("article")
            or soup.find(attrs={"role": "main"})
            or soup.find("div", class_=lambda c: c and any(
                pattern in " ".join(c).lower() for pattern in ["content", "article", "post", "entry", "main"]
            ) if c else False)
            or soup.body
            or soup
        )

    return str(main_content)


def html_to_markdown(html: str, strip_tags: list[str] | None = None, selector: str | None = None) -> str:
    """Convert HTML to Markdown using markdownify."""
    cleaned = clean_html(html, selector=selector)

    # Convert to markdown with sensible defaults
    markdown = md(
        cleaned,
        heading_style="atx",
        bullets="-",
        code_language_callback=lambda el: el.get("class", [""])[0].replace("language-", "") if el.get("class") else None,
        strip=strip_tags or [],
    )

    # Clean up excessive whitespace
    lines = markdown.split("\n")
    cleaned_lines = []
    prev_empty = False

    for line in lines:
        is_empty = not line.strip()
        if is_empty and prev_empty:
            continue
        cleaned_lines.append(line.rstrip())
        prev_empty = is_empty

    return "\n".join(cleaned_lines).strip() + "\n"


def is_markdown_file(path: str) -> bool:
    """Check if file path has a markdown extension."""
    markdown_extensions = {'.md', '.markdown', '.mdown', '.mkdn', '.mkd', '.mdwn', '.mdtxt', '.mdtext', '.rmd'}
    return any(path.lower().endswith(ext) for ext in markdown_extensions)


def is_markdown_content_type(content_type: str | None) -> bool:
    """Check if Content-Type header indicates markdown."""
    if not content_type:
        return False
    return any(ctype in content_type.lower() for ctype in ['markdown', 'text/markdown', 'text/x-markdown'])


def get_html_content(
    input_arg: str | None,
    input_type: InputType,
    timeout: int = 30000,
    wait_for: str | None = None,
    no_js: bool = False,
    user_agent: str | None = None,
    proxy_url: str | None = None,
    headless: bool = True,
    wait_until: str = "networkidle",
) -> tuple[str, bool]:
    """Get HTML content based on input type. Returns (content, is_markdown)."""
    if input_type == InputType.URL:
        url = input_arg
        # Add https:// if no protocol specified
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        # Check if URL looks like a markdown file based on extension
        if is_markdown_file(url):
            # Use simple HTTP fetch since it's a raw file
            import urllib.request
            req = urllib.request.Request(url, headers={"User-Agent": user_agent or DEFAULT_USER_AGENT})
            with urllib.request.urlopen(req, timeout=timeout // 1000) as response:
                content_type = response.getheader("Content-Type")
                # Even if extension suggests markdown, verify Content-Type
                if is_markdown_content_type(content_type) or is_markdown_file(url):
                    return (response.read().decode("utf-8"), True)
            return (response.read().decode("utf-8"), False)

        if no_js:
            import urllib.request
            req = urllib.request.Request(url, headers={"User-Agent": user_agent or DEFAULT_USER_AGENT})
            with urllib.request.urlopen(req, timeout=timeout // 1000) as response:
                return (response.read().decode("utf-8"), False)
        return fetch_with_playwright(
            url,
            timeout=timeout,
            wait_for=wait_for,
            user_agent=user_agent,
            proxy_url=proxy_url,
            headless=headless,
            wait_until=wait_until,
        ), False

    elif input_type == InputType.FILE:
        # Check if file is markdown
        if is_markdown_file(input_arg):
            return (Path(input_arg).read_text(encoding="utf-8"), True)
        html = Path(input_arg).read_text(encoding="utf-8")
        if no_js:
            return (html, False)
        return (render_local_html(html, timeout=timeout, headless=headless, wait_until=wait_until), False)

    elif input_type == InputType.STDIN:
        html = sys.stdin.read()
        if no_js:
            return (html, False)
        return (render_local_html(html, timeout=timeout, headless=headless, wait_until=wait_until), False)

    raise ValueError(f"Unknown input type: {input_type}")


def write_output(markdown: str, output: str | None) -> None:
    """Write markdown to file or stdout."""
    if output:
        Path(output).write_text(markdown, encoding="utf-8")
    else:
        print(markdown, end="")


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser."""
    parser = argparse.ArgumentParser(
        prog="playwrightmd",
        description="Convert HTML to Markdown using Playwright for JS-rendered content",
        epilog="""
Examples:
  playwrightmd https://example.com -o output.md
  playwrightmd page.html -o output.md
  cat page.html | playwrightmd -o output.md
  curl -s https://example.com | playwrightmd
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "input",
        nargs="?",
        help="URL or file path (omit or use '-' for stdin)",
    )

    parser.add_argument(
        "-o", "--output",
        help="Output file (default: stdout)",
    )

    parser.add_argument(
        "--wait-for",
        metavar="SELECTOR",
        help="CSS selector to wait for before extracting content",
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=30000,
        metavar="MS",
        help="Page load timeout in milliseconds (default: 30000)",
    )

    parser.add_argument(
        "--no-js",
        action="store_true",
        help="Skip Playwright rendering, use simple HTTP fetch",
    )

    parser.add_argument(
        "-s", "--selector",
        metavar="CSS",
        help="CSS selector for main content (e.g., 'article', '.content', '#main')",
    )

    parser.add_argument(
        "--user-agent",
        metavar="UA",
        help="Custom User-Agent string",
    )

    parser.add_argument(
        "--proxy-url",
        metavar="URL",
        help="Proxy URL for requests (e.g., 'http://proxy:8080')",
    )

    parser.add_argument(
        "--headless",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Run browser in headless mode (default: True, use --no-headless for headed)",
    )

    parser.add_argument(
        "--wait-until",
        choices=WAIT_UNTIL_CHOICES,
        default="networkidle",
        help="When to consider navigation succeeded (default: networkidle)",
    )

    parser.add_argument(
        "--ignore-robots-txt",
        action="store_true",
        help="Ignore robots.txt restrictions (Playwright ignores by default)",
    )

    parser.add_argument(
        "--raw",
        action="store_true",
        help="Output raw HTML without converting to Markdown",
    )

    return parser


def main() -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    try:
        input_type = detect_input_type(args.input)

        content, is_markdown = get_html_content(
            args.input,
            input_type,
            timeout=args.timeout,
            wait_for=args.wait_for,
            no_js=args.no_js,
            user_agent=args.user_agent,
            proxy_url=args.proxy_url,
            headless=args.headless,
            wait_until=args.wait_until,
        )

        if args.raw:
            output = content
        elif is_markdown:
            # Skip conversion, output raw markdown
            output = content
        else:
            output = html_to_markdown(content, selector=args.selector)

        write_output(output, args.output)

        return 0

    except PlaywrightTimeout as e:
        print(f"Error: Page load timed out after {args.timeout}ms", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
