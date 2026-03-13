from urllib.error import HTTPError
from unittest.mock import MagicMock, call, patch

import pytest

from playwrightmd import (
    InputType,
    is_text_file,
    get_html_content,
    http_prefetch,
    is_markdown_file,
    is_text_content_type,
    is_markdown_content_type,
)


class TestMarkdownDetection:
    def test_is_markdown_file(self):
        # Test various markdown extensions
        assert is_markdown_file("test.md")
        assert is_markdown_file("test.markdown")
        assert is_markdown_file("test.mdown")
        assert is_markdown_file("test.mkdn")
        assert is_markdown_file("test.mkd")
        assert is_markdown_file("test.mdwn")
        assert is_markdown_file("test.mdtxt")
        assert is_markdown_file("test.mdtext")
        assert is_markdown_file("test.rmd")

        # Test case insensitivity
        assert is_markdown_file("test.MD")
        assert is_markdown_file("TEST.MARKDOWN")

        # Test non-markdown files
        assert not is_markdown_file("test.html")
        assert not is_markdown_file("test.txt")
        assert not is_markdown_file("test.pdf")
        assert not is_markdown_file("test.jpg")
        assert not is_markdown_file("test")  # no extension

    def test_is_markdown_content_type(self):
        # Test positive cases
        assert is_markdown_content_type("text/markdown")
        assert is_markdown_content_type("text/x-markdown")
        assert is_markdown_content_type("application/markdown")
        assert is_markdown_content_type("text/plain; charset=utf-8; format=markdown")

        # Test case insensitivity
        assert is_markdown_content_type("TEXT/MARKDOWN")
        assert is_markdown_content_type("text/Markdown")

        # Test negative cases
        assert not is_markdown_content_type("text/html")
        assert not is_markdown_content_type("text/plain")
        assert not is_markdown_content_type("application/json")
        assert not is_markdown_content_type(None)
        assert not is_markdown_content_type("")

    def test_local_markdown_file_detection(self, tmp_path):
        # Create a test markdown file
        md_file = tmp_path / "test.md"
        md_content = "# Test\n## Subtitle\n\nContent"
        md_file.write_text(md_content, encoding="utf-8")

        # Test that it's detected as markdown
        content, is_markdown, base_url = get_html_content(
            str(md_file),
            InputType.FILE,
            no_js=True,
        )

        assert is_markdown is True
        assert content == md_content

    def test_local_html_file_detection(self, tmp_path):
        # Create a test HTML file
        html_file = tmp_path / "test.html"
        html_content = "<html><body><h1>Test</h1><p>Content</p></body></html>"
        html_file.write_text(html_content, encoding="utf-8")

        # Test that it's NOT detected as markdown
        content, is_markdown, base_url = get_html_content(
            str(html_file),
            InputType.FILE,
            no_js=True,
        )

        assert is_markdown is False
        assert content == html_content


