"""Tests for FxTwitter API integration: apply_facets, fxtwitter_to_markdown."""

from playwrightmd import apply_facets, FxTwitterTweet, fxtwitter_to_markdown


class TestApplyFacetsUrlReplacement:
    """t.co short links should be replaced with full URLs from facet replacement field."""

    def test_url_facet_uses_replacement_as_href(self):
        """When a url facet has a replacement field, the link href should use the full URL."""
        text = "Check this out https://t.co/abc123"
        facets = [
            {
                "type": "url",
                "indices": [15, 34],
                "original": "https://t.co/abc123",
                "replacement": "https://www.example.com/full/path",
                "display": "example.com/full/path",
            }
        ]
        result = apply_facets(text, facets)
        assert "https://www.example.com/full/path" in result
        assert "https://t.co/abc123" not in result

    def test_url_facet_replaces_tco_text_with_full_url(self):
        """The visible text span (t.co URL) should be replaced with the full URL."""
        text = "Read more: https://t.co/xyz789"
        facets = [
            {
                "type": "url",
                "indices": [11, 30],
                "original": "https://t.co/xyz789",
                "replacement": "https://blog.example.com/article",
                "display": "blog.example.com/article",
            }
        ]
        result = apply_facets(text, facets)
        # The rendered link text should show the full URL, not t.co
        assert "t.co" not in result

    def test_url_facet_without_replacement_keeps_original(self):
        """When no replacement field, fall back to using original as href."""
        text = "Link: https://example.com"
        facets = [
            {
                "type": "url",
                "indices": [6, 25],
                "original": "https://example.com",
            }
        ]
        result = apply_facets(text, facets)
        assert "https://example.com" in result

    def test_multiple_url_facets_all_replaced(self):
        """Multiple t.co links in one text should all be replaced."""
        text = "A https://t.co/aaa B https://t.co/bbb"
        facets = [
            {
                "type": "url",
                "indices": [2, 18],
                "original": "https://t.co/aaa",
                "replacement": "https://example.com/first",
                "display": "example.com/first",
            },
            {
                "type": "url",
                "indices": [21, 37],
                "original": "https://t.co/bbb",
                "replacement": "https://example.com/second",
                "display": "example.com/second",
            },
        ]
        result = apply_facets(text, facets)
        assert "https://example.com/first" in result
        assert "https://example.com/second" in result
        assert "t.co" not in result

    def test_url_facet_coexists_with_mention_and_italic(self):
        """URL replacement works alongside other facet types."""
        text = "@alice check https://t.co/abc"
        facets = [
            {
                "type": "mention",
                "indices": [0, 6],
                "text": "alice",
            },
            {
                "type": "url",
                "indices": [13, 29],
                "original": "https://t.co/abc",
                "replacement": "https://www.example.com/page",
                "display": "example.com/page",
            },
        ]
        result = apply_facets(text, facets)
        assert "https://x.com/alice" in result
        assert "https://www.example.com/page" in result
        assert "t.co" not in result


class TestFxTwitterToMarkdownUrlReplacement:
    """End-to-end: t.co links in tweet text should become full URLs in markdown output."""

    def test_tco_link_replaced_in_markdown_output(self):
        """fxtwitter_to_markdown should produce markdown with full URLs, not t.co."""
        # Simulate what fetch_fxtwitter returns after apply_facets
        # The text field contains HTML with proper links after apply_facets
        tweet = FxTwitterTweet(
            text='Read this <a href="https://www.example.com/article">https://www.example.com/article</a>',
            author_name="Test User",
            author_handle="testuser",
            photos=[],
        )
        md = fxtwitter_to_markdown(tweet, "https://x.com/testuser/status/123")
        assert "https://www.example.com/article" in md
        assert "t.co" not in md
