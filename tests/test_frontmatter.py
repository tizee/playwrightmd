"""Tests for unified YAML frontmatter: metadata extraction + formatting.

Behavior under test:
- extract_metadata pulls structured metadata from HTML <head> tags
- Priority: OG > article meta > standard meta > JSON-LD > twitter cards
- format_frontmatter renders a valid YAML frontmatter block
- Only non-empty fields are included in output
- Values with special YAML characters are properly quoted
- main() prepends frontmatter to markdown output for HTML pages
"""

import pytest
from unittest.mock import patch, MagicMock
from click.testing import CliRunner

from playwrightmd import PageMetadata, extract_metadata, format_frontmatter, main


# ---------------------------------------------------------------------------
# Fixtures: HTML fragments for testing
# ---------------------------------------------------------------------------

OG_HTML = """<!DOCTYPE html><html><head>
<meta property="og:title" content="Can LLMs Be Computers?">
<meta property="og:description" content="We build a computer inside a transformer.">
<meta property="og:site_name" content="Percepta">
<meta property="og:url" content="https://percepta.ai/blog/can-llms-be-computers">
<meta property="og:image" content="https://percepta.ai/blog/turing-hero-og.png">
<meta property="article:published_time" content="2026-03-11T00:00:00.000Z">
<meta property="article:author" content="Christos Tzamos">
</head><body><p>Content</p></body></html>"""

STANDARD_META_HTML = """<!DOCTYPE html><html><head>
<title>A Simple Blog Post</title>
<meta name="author" content="Jane Doe">
<meta name="description" content="A post about something interesting.">
</head><body><p>Content</p></body></html>"""

JSONLD_HTML = """<!DOCTYPE html><html><head>
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "BlogPosting",
  "headline": "JSON-LD Article Title",
  "description": "Description from JSON-LD.",
  "datePublished": "2026-01-15T10:00:00Z",
  "author": [{"@type": "Person", "name": "John Smith"}],
  "publisher": {"@type": "Organization", "name": "TechBlog"}
}
</script>
</head><body><p>Content</p></body></html>"""

TWITTER_CARD_HTML = """<!DOCTYPE html><html><head>
<meta name="twitter:title" content="Twitter Card Title">
<meta name="twitter:description" content="Description from twitter card.">
</head><body><p>Content</p></body></html>"""

MIXED_PRIORITY_HTML = """<!DOCTYPE html><html><head>
<title>Standard Title</title>
<meta name="description" content="Standard description">
<meta name="author" content="Standard Author">
<meta property="og:title" content="OG Title">
<meta property="og:description" content="OG description">
<meta name="twitter:title" content="Twitter Title">
<meta name="twitter:description" content="Twitter description">
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Article",
  "headline": "JSON-LD Title",
  "author": {"@type": "Person", "name": "JSON-LD Author"},
  "datePublished": "2026-02-20"
}
</script>
</head><body><p>Content</p></body></html>"""

MINIMAL_HTML = """<!DOCTYPE html><html><head>
<title>Bare Page</title>
</head><body><p>Content</p></body></html>"""

EMPTY_HTML = """<!DOCTYPE html><html><head></head><body></body></html>"""

SPECIAL_CHARS_HTML = """<!DOCTYPE html><html><head>
<meta property="og:title" content='He said "hello" &amp; goodbye'>
<meta property="og:description" content="Line with: colon and #hash">
</head><body><p>Content</p></body></html>"""

JSONLD_AUTHOR_STRING_HTML = """<!DOCTYPE html><html><head>
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Article",
  "headline": "Article With String Author",
  "author": "Simple Author Name"
}
</script>
</head><body><p>Content</p></body></html>"""

JSONLD_MULTIPLE_AUTHORS_HTML = """<!DOCTYPE html><html><head>
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "NewsArticle",
  "headline": "Multi-Author Article",
  "author": [
    {"@type": "Person", "name": "Alice"},
    {"@type": "Person", "name": "Bob"}
  ]
}
</script>
</head><body><p>Content</p></body></html>"""


# ---------------------------------------------------------------------------
# extract_metadata tests
# ---------------------------------------------------------------------------