class TestTextDetection:
    def test_is_text_file(self):
        # Test plain text files
        assert is_text_file("test.txt")
        assert is_text_file("README.txt")
        assert is_text_file("test.TEXT")

        # Test JSON files
        assert is_text_file("data.json")
        assert is_text_file("config.JSON")

        # Test XML files
        assert is_text_file("data.xml")
        assert is_text_file("feed.XML")

        # Test YAML files
        assert is_text_file("config.yaml")
        assert is_text_file("config.yml")
        assert is_text_file("data.YAML")

        # Test CSV files
        assert is_text_file("data.csv")
        assert is_text_file("export.CSV")

        # Test TOML files
        assert is_text_file("config.toml")
        assert is_text_file("pyproject.TOML")

        # Test config files
        assert is_text_file("config.ini")
        assert is_text_file("settings.cfg")
        assert is_text_file("app.conf")

        # Test log files
        assert is_text_file("app.log")
        assert is_text_file("error.LOG")

        # Test RDF formats
        assert is_text_file("data.rdf")
        assert is_text_file("data.n3")
        assert is_text_file("data.ttl")
        assert is_text_file("data.nt")

        # Test non-text files
        assert not is_text_file("test.html")
        assert not is_text_file("test.md")
        assert not is_text_file("test.pdf")
        assert not is_text_file("test.jpg")
        assert not is_text_file("test")  # no extension

    def test_is_text_content_type(self):
        # Test positive cases
        assert is_text_content_type("text/plain")
        assert is_text_content_type("text/plain; charset=utf-8")
        assert is_text_content_type("text/plain; charset=iso-8859-1")

        # Test case insensitivity
        assert is_text_content_type("TEXT/PLAIN")
        assert is_text_content_type("Text/Plain")

        # Test negative cases
        assert not is_text_content_type("text/html")
        assert not is_text_content_type("text/markdown")
        assert not is_text_content_type("application/json")
        assert not is_text_content_type(None)
        assert not is_text_content_type("")

    def test_local_text_file_detection(self, tmp_path):
        # Create a test text file
        txt_file = tmp_path / "test.txt"
        txt_content = "This is plain text content.\nMultiple lines.\nNo conversion needed."
        txt_file.write_text(txt_content, encoding="utf-8")

        # Test that it's detected as text (skip conversion)
        content, is_markdown, base_url = get_html_content(
            str(txt_file),
            InputType.FILE,
            no_js=True,
        )

        assert is_markdown is True  # Returns True for passthrough content
        assert content == txt_content

    def test_local_json_file_detection(self, tmp_path):
        # Create a test JSON file
        json_file = tmp_path / "data.json"
        json_content = '{"key": "value", "number": 42, "nested": {"item": true}}'
        json_file.write_text(json_content, encoding="utf-8")

        # Test that it's detected as text (skip conversion)
        content, is_markdown, base_url = get_html_content(
            str(json_file),
            InputType.FILE,
            no_js=True,
        )

        assert is_markdown is True  # Returns True for passthrough content
        assert content == json_content


