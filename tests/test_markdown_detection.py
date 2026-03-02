import pytest
from pathlib import Path
from urllib.error import HTTPError
from unittest.mock import patch, MagicMock
from playwrightmd import (
    is_markdown_file,
    is_markdown_content_type,
    is_text_file,
    is_text_content_type,
    get_html_content,
    InputType,
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
        content, is_markdown = get_html_content(
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
        content, is_markdown = get_html_content(
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
        content, is_markdown = get_html_content(
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
        content, is_markdown = get_html_content(
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

    @patch('urllib.request.urlopen')
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
        content, is_markdown = get_html_content(
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

    @patch('urllib.request.urlopen')
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
        content, is_markdown = get_html_content(
            "https://example.com/README.md",
            InputType.URL,
            no_js=True,
        )

        # Should return is_markdown=True to skip HTML parsing
        assert is_markdown is True
        assert "# Hello World" in content

    @patch('urllib.request.urlopen')
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
        content, is_markdown = get_html_content(
            "https://example.com/README.md",
            InputType.URL,
            no_js=True,
        )

        # Should return is_markdown=False to trigger HTML parsing
        assert is_markdown is False
        assert "<h1>Hello</h1>" in content

    @patch('urllib.request.urlopen')
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
        content, is_markdown = get_html_content(
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

    @patch('playwrightmd.fetch_with_playwright')
    @patch('urllib.request.urlopen')
    def test_http_403_falls_back_to_playwright(self, mock_urlopen, mock_playwright):
        """When prefetch gets HTTP 403, should fall back to Playwright."""
        # Simulate 403 from urllib prefetch
        mock_urlopen.side_effect = HTTPError(
            url="https://example.com/page",
            code=403,
            msg="Forbidden",
            hdrs={},
            fp=None,
        )

        # Playwright fallback returns rendered HTML
        mock_playwright.return_value = "<html><body><h1>Rendered</h1></body></html>"

        content, is_markdown = get_html_content(
            "https://example.com/page",
            InputType.URL,
        )

        # Should have fallen back to Playwright
        mock_playwright.assert_called_once()
        assert "<h1>Rendered</h1>" in content
        assert is_markdown is False

    @patch('playwrightmd.fetch_with_playwright')
    @patch('urllib.request.urlopen')
    def test_http_500_falls_back_to_playwright(self, mock_urlopen, mock_playwright):
        """When prefetch gets HTTP 500, should fall back to Playwright."""
        mock_urlopen.side_effect = HTTPError(
            url="https://example.com/page",
            code=500,
            msg="Internal Server Error",
            hdrs={},
            fp=None,
        )

        mock_playwright.return_value = "<html><body><h1>Works</h1></body></html>"

        content, is_markdown = get_html_content(
            "https://example.com/page",
            InputType.URL,
        )

        mock_playwright.assert_called_once()
        assert "<h1>Works</h1>" in content

    @patch('playwrightmd.fetch_with_playwright')
    @patch('urllib.request.urlopen')
    def test_connection_error_falls_back_to_playwright(self, mock_urlopen, mock_playwright):
        """When prefetch gets a connection error, should fall back to Playwright."""
        from urllib.error import URLError
        mock_urlopen.side_effect = URLError("Connection refused")

        mock_playwright.return_value = "<html><body><h1>Fallback</h1></body></html>"

        content, is_markdown = get_html_content(
            "https://example.com/page",
            InputType.URL,
        )

        mock_playwright.assert_called_once()
        assert "<h1>Fallback</h1>" in content

    @patch('urllib.request.urlopen')
    def test_http_error_with_no_js_still_raises(self, mock_urlopen):
        """When --no-js is set and prefetch fails, there's no Playwright fallback, so error should propagate."""
        mock_urlopen.side_effect = HTTPError(
            url="https://example.com/page",
            code=403,
            msg="Forbidden",
            hdrs={},
            fp=None,
        )

        with pytest.raises(HTTPError):
            get_html_content(
                "https://example.com/page",
                InputType.URL,
                no_js=True,
            )