class TestExtractMetadata:
    """extract_metadata pulls structured metadata from HTML <head>."""

    def test_extracts_open_graph_tags(self):
        meta = extract_metadata(OG_HTML, "https://percepta.ai/blog/can-llms-be-computers")
        assert meta.title == "Can LLMs Be Computers?"
        assert meta.description == "We build a computer inside a transformer."
        assert meta.site == "Percepta"
        assert meta.image == "https://percepta.ai/blog/turing-hero-og.png"
        assert meta.source == "https://percepta.ai/blog/can-llms-be-computers"

    def test_extracts_article_meta(self):
        meta = extract_metadata(OG_HTML, "https://percepta.ai/blog/post")
        assert meta.published == "2026-03-11T00:00:00.000Z"
        assert meta.author == "Christos Tzamos"

    def test_extracts_standard_meta_tags(self):
        meta = extract_metadata(STANDARD_META_HTML, "https://example.com/post")
        assert meta.title == "A Simple Blog Post"
        assert meta.author == "Jane Doe"
        assert meta.description == "A post about something interesting."

    def test_extracts_jsonld_article(self):
        meta = extract_metadata(JSONLD_HTML, "https://example.com/post")
        assert meta.title == "JSON-LD Article Title"
        assert meta.description == "Description from JSON-LD."
        assert meta.published == "2026-01-15T10:00:00Z"
        assert meta.author == "John Smith"
        assert meta.site == "TechBlog"

    def test_extracts_twitter_cards(self):
        meta = extract_metadata(TWITTER_CARD_HTML, "https://example.com/post")
        assert meta.title == "Twitter Card Title"
        assert meta.description == "Description from twitter card."

    def test_og_takes_priority_over_standard_and_twitter(self):
        """OG > standard meta > twitter cards for title and description."""
        meta = extract_metadata(MIXED_PRIORITY_HTML, "https://example.com/post")
        assert meta.title == "OG Title"
        assert meta.description == "OG description"

    def test_article_author_over_jsonld_author(self):
        """article:author takes priority over JSON-LD author."""
        html = """<!DOCTYPE html><html><head>
        <meta property="article:author" content="Article Author">
        <script type="application/ld+json">
        {"@type": "Article", "author": {"@type": "Person", "name": "JSON-LD Author"}}
        </script>
        </head><body></body></html>"""
        meta = extract_metadata(html, "https://example.com")
        assert meta.author == "Article Author"

    def test_jsonld_author_as_string(self):
        """JSON-LD author can be a plain string instead of object."""
        meta = extract_metadata(JSONLD_AUTHOR_STRING_HTML, "https://example.com")
        assert meta.author == "Simple Author Name"

    def test_jsonld_multiple_authors(self):
        """JSON-LD with multiple authors should join names."""
        meta = extract_metadata(JSONLD_MULTIPLE_AUTHORS_HTML, "https://example.com")
        assert meta.author == "Alice, Bob"

    def test_minimal_html_extracts_title(self):
        meta = extract_metadata(MINIMAL_HTML, "https://example.com/page")
        assert meta.title == "Bare Page"
        assert meta.source == "https://example.com/page"

    def test_empty_html_returns_source_only(self):
        meta = extract_metadata(EMPTY_HTML, "https://example.com/page")
        assert meta.title is None
        assert meta.source == "https://example.com/page"

    def test_source_always_set_from_url_param(self):
        """source field comes from the url parameter, not og:url."""
        meta = extract_metadata(OG_HTML, "https://www.percepta.ai/blog/can-llms-be-computers")
        assert meta.source == "https://www.percepta.ai/blog/can-llms-be-computers"

    def test_jsonld_non_article_type_ignored(self):
        """JSON-LD with @type other than Article/BlogPosting/NewsArticle should be skipped."""
        html = """<!DOCTYPE html><html><head>
        <script type="application/ld+json">
        {"@type": "WebSite", "name": "My Site", "url": "https://example.com"}
        </script>
        </head><body></body></html>"""
        meta = extract_metadata(html, "https://example.com")
        assert meta.title is None


# ---------------------------------------------------------------------------
# format_frontmatter tests
# ---------------------------------------------------------------------------


class TestFormatFrontmatter:
    """format_frontmatter renders a YAML frontmatter block."""

    def test_full_metadata(self):
        meta = PageMetadata(
            title="Test Title",
            author="Author Name",
            published="2026-03-11",
            description="A description.",
            source="https://example.com/post",
            site="Example",
            image="https://example.com/img.png",
        )
        result = format_frontmatter(meta)
        assert result.startswith("---\n")
        assert result.endswith("---\n")
        assert 'title: "Test Title"' in result
        assert 'author: "Author Name"' in result
        assert 'published: "2026-03-11"' in result
        assert 'description: "A description."' in result
        assert 'source: "https://example.com/post"' in result
        assert 'site: "Example"' in result
        assert 'image: "https://example.com/img.png"' in result

    def test_omits_none_fields(self):
        meta = PageMetadata(
            title="Only Title",
            source="https://example.com",
        )
        result = format_frontmatter(meta)
        assert 'title: "Only Title"' in result
        assert 'source: "https://example.com"' in result
        assert "author:" not in result
        assert "published:" not in result
        assert "description:" not in result
        assert "site:" not in result
        assert "image:" not in result

    def test_special_characters_quoted(self):
        meta = PageMetadata(
            title='He said "hello" & goodbye',
            description="Line with: colon and #hash",
            source="https://example.com",
        )
        result = format_frontmatter(meta)
        # Double quotes inside values should be escaped
        assert 'title: "He said \\"hello\\" & goodbye"' in result
        assert 'description: "Line with: colon and #hash"' in result

    def test_empty_metadata_returns_empty_string(self):
        """If no fields are set, don't emit an empty frontmatter block."""
        meta = PageMetadata()
        result = format_frontmatter(meta)
        assert result == ""

    def test_source_only_returns_empty(self):
        """source alone is not interesting enough for frontmatter."""
        meta = PageMetadata(source="https://example.com")
        result = format_frontmatter(meta)
        assert result == ""

    def test_field_order_is_stable(self):
        """Fields should appear in a consistent, logical order."""
        meta = PageMetadata(
            title="Title",
            author="Author",
            published="2026-01-01",
            source="https://example.com",
            site="Site",
        )
        result = format_frontmatter(meta)
        lines = result.strip().split("\n")
        # First and last lines are ---
        field_lines = [l for l in lines if l != "---"]
        keys = [l.split(":")[0] for l in field_lines]
        assert keys == ["title", "author", "published", "site", "source"]