class TestCloudflareMarkdownForAgents:
    """Tests for Cloudflare Markdown for Agents support.

    When a website enables Cloudflare's Markdown for Agents feature,
    AI agents can receive Markdown directly instead of HTML, reducing
    token consumption by ~80%.
    """

    @patch("urllib.request.urlopen")
    def test_url_fetch_sends_accept_header_with_markdown_and_html(self, mock_urlopen):
        """Verify URL fetch includes Accept: text/markdown, text/html header for Cloudflare support."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.getheader.return_value = "text/html; charset=utf-8"
        mock_response.read.return_value = b"<html><body>Test</body></html>"
        mock_urlopen.return_value.__enter__ = MagicMock(return_value=mock_response)
        mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)

        # Call get_html_content for a URL that doesn't look like a file
        # Using a domain that doesn't have a file extension
        content, is_markdown, base_url = get_html_content(
            "https://example.com",
            InputType.URL,
            no_js=True,  # Use simple HTTP fetch
        )

        # Verify urlopen was called
        mock_urlopen.assert_called_once()

        # Get the Request object that was passed to urlopen
        call_args = mock_urlopen.call_args
        request_obj = call_args[0][0]

        # Verify Accept header is set
        accept_header = request_obj.get_header("Accept")
        assert accept_header == "text/markdown, text/html"

    @patch("urllib.request.urlopen")
    def test_cloudflare_markdown_response_returns_is_markdown_true(self, mock_urlopen):
        """When server returns text/markdown Content-Type, should return is_markdown=True."""
        # Setup mock response simulating Cloudflare Markdown response
        mock_response = MagicMock()
        mock_response.getheader.side_effect = lambda h: {
            "Content-Type": "text/markdown",
            "X-Markdown-Tokens": "1500",
        }.get(h)
        mock_response.read.return_value = b"# Hello World\n\nThis is markdown content."
        mock_urlopen.return_value.__enter__ = MagicMock(return_value=mock_response)
        mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)

        # Call get_html_content for a URL with .md extension (triggers file fetch)
        content, is_markdown, base_url = get_html_content(
            "https://example.com/README.md",
            InputType.URL,
            no_js=True,
        )

        # Should return is_markdown=True to skip HTML parsing
        assert is_markdown is True
        assert "# Hello World" in content

    @patch("urllib.request.urlopen")
    def test_cloudflare_html_response_returns_is_markdown_false(self, mock_urlopen):
        """When server returns text/html Content-Type, should return is_markdown=False."""
        # Setup mock response simulating regular HTML response
        mock_response = MagicMock()
        mock_response.getheader.side_effect = lambda h: {
            "Content-Type": "text/html; charset=utf-8",
        }.get(h)
        mock_response.read.return_value = b"<html><body><h1>Hello</h1></body></html>"
        mock_urlopen.return_value.__enter__ = MagicMock(return_value=mock_response)
        mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)

        # Call get_html_content for a URL with .md extension
        content, is_markdown, base_url = get_html_content(
            "https://example.com/README.md",
            InputType.URL,
            no_js=True,
        )

        # Should return is_markdown=False to trigger HTML parsing
        assert is_markdown is False
        assert "<h1>Hello</h1>" in content

    @patch("urllib.request.urlopen")
    def test_x_markdown_tokens_header_logged_when_present(self, mock_urlopen, capsys):
        """When server includes X-Markdown-Tokens header, it should be logged."""
        # Setup mock response with X-Markdown-Tokens header
        mock_response = MagicMock()
        mock_response.getheader.side_effect = lambda h: {
            "Content-Type": "text/markdown",
            "X-Markdown-Tokens": "1500",
        }.get(h)
        mock_response.read.return_value = b"# Hello World"
        mock_urlopen.return_value.__enter__ = MagicMock(return_value=mock_response)
        mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)

        # Call get_html_content
        content, is_markdown, base_url = get_html_content(
            "https://example.com/README.md",
            InputType.URL,
            no_js=True,
        )

        # Verify logging occurred to stderr
        captured = capsys.readouterr()
        assert "Markdown tokens" in captured.err or "1500" in captured.err


class TestHTTPPrefetchFallback:
    """Tests for HTTP prefetch fallback to Playwright.

    When HTTP prefetch fails (e.g., 403 Forbidden), get_html_content should
    fall back to Playwright instead of propagating the error.
    """

    # Realistic HTML with enough body text (>200 chars) to avoid triggering
    # the empty-content auto-retry with networkidle.
    _RENDERED_HTML = (
        "<html><body><h1>Rendered</h1>"
        "<p>" + "This is a paragraph with meaningful content. " * 8 + "</p>"
        "</body></html>"
    )
    _WORKS_HTML = (
        "<html><body><h1>Works</h1>"
        "<p>" + "The server returned content successfully. " * 8 + "</p>"
        "</body></html>"
    )
    _FALLBACK_HTML = (
        "<html><body><h1>Fallback</h1>"
        "<p>" + "Content loaded via Playwright fallback. " * 8 + "</p>"
        "</body></html>"
    )

    @patch("playwrightmd.fetch_with_playwright")
    @patch("urllib.request.urlopen")
    def test_http_403_falls_back_to_playwright(self, mock_urlopen, mock_playwright):
        """When prefetch gets HTTP 403, should fall back to Playwright."""
        # Simulate 403 from urllib prefetch
        mock_urlopen.side_effect = HTTPError(
            url="https://example.com/page",
            code=403,
            msg="Forbidden",
            hdrs=None,  # type: ignore[arg-type]
            fp=None,
        )

        # Playwright fallback returns rendered HTML
        mock_playwright.return_value = self._RENDERED_HTML

        content, is_markdown, base_url = get_html_content(
            "https://example.com/page",
            InputType.URL,
        )

        # Should have fallen back to Playwright
        mock_playwright.assert_called_once()
        assert "<h1>Rendered</h1>" in content
        assert is_markdown is False

    @patch("playwrightmd.fetch_with_playwright")
    @patch("urllib.request.urlopen")
    def test_http_500_falls_back_to_playwright(self, mock_urlopen, mock_playwright):
        """When prefetch gets HTTP 500, should fall back to Playwright."""
        mock_urlopen.side_effect = HTTPError(
            url="https://example.com/page",
            code=500,
            msg="Internal Server Error",
            hdrs=None,  # type: ignore[arg-type]
            fp=None,
        )

        mock_playwright.return_value = self._WORKS_HTML

        content, is_markdown, base_url = get_html_content(
            "https://example.com/page",
            InputType.URL,
        )

        mock_playwright.assert_called_once()
        assert "<h1>Works</h1>" in content

    @patch("playwrightmd.fetch_with_playwright")
    @patch("urllib.request.urlopen")
    def test_connection_error_falls_back_to_playwright(self, mock_urlopen, mock_playwright):
        """When prefetch gets a connection error, should fall back to Playwright."""
        from urllib.error import URLError

        mock_urlopen.side_effect = URLError("Connection refused")

        mock_playwright.return_value = self._FALLBACK_HTML

        content, is_markdown, base_url = get_html_content(
            "https://example.com/page",
            InputType.URL,
        )

        mock_playwright.assert_called_once()
        assert "<h1>Fallback</h1>" in content

    @patch("urllib.request.urlopen")
    def test_http_error_with_no_js_still_raises(self, mock_urlopen):
        """When --no-js is set and prefetch fails, there's no Playwright fallback, so error should propagate."""
        mock_urlopen.side_effect = HTTPError(
            url="https://example.com/page",
            code=403,
            msg="Forbidden",
            hdrs=None,  # type: ignore[arg-type]
            fp=None,
        )

        with pytest.raises(HTTPError):
            get_html_content(
                "https://example.com/page",
                InputType.URL,
                no_js=True,
            )


