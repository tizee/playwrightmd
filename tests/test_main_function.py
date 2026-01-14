import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
from playwrightmd import main, detect_input_type, InputType


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
