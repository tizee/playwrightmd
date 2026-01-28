import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
from playwrightmd import main, detect_input_type, InputType, truncate_markdown_links


class TestMainFunction:
    def test_detect_input_type(self):
        # Test URL detection
        assert detect_input_type("https://example.com") == InputType.URL
        assert detect_input_type("http://example.com") == InputType.URL
        assert detect_input_type("example.com") == InputType.URL  # will default to URL

        # Test file detection
        with patch("pathlib.Path.exists", return_value=True):
            assert detect_input_type("/path/to/file.html") == InputType.FILE
            assert detect_input_type("file.html") == InputType.FILE

        # Test stdin detection
        assert detect_input_type(None) == InputType.STDIN
        assert detect_input_type("-") == InputType.STDIN

    def test_main_with_positional_output(self, tmp_path):
        # Create test HTML file
        html_file = tmp_path / "test.html"
        output_file = tmp_path / "output.md"
        html_content = """
        <html>
            <head><title>Test</title></head>
            <body>
                <h1>Test HTML</h1>
                <p>This is a paragraph with <strong>bold</strong> text.</p>
            </body>
        </html>
        """
        html_file.write_text(html_content, encoding="utf-8")

        # Run main with positional output argument
        with patch.object(sys, 'argv', ['playwrightmd', str(html_file), str(output_file)]):
            result = main()
            assert result == 0

        # Verify output file was created and contains markdown
        assert output_file.exists()
        output_content = output_file.read_text(encoding="utf-8")
        assert "# Test HTML" in output_content
        assert "This is a paragraph with **bold** text." in output_content

    def test_main_with_output_flag_backward_compat(self, tmp_path):
        # Create test HTML file
        html_file = tmp_path / "test.html"
        output_file = tmp_path / "output.md"
        html_content = "<html><body><h1>Backward Compat Test</h1></body></html>"
        html_file.write_text(html_content, encoding="utf-8")

        # Run main with -o flag (backward compatibility)
        with patch.object(sys, 'argv', ['playwrightmd', str(html_file), '-o', str(output_file)]):
            result = main()
            assert result == 0

        # Verify output file was created
        assert output_file.exists()
        output_content = output_file.read_text(encoding="utf-8")
        assert "# Backward Compat Test" in output_content

    def test_main_positional_output_takes_precedence(self, tmp_path):
        # Create test HTML file
        html_file = tmp_path / "test.html"
        positional_output = tmp_path / "positional.md"
        flag_output = tmp_path / "flag.md"
        html_content = "<html><body><h1>Precedence Test</h1></body></html>"
        html_file.write_text(html_content, encoding="utf-8")

        # Run main with both positional and -o flag (positional should win)
        with patch.object(sys, 'argv', ['playwrightmd', str(html_file), str(positional_output), '-o', str(flag_output)]):
            result = main()
            assert result == 0

        # Verify only positional output file was created
        assert positional_output.exists()
        assert not flag_output.exists()
        output_content = positional_output.read_text(encoding="utf-8")
        assert "# Precedence Test" in output_content

    def test_main_with_markdown_file(self, tmp_path, capsys):
        # Create test markdown file
        md_file = tmp_path / "test.md"
        md_content = "# Test Markdown\n\nThis is a paragraph with **bold** and *italic* text.\n\n- List item 1\n- List item 2"
        md_file.write_text(md_content, encoding="utf-8")

        # Run main with markdown file input
        with patch.object(sys, 'argv', ['playwrightmd', str(md_file)]):
            result = main()
            assert result == 0

        # Capture output
        captured = capsys.readouterr()
        assert captured.out.strip() == md_content.strip()

    def test_main_with_html_file(self, tmp_path, capsys):
        # Create test HTML file
        html_file = tmp_path / "test.html"
        html_content = """
        <html>
            <head><title>Test</title></head>
            <body>
                <h1>Test HTML</h1>
                <p>This is a paragraph with <strong>bold</strong> and <em>italic</em> text.</p>
                <ul>
                    <li>List item 1</li>
                    <li>List item 2</li>
                </ul>
            </body>
        </html>
        """
        html_file.write_text(html_content, encoding="utf-8")

        # Run main with HTML file input
        with patch.object(sys, 'argv', ['playwrightmd', str(html_file)]):
            result = main()
            assert result == 0

        # Capture output
        captured = capsys.readouterr()
        output = captured.out.strip()

        # Verify conversion happened
        assert "# Test HTML" in output  # h1 converted to #
        assert "This is a paragraph with **bold** and *italic* text." in output
        assert "- List item 1" in output
        assert "- List item 2" in output

    def test_main_with_raw_flag(self, tmp_path, capsys):
        # Create test HTML file
        html_file = tmp_path / "test.html"
        html_content = "<html><body><h1>Test</h1></body></html>"
        html_file.write_text(html_content, encoding="utf-8")

        # Run main with --raw flag
        with patch.object(sys, 'argv', ['playwrightmd', str(html_file), '--raw']):
            result = main()
            assert result == 0

        # Capture output
        captured = capsys.readouterr()
        output = captured.out.strip()

        # When running through Playwright, it adds proper HTML structure
        assert "<h1>Test</h1>" in output
        assert "<body>" in output
        assert "<html>" in output

    def test_main_with_text_file(self, tmp_path, capsys):
        # Create test text file
        txt_file = tmp_path / "test.txt"
        txt_content = "This is plain text content.\nMultiple lines.\nNo conversion needed."
        txt_file.write_text(txt_content, encoding="utf-8")

        # Run main with text file input
        with patch.object(sys, 'argv', ['playwrightmd', str(txt_file)]):
            result = main()
            assert result == 0

        # Capture output
        captured = capsys.readouterr()
        assert captured.out.strip() == txt_content.strip()

    def test_main_with_json_file(self, tmp_path, capsys):
        # Create test JSON file
        json_file = tmp_path / "data.json"
        json_content = '{"key": "value", "number": 42, "nested": {"item": true}}'
        json_file.write_text(json_content, encoding="utf-8")

        # Run main with JSON file input
        with patch.object(sys, 'argv', ['playwrightmd', str(json_file)]):
            result = main()
            assert result == 0

        # Capture output - JSON should pass through unchanged
        captured = capsys.readouterr()
        assert captured.out.strip() == json_content.strip()

    def test_truncate_links_default_length(self, tmp_path, capsys):
        # Create test HTML file with a long link
        html_file = tmp_path / "test.html"
        long_url = "https://example.com/very/long/path/to/some/resource?param1=value1&param2=value2&param3=value3"
        html_content = f'<html><body><a href="{long_url}">Link Text</a></body></html>'
        html_file.write_text(html_content, encoding="utf-8")

        # Run main with --truncate-link flag (default 42)
        with patch.object(sys, 'argv', ['playwrightmd', str(html_file), '--truncate-link']):
            result = main()
            assert result == 0

        # Capture output
        captured = capsys.readouterr()
        output = captured.out

        # Verify URL is truncated (42 display width = 41 chars + ellipsis)
        assert "https://example.com/very/long/path/to/som…" in output
        assert "Link Text" in output
        # Original URL should NOT be present
        assert long_url not in output

    def test_truncate_links_custom_length(self, tmp_path, capsys):
        # Create test HTML file with a long link
        html_file = tmp_path / "test.html"
        long_url = "https://example.com/very/long/path/to/some/resource"
        html_content = f'<html><body><a href="{long_url}">Link Text</a></body></html>'
        html_file.write_text(html_content, encoding="utf-8")

        # Run main with --truncate-link 20
        with patch.object(sys, 'argv', ['playwrightmd', str(html_file), '--truncate-link', '20']):
            result = main()
            assert result == 0

        # Capture output
        captured = capsys.readouterr()
        output = captured.out

        # Verify URL is truncated to 20 display width (19 chars + "…")
        assert "https://example.com…" in output

    def test_truncate_links_no_truncation_for_short_urls(self, tmp_path, capsys):
        # Create test HTML file with a short link
        html_file = tmp_path / "test.html"
        short_url = "https://example.com"
        html_content = f'<html><body><a href="{short_url}">Link Text</a></body></html>'
        html_file.write_text(html_content, encoding="utf-8")

        # Run main with --truncate-link
        with patch.object(sys, 'argv', ['playwrightmd', str(html_file), '--truncate-link']):
            result = main()
            assert result == 0

        # Capture output
        captured = capsys.readouterr()
        output = captured.out

        # Short URL should remain unchanged
        assert "https://example.com" in output
        assert "…" not in output


class TestTruncateMarkdownLinks:
    def test_truncate_long_url(self):
        markdown = "[Link](https://example.com/very/long/path/to/some/resource?query=param)"
        result = truncate_markdown_links(markdown, max_length=20)
        # Should be truncated to 20 display width (19 chars + ellipsis)
        assert result == "[Link](https://example.com…)"

    def test_no_truncate_short_url(self):
        markdown = "[Link](https://example.com)"
        result = truncate_markdown_links(markdown, max_length=42)
        assert result == "[Link](https://example.com)"

    def test_truncate_with_title(self):
        markdown = '[Link](https://example.com/very/long/path "Title")'
        result = truncate_markdown_links(markdown, max_length=20)
        # Title is preserved during truncation, truncated to 20 display width
        assert result == '[Link](https://example.com… "Title")'

    def test_multiple_links(self):
        markdown = "[Link1](https://short.com) and [Link2](https://example.com/very/long/path)"
        result = truncate_markdown_links(markdown, max_length=20)
        assert "[Link1](https://short.com)" in result
        assert "[Link2](https://example.com…)" in result

    def test_no_links_unchanged(self):
        markdown = "This is just plain text without any links."
        result = truncate_markdown_links(markdown, max_length=10)
        assert result == markdown