class TestBinaryContentRejection:
    """Fetching a URL that returns binary content (PDF, images, etc.) should
    fail gracefully with a clear error instead of crashing with UnicodeDecodeError."""

    @patch("urllib.request.urlopen")
    def test_pdf_content_type_raises_value_error(self, mock_urlopen):
        """http_prefetch rejects application/pdf with a descriptive ValueError."""
        mock_response = MagicMock()
        mock_response.getheader.side_effect = lambda h: {
            "Content-Type": "application/pdf",
        }.get(h)
        mock_response.read.return_value = b"%PDF-1.4 binary garbage \xbf\x00"
        mock_urlopen.return_value.__enter__ = MagicMock(return_value=mock_response)
        mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)

        with pytest.raises(ValueError, match="binary.*application/pdf"):
            http_prefetch("https://arxiv.org/pdf/2603.02473v1")

    @patch("urllib.request.urlopen")
    def test_image_content_type_raises_value_error(self, mock_urlopen):
        """http_prefetch rejects image/png with a descriptive ValueError."""
        mock_response = MagicMock()
        mock_response.getheader.side_effect = lambda h: {
            "Content-Type": "image/png",
        }.get(h)
        mock_response.read.return_value = b"\x89PNG\r\n\x1a\n\x00\x00"
        mock_urlopen.return_value.__enter__ = MagicMock(return_value=mock_response)
        mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)

        with pytest.raises(ValueError, match="binary.*image/png"):
            http_prefetch("https://example.com/photo.png")

    @patch("urllib.request.urlopen")
    def test_octet_stream_raises_value_error(self, mock_urlopen):
        """http_prefetch rejects application/octet-stream."""
        mock_response = MagicMock()
        mock_response.getheader.side_effect = lambda h: {
            "Content-Type": "application/octet-stream",
        }.get(h)
        mock_response.read.return_value = b"\x00\x01\x02\x03"
        mock_urlopen.return_value.__enter__ = MagicMock(return_value=mock_response)
        mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)

        with pytest.raises(ValueError, match="binary.*application/octet-stream"):
            http_prefetch("https://example.com/file.bin")

    @patch("urllib.request.urlopen")
    def test_binary_url_gives_graceful_exit_code(self, mock_urlopen, capsys):
        """main() returns exit code 1 with descriptive error for binary URLs."""
        from playwrightmd import main

        mock_response = MagicMock()
        mock_response.getheader.side_effect = lambda h: {
            "Content-Type": "application/pdf",
        }.get(h)
        mock_response.read.return_value = b"%PDF-1.4 \xbf"
        mock_urlopen.return_value.__enter__ = MagicMock(return_value=mock_response)
        mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)

        result = main(
            ["https://arxiv.org/pdf/2603.02473v1", "--no-js"],
            standalone_mode=False,
        )
        assert result == 1
        captured = capsys.readouterr()
        # Error message should mention binary content, not show raw UnicodeDecodeError
        assert "binary" in captured.err.lower()
        assert "application/pdf" in captured.err

    @patch("urllib.request.urlopen")
    def test_text_html_still_works(self, mock_urlopen):
        """text/html content type should still be fetched normally (not rejected)."""
        mock_response = MagicMock()
        mock_response.getheader.side_effect = lambda h: {
            "Content-Type": "text/html; charset=utf-8",
        }.get(h)
        mock_response.read.return_value = b"<html><body>Hello</body></html>"
        mock_urlopen.return_value.__enter__ = MagicMock(return_value=mock_response)
        mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)

        content, content_type = http_prefetch("https://example.com")
        assert "<html>" in content
        assert content_type == "text/html; charset=utf-8"

    @patch("urllib.request.urlopen")
    def test_no_content_type_still_works(self, mock_urlopen):
        """Missing Content-Type header should still attempt decode (backward compat)."""
        mock_response = MagicMock()
        mock_response.getheader.return_value = None
        mock_response.read.return_value = b"<html><body>Hello</body></html>"
        mock_urlopen.return_value.__enter__ = MagicMock(return_value=mock_response)
        mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)

        content, content_type = http_prefetch("https://example.com")
        assert "<html>" in content


