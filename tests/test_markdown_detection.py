import pytest
from pathlib import Path
from playwrightmd import (
    is_markdown_file,
    is_markdown_content_type,
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
