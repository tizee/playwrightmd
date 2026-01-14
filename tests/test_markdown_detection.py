import pytest
from pathlib import Path
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