# Minimal Next.js SSG page: article shell is present but body is empty.
# This simulates what percepta.ai (and many Next.js sites) return before
# React hydration injects the actual blog content.
EMPTY_NEXTJS_HTML = """<!DOCTYPE html><html lang="en"><head>
<title>Blog Post | Site</title></head><body>
<div id="__next"><main class="blog-post-content">
<header><h1>Blog Post Title</h1></header>
<article class="prose-wrapper overflow-visible"></article>
</main></div>
<script id="__NEXT_DATA__" type="application/json">{"props":{}}</script>
</body></html>"""

# The same page after React hydration — article has real content.
HYDRATED_NEXTJS_HTML = """<!DOCTYPE html><html lang="en"><head>
<title>Blog Post | Site</title></head><body>
<div id="__next"><main class="blog-post-content">
<header><h1>Blog Post Title</h1></header>
<article class="prose-wrapper overflow-visible">
<p>Language models can solve tough math problems but struggle on simple
computational tasks that involve reasoning over many steps.</p>
<h2>Motivation</h2>
<p>State-of-the-art language models can solve impressively hard mathematics.</p>
</article>
</main></div></body></html>"""


class TestEmptyContentAutoRetry:
    """When Playwright returns HTML with no extractable content (e.g. Next.js
    SSG pages where React hasn't hydrated yet), get_html_content should
    automatically retry with wait_until=networkidle."""

    @patch("playwrightmd.fetch_with_playwright")
    @patch("playwrightmd.http_prefetch")
    def test_retries_with_networkidle_when_content_empty(
        self, mock_prefetch, mock_playwright
    ):
        """Empty article on domcontentloaded should trigger a networkidle retry."""
        mock_prefetch.return_value = (EMPTY_NEXTJS_HTML, "text/html; charset=utf-8")
        # First call (domcontentloaded) returns empty, second (networkidle) returns content
        mock_playwright.side_effect = [EMPTY_NEXTJS_HTML, HYDRATED_NEXTJS_HTML]

        content, is_markdown, base_url = get_html_content(
            "https://example.com/blog/post",
            InputType.URL,
        )

        assert mock_playwright.call_count == 2
        # Second call should use networkidle
        second_call = mock_playwright.call_args_list[1]
        assert second_call.kwargs.get("wait_until") == "networkidle"
        # Returned content should be the hydrated version
        assert "Language models" in content

    @patch("playwrightmd.fetch_with_playwright")
    @patch("playwrightmd.http_prefetch")
    def test_no_retry_when_content_present(self, mock_prefetch, mock_playwright):
        """If domcontentloaded returns content, no retry needed."""
        mock_prefetch.return_value = (HYDRATED_NEXTJS_HTML, "text/html; charset=utf-8")
        mock_playwright.return_value = HYDRATED_NEXTJS_HTML

        content, is_markdown, base_url = get_html_content(
            "https://example.com/blog/post",
            InputType.URL,
        )

        mock_playwright.assert_called_once()
        assert "Language models" in content

    @patch("playwrightmd.fetch_with_playwright")
    @patch("playwrightmd.http_prefetch")
    def test_no_retry_when_user_set_networkidle(self, mock_prefetch, mock_playwright):
        """If user explicitly chose networkidle, don't retry (already using it)."""
        mock_prefetch.return_value = (EMPTY_NEXTJS_HTML, "text/html; charset=utf-8")
        mock_playwright.return_value = EMPTY_NEXTJS_HTML

        content, is_markdown, base_url = get_html_content(
            "https://example.com/blog/post",
            InputType.URL,
            wait_until="networkidle",
        )

        mock_playwright.assert_called_once()

    @patch("playwrightmd.fetch_with_playwright")
    @patch("playwrightmd.http_prefetch")
    def test_no_retry_when_user_set_load(self, mock_prefetch, mock_playwright):
        """If user explicitly chose 'load', don't second-guess their choice."""
        mock_prefetch.return_value = (EMPTY_NEXTJS_HTML, "text/html; charset=utf-8")
        mock_playwright.return_value = EMPTY_NEXTJS_HTML

        content, is_markdown, base_url = get_html_content(
            "https://example.com/blog/post",
            InputType.URL,
            wait_until="load",
        )

        mock_playwright.assert_called_once()

    @patch("playwrightmd.http_prefetch")
    def test_no_retry_in_no_js_mode(self, mock_prefetch):
        """--no-js skips Playwright entirely, so no retry should happen."""
        mock_prefetch.return_value = (EMPTY_NEXTJS_HTML, "text/html; charset=utf-8")

        content, is_markdown, base_url = get_html_content(
            "https://example.com/blog/post",
            InputType.URL,
            no_js=True,
        )

        # Should return the prefetch content as-is, no Playwright involved
        assert content == EMPTY_NEXTJS_HTML

    @patch("playwrightmd.fetch_with_playwright")
    @patch("playwrightmd.http_prefetch")
    def test_retry_emits_stderr_hint(self, mock_prefetch, mock_playwright, capsys):
        """Retry should log a hint to stderr so users know what happened."""
        mock_prefetch.return_value = (EMPTY_NEXTJS_HTML, "text/html; charset=utf-8")
        mock_playwright.side_effect = [EMPTY_NEXTJS_HTML, HYDRATED_NEXTJS_HTML]

        get_html_content(
            "https://example.com/blog/post",
            InputType.URL,
        )

        captured = capsys.readouterr()
        assert "networkidle" in captured.err.lower() or "retry" in captured.err.lower()

    @patch("playwrightmd.fetch_with_playwright")
    @patch("playwrightmd.http_prefetch")
    def test_retry_preserves_other_params(self, mock_prefetch, mock_playwright):
        """Retry call should preserve timeout, wait_for, user_agent, etc."""
        mock_prefetch.return_value = (EMPTY_NEXTJS_HTML, "text/html; charset=utf-8")
        mock_playwright.side_effect = [EMPTY_NEXTJS_HTML, HYDRATED_NEXTJS_HTML]

        get_html_content(
            "https://example.com/blog/post",
            InputType.URL,
            timeout=60000,
            user_agent="CustomAgent/1.0",
        )

        second_call = mock_playwright.call_args_list[1]
        assert second_call.kwargs.get("timeout") == 60000
        assert second_call.kwargs.get("user_agent") == "CustomAgent/1.0"
        assert second_call.kwargs.get("wait_until") == "networkidle"