# ---------------------------------------------------------------------------
# Integration: extract + format
# ---------------------------------------------------------------------------


class TestFrontmatterIntegration:
    """End-to-end: extract_metadata from HTML, then format_frontmatter."""

    def test_og_html_to_frontmatter(self):
        meta = extract_metadata(OG_HTML, "https://percepta.ai/blog/post")
        result = format_frontmatter(meta)
        assert result.startswith("---\n")
        assert 'title: "Can LLMs Be Computers?"' in result
        assert 'author: "Christos Tzamos"' in result
        assert 'site: "Percepta"' in result

    def test_empty_html_no_frontmatter(self):
        meta = extract_metadata(EMPTY_HTML, "https://example.com")
        result = format_frontmatter(meta)
        assert result == ""

    def test_special_chars_roundtrip(self):
        meta = extract_metadata(SPECIAL_CHARS_HTML, "https://example.com")
        result = format_frontmatter(meta)
        assert "---" in result
        # HTML entities should be decoded
        assert "hello" in result
        assert "goodbye" in result


# ---------------------------------------------------------------------------
# Pipeline integration: main() prepends frontmatter
# ---------------------------------------------------------------------------

# Realistic HTML with OG metadata and body content
FULL_PAGE_HTML = """<!DOCTYPE html><html><head>
<meta property="og:title" content="Test Article">
<meta property="og:description" content="An article for testing.">
<meta property="og:site_name" content="TestSite">
<meta property="article:author" content="Test Author">
<meta property="article:published_time" content="2026-03-11">
</head><body>
<article><p>This is the article body with enough content to pass extraction.
It needs to have sufficient text so the content extraction heuristics
don't consider it empty. Here is more text to make it work properly.</p>
<p>Second paragraph with additional content for the extraction pipeline.</p>
</article></body></html>"""


class TestMainFrontmatterIntegration:
    """main() prepends frontmatter to markdown output for HTML pages."""

    @patch("playwrightmd.fetch_with_playwright")
    @patch("playwrightmd.http_prefetch")
    def test_main_prepends_frontmatter(self, mock_prefetch, mock_playwright):
        """Normal HTML page should get frontmatter prepended."""
        mock_prefetch.return_value = (FULL_PAGE_HTML, "text/html; charset=utf-8")
        mock_playwright.return_value = FULL_PAGE_HTML

        runner = CliRunner()
        result = runner.invoke(main, ["https://example.com/article"])

        assert result.exit_code == 0
        output = result.output
        assert output.startswith("---\n")
        assert 'title: "Test Article"' in output
        assert 'author: "Test Author"' in output
        assert 'site: "TestSite"' in output
        # Body content should follow the frontmatter
        assert "article body" in output

    @patch("playwrightmd.fetch_with_playwright")
    @patch("playwrightmd.http_prefetch")
    def test_no_frontmatter_flag(self, mock_prefetch, mock_playwright):
        """--no-frontmatter should suppress frontmatter."""
        mock_prefetch.return_value = (FULL_PAGE_HTML, "text/html; charset=utf-8")
        mock_playwright.return_value = FULL_PAGE_HTML

        runner = CliRunner()
        result = runner.invoke(main, ["https://example.com/article", "--no-frontmatter"])

        assert result.exit_code == 0
        assert not result.output.startswith("---\n")
        assert "article body" in result.output

    @patch("playwrightmd.fetch_with_playwright")
    @patch("playwrightmd.http_prefetch")
    def test_raw_mode_no_frontmatter(self, mock_prefetch, mock_playwright):
        """--raw should output HTML without frontmatter."""
        mock_prefetch.return_value = (FULL_PAGE_HTML, "text/html; charset=utf-8")
        mock_playwright.return_value = FULL_PAGE_HTML

        runner = CliRunner()
        result = runner.invoke(main, ["https://example.com/article", "--raw"])

        assert result.exit_code == 0
        assert "<!DOCTYPE html>" in result.output or "<html>" in result.output
        assert not result.output.startswith("---\n")

    @patch("playwrightmd.http_prefetch")
    def test_cloudflare_markdown_no_double_frontmatter(self, mock_prefetch):
        """When Cloudflare returns markdown (is_markdown=True), don't add frontmatter."""
        existing_md = "---\ntitle: Already There\n---\n\n# Heading\n\nContent here.\n"
        mock_prefetch.return_value = (existing_md, "text/markdown")

        runner = CliRunner()
        result = runner.invoke(main, ["https://example.com/page"])

        assert result.exit_code == 0
        # Should have exactly one frontmatter block, not two
        assert result.output.count("---\n") <= 2  # opening + closing
