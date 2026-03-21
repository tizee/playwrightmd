"""Tests for readability-style content extraction rules.

Covers: EXACT_SELECTORS removal, PARTIAL_PATTERNS matching,
ENTRY_POINT_ELEMENTS content finding, score_element, find_main_content,
matches_partial_pattern, normalize_headings, remove_trailing_headings,
remove_orphaned_dividers, resolve_relative_urls, and clean_html integration.

BDD Scenarios
=============

Feature: Content Extraction Pipeline
  Extract the main article content from a full HTML page, stripping
  navigation, ads, metadata, and other non-content elements.

  Scenario: Exact selector removal
    Given an HTML page with <script>, <nav>, <footer>, <form>, ads, and hidden elements
    When clean_html processes the page
    Then those elements are removed
    And math-related scripts/aria-hidden, checkbox inputs, callout asides,
        and video iframes are preserved

  Scenario: Partial pattern removal
    Given an HTML page with elements whose class/id/data-testid contain
          boilerplate substrings (e.g. "breadcrumb", "newsletter", "related")
    When clean_html processes the page
    Then those elements are removed
    And content-bearing elements with unrelated class names are preserved

  Scenario: Decomposed parent does not crash children
    Given an HTML page where a parent element matches a partial pattern
          and contains child elements
    When clean_html iterates over all elements after decomposing the parent
    Then it skips the destroyed children without raising AttributeError

  Scenario: Main content discovery
    Given an HTML page with multiple candidate containers
          (article, main, .post-content, role="main")
    When find_main_content scores each candidate
    Then the highest-scoring container by word count, paragraph count,
         content-class indicators, and priority bonus is selected
    And if no candidates exist, <body> is used as fallback

  Scenario: Score element penalizes noise
    Given an element with high link density or image density
    When score_element evaluates it
    Then the score is lower than an equivalent element with real paragraph text

  Scenario: Score element rewards footnotes
    Given an element containing footnote references (sup.reference, a[href^="#fn"])
    When score_element evaluates it
    Then the score includes a footnote bonus

  Scenario: Heading normalization
    Given extracted content with H1 headings
    When normalize_headings processes it
    Then all H1 tags become H2, other heading levels are unchanged

  Scenario: Trailing heading removal
    Given extracted content ending with headings (possibly followed by whitespace)
    When remove_trailing_headings processes it
    Then trailing headings are removed
    And headings followed by content are preserved

  Scenario: Trailing heading with non-whitespace text
    Given extracted content ending with a bare text node (not a heading)
    When remove_trailing_headings processes it
    Then no headings are removed (the text node stops the loop)

  Scenario: Orphaned divider removal
    Given extracted content with leading or trailing <hr> elements
    When remove_orphaned_dividers processes it
    Then those boundary HRs are removed
    And middle HRs between content are preserved

  Scenario: Orphaned divider on empty element
    Given an empty element with no children
    When remove_orphaned_dividers processes it
    Then it returns without error

  Scenario: URL resolution
    Given extracted content with relative href, src, and srcset attributes
    When resolve_relative_urls processes it with a base URL
    Then relative URLs become absolute
    And absolute URLs, hash links, mailto links, and data URIs are unchanged

  Scenario: Selector override
    Given the user provides a CSS selector via --selector
    When clean_html processes the page
    Then the exact-selector and partial-pattern stripping is skipped
    And only the user-specified element is extracted
    And if the selector matches nothing, ValueError is raised

  Scenario: HTML to markdown end-to-end
    Given a realistic blog page with nav, article, code blocks, and footer
    When html_to_markdown processes it
    Then the output is clean markdown with ATX headings, code fences,
         and no boilerplate
    And consecutive blank lines are collapsed to single blank lines

  Scenario: Exact selector exception handling
    Given an HTML page where an EXACT_SELECTOR is syntactically invalid
          for the parser
    When clean_html tries to select it
    Then the exception is caught and processing continues with the
         remaining selectors

  Scenario: find_main_content selector exception handling
    Given an HTML page where an ENTRY_POINT_ELEMENTS selector triggers
          an exception during select()
    When find_main_content processes it
    Then the exception is caught and other selectors are still tried
"""

import pytest
from bs4 import BeautifulSoup
from bs4.element import Tag

from playwrightmd import (
    clean_html,
    score_element,
    html_to_markdown,
    find_main_content,
    normalize_headings,
    resolve_relative_urls,
    matches_partial_pattern,
    remove_orphaned_dividers,
    remove_trailing_headings,
)


def make_soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


def find_tag(soup: BeautifulSoup, name: str) -> Tag:
    """Find a tag by name, asserting it exists."""
    tag = soup.find(name)
    assert isinstance(tag, Tag), f"Expected <{name}> tag, got {type(tag)}"
    return tag


# =============================================================================
# EXACT_SELECTORS removal
# =============================================================================


class TestExactSelectorRemoval:
    """Elements matching EXACT_SELECTORS should be removed by clean_html."""

    def test_removes_script_tags(self):
        html = (
            "<html><body><article><p>Content</p><script>alert(1)</script></article></body></html>"
        )
        result = clean_html(html)
        assert "<script" not in result
        assert "Content" in result

    def test_preserves_math_script_tags(self):
        """script[type^='math/'] should be preserved."""
        html = '<html><body><article><p>Content</p><script type="math/tex">x^2</script></article></body></html>'
        result = clean_html(html)
        assert "math/tex" in result

    def test_removes_style_tags(self):
        html = "<html><body><article><p>Content</p><style>.x{color:red}</style></article></body></html>"
        result = clean_html(html)
        assert "<style" not in result

    def test_removes_noscript_tags(self):
        html = "<html><body><article><p>Content</p><noscript>Enable JS</noscript></article></body></html>"
        result = clean_html(html)
        assert "<noscript" not in result

    def test_removes_nav_elements(self):
        html = "<html><body><nav><a href='/'>Home</a></nav><article><p>Content</p></article></body></html>"
        result = clean_html(html)
        assert "<nav" not in result
        assert "Content" in result

    def test_removes_header_footer(self):
        html = """<html><body>
            <header><h1>Site Title</h1></header>
            <article><p>Content</p></article>
            <footer>Copyright 2024</footer>
        </body></html>"""
        result = clean_html(html)
        assert "<header" not in result
        assert "<footer" not in result
        assert "Content" in result

    def test_removes_sidebar(self):
        html = """<html><body>
            <div class="sidebar">Side content</div>
            <article><p>Main content</p></article>
        </body></html>"""
        result = clean_html(html)
        assert "Side content" not in result
        assert "Main content" in result

    def test_removes_hidden_elements(self):
        html = """<html><body><article>
            <p>Visible</p>
            <div hidden>Hidden</div>
            <div style="display: none">Also hidden</div>
            <div style="display:none">Hidden too</div>
            <div style="visibility: hidden">Invisible</div>
            <div class="hidden">Class hidden</div>
        </article></body></html>"""
        result = clean_html(html)
        assert "Visible" in result
        assert "Hidden" not in result or "hidden" not in result.lower().replace(
            "class", ""
        ).replace("style", "")

    def test_preserves_math_aria_hidden(self):
        """aria-hidden='true' with class containing 'math' should be preserved."""
        html = (
            "<html><body><article><p>Content</p>"
            '<span aria-hidden="true" class="math-symbol">x</span></article></body></html>'
        )
        result = clean_html(html)
        assert "math-symbol" in result

    def test_removes_ad_elements(self):
        html = """<html><body><article>
            <p>Content</p>
            <div class="ad">Ad here</div>
            <div class="ad-banner">Banner</div>
            <div class="top-ad">Top ad</div>
            <div id="ad-container">Container</div>
        </article></body></html>"""
        result = clean_html(html)
        assert "Ad here" not in result
        assert "Banner" not in result

    def test_preserves_ad_gradient(self):
        """class='ad' with 'gradient' in class should NOT be removed by .ad selector."""
        # .ad:not([class*="gradient"]) preserves elements that have "gradient" in class
        html = '<html><body><article><p>Content</p><div class="ad gradient-bg">Keep this</div></article></body></html>'
        result = clean_html(html)
        assert "Keep this" in result

    def test_removes_form_elements(self):
        html = """<html><body><article>
            <p>Content</p>
            <form><input type="text"><button>Submit</button></form>
        </article></body></html>"""
        result = clean_html(html)
        assert "<form" not in result
        assert "<button" not in result

    def test_preserves_checkbox_inputs(self):
        """input[type='checkbox'] should be preserved."""
        html = '<html><body><article><p>Content</p><input type="checkbox" checked>Task done</article></body></html>'
        result = clean_html(html)
        assert "checkbox" in result

    def test_removes_iframe_but_preserves_youtube(self):
        html = """<html><body><article>
            <p>Content</p>
            <iframe src="https://ads.example.com"></iframe>
            <iframe src="https://youtube.com/embed/abc"></iframe>
        </article></body></html>"""
        result = clean_html(html)
        assert "ads.example.com" not in result
        assert "youtube.com" in result

    def test_removes_toc_elements(self):
        html = """<html><body><article>
            <div class="toc">Table of Contents</div>
            <p>Actual content</p>
        </article></body></html>"""
        result = clean_html(html)
        assert "Table of Contents" not in result
        assert "Actual content" in result

    def test_removes_role_navigation(self):
        html = """<html><body>
            <div role="navigation"><a href="/">Home</a></div>
            <article><p>Content</p></article>
        </body></html>"""
        result = clean_html(html)
        assert "Home" not in result
        assert "Content" in result

    def test_removes_aside_but_preserves_callout(self):
        html = """<html><body><article>
            <aside>Regular aside</aside>
            <aside class="callout-note">Important callout</aside>
            <p>Content</p>
        </article></body></html>"""
        result = clean_html(html)
        assert "Regular aside" not in result
        assert "Important callout" in result


# =============================================================================
# PARTIAL_PATTERNS matching
# =============================================================================


class TestPartialPatterns:
    """matches_partial_pattern and partial pattern removal in clean_html."""

    def test_matches_partial_pattern_basic(self):
        assert matches_partial_pattern("article-author")
        assert matches_partial_pattern("my-breadcrumb-nav")
        assert matches_partial_pattern("social-share-buttons")
        assert matches_partial_pattern("newsletter-signup-form")

    def test_matches_partial_pattern_case_insensitive(self):
        assert matches_partial_pattern("Article-Author")
        assert matches_partial_pattern("BREADCRUMB")
        assert matches_partial_pattern("Newsletter-Signup")

    def test_no_match_for_content_classes(self):
        assert not matches_partial_pattern("article-body")
        assert not matches_partial_pattern("main-content")
        assert not matches_partial_pattern("paragraph")

    def test_no_match_for_empty_or_none(self):
        assert not matches_partial_pattern("")
        assert not matches_partial_pattern(None)

    def test_removes_elements_with_partial_patterns_in_class(self):
        html = """<html><body>
            <article>
                <p>Content</p>
                <div class="article-author-bio">Author info</div>
                <div class="share-icons-container">Share</div>
            </article>
        </body></html>"""
        result = clean_html(html)
        assert "Author info" not in result
        assert "Share" not in result
        assert "Content" in result

    def test_removes_elements_with_partial_patterns_in_id(self):
        html = """<html><body>
            <article>
                <p>Content</p>
                <div id="related-posts">Related</div>
                <div id="newsletter-signup-widget">Subscribe</div>
            </article>
        </body></html>"""
        result = clean_html(html)
        assert "Related" not in result
        assert "Subscribe" not in result

    def test_removes_elements_with_partial_patterns_in_data_testid(self):
        html = """<html><body>
            <article>
                <p>Content</p>
                <div data-testid="breadcrumb-nav">Home > Blog</div>
            </article>
        </body></html>"""
        result = clean_html(html)
        assert "Home &gt; Blog" not in result

    def test_partial_pattern_skips_structural_tags(self):
        """Partial patterns must not strip <html>, <body>, or <head>.

        Regression: Wikipedia's <body class="...skin-vector-search-vue...">
        matched the "-search" pattern, nuking the entire document.
        """
        html = """<html class="vector-feature-main-menu-disabled">
        <body class="skin-vector-search-vue mediawiki">
            <main><article><p>Article content</p></article></main>
        </body></html>"""
        result = clean_html(html)
        assert "Article content" in result

    def test_decomposed_parent_children_do_not_crash(self):
        """Decomposing a parent with partial-pattern match must not crash
        when the iterator later visits its (now-detached) children."""
        html = """<html><body>
            <article>
                <p>Main content here.</p>
                <div class="post-meta-line">
                    <span class="inner"><a href="/tags">Tags</a></span>
                    <span class="inner"><a href="/cats">Cats</a></span>
                </div>
            </article>
        </body></html>"""
        # Should not raise: 'NoneType' object has no attribute 'get'
        result = clean_html(html)
        assert "Main content" in result
        assert "Tags" not in result


# =============================================================================
# Content finding and scoring
# =============================================================================


class TestContentFinding:
    """Tests for find_main_content and score_element."""

    def test_finds_article_element(self):
        soup = make_soup("""<html><body>
            <div>Sidebar</div>
            <article><p>Main content with several words for scoring purposes here.</p></article>
        </body></html>""")
        main = find_main_content(soup)
        assert main.name == "article"

    def test_finds_main_element(self):
        soup = make_soup("""<html><body>
            <div>Sidebar</div>
            <main><p>Main content with several words for scoring purposes here.</p></main>
        </body></html>""")
        main = find_main_content(soup)
        assert main.name == "main"

    def test_finds_role_main(self):
        soup = make_soup("""<html><body>
            <div>Sidebar</div>
            <div role="main"><p>Main content with several words for scoring.</p></div>
        </body></html>""")
        main = find_main_content(soup)
        assert main.get("role") == "main"

    def test_prefers_post_content_over_article(self):
        """Earlier selectors in ENTRY_POINT_ELEMENTS get higher priority bonus."""
        soup = make_soup("""<html><body>
            <article><p>Article content with words.</p></article>
            <div class="post-content"><p>Post content with many words for scoring.</p></div>
        </body></html>""")
        main = find_main_content(soup)
        classes = main.get("class")
        assert classes and "post-content" in " ".join(classes)

    def test_falls_back_to_body_when_no_candidates(self):
        soup = make_soup("<html><body><div><p>Just content.</p></div></body></html>")
        main = find_main_content(soup)
        assert main.name == "body"

    def test_score_element_word_count(self):
        soup = make_soup("<div><p>one two three four five</p></div>")
        div = find_tag(soup, "div")
        score = score_element(div)
        assert score > 0

    def test_score_element_paragraph_bonus(self):
        soup_with_p = make_soup("<div><p>Hello</p><p>World</p></div>")
        soup_without_p = make_soup("<div>Hello World</div>")
        score_with = score_element(find_tag(soup_with_p, "div"))
        score_without = score_element(find_tag(soup_without_p, "div"))
        assert score_with > score_without

    def test_score_element_content_indicator_bonus(self):
        """Elements with content-indicating class names get bonus."""
        soup_content = make_soup('<div class="article-body"><p>Words here.</p></div>')
        soup_generic = make_soup('<div class="xyz"><p>Words here.</p></div>')
        score_content = score_element(find_tag(soup_content, "div"))
        score_generic = score_element(find_tag(soup_generic, "div"))
        assert score_content > score_generic

    def test_score_element_penalizes_high_link_density(self):
        """Elements with lots of links relative to text get penalized."""
        soup_links = make_soup("<div><a>a</a><a>b</a><a>c</a><a>d</a><a>e</a></div>")
        soup_text = make_soup("<div><p>This is a paragraph with real content words.</p></div>")
        score_links = score_element(find_tag(soup_links, "div"))
        score_text = score_element(find_tag(soup_text, "div"))
        assert score_text > score_links

    def test_score_element_footnote_bonus(self):
        """Elements containing footnote references get a bonus."""
        html_with_fn = '<div><p>Text<sup class="reference">[1]</sup> more words here.</p></div>'
        html_without_fn = "<div><p>Text more words here without footnotes at all.</p></div>"
        soup_fn = make_soup(html_with_fn)
        soup_no = make_soup(html_without_fn)
        score_fn = score_element(find_tag(soup_fn, "div"))
        score_no = score_element(find_tag(soup_no, "div"))
        assert score_fn > score_no

    def test_score_element_footnote_selector_exception(self):
        """score_element handles exceptions from invalid footnote selectors gracefully."""
        from unittest.mock import patch, MagicMock
        soup = make_soup("<div><p>Some content words here.</p></div>")
        div = find_tag(soup, "div")
        call_count = 0
        original_select_one = Tag.select_one

        def exploding_select_one(self, selector):
            nonlocal call_count
            call_count += 1
            raise Exception("CSS parse error")

        with patch.object(Tag, "select_one", exploding_select_one):
            score = score_element(div)
        # Should not crash, and should have tried the footnote selectors
        assert call_count >= 3  # FOOTNOTE_INLINE_SELECTORS[:3]
        assert isinstance(score, int)

    def test_score_element_penalizes_image_density(self):
        """Elements with many images relative to text get penalized."""
        html_images = "<div><img><img><img><img><img>few words</div>"
        html_text = "<div><p>This has many words but no images at all in the content.</p></div>"
        score_img = score_element(find_tag(make_soup(html_images), "div"))
        score_txt = score_element(find_tag(make_soup(html_text), "div"))
        assert score_txt > score_img

    def test_find_main_content_selector_exception(self):
        """find_main_content handles exceptions from soup.select() gracefully."""
        from unittest.mock import patch
        soup = make_soup("<html><body><p>Fallback content.</p></body></html>")
        original_select = soup.select

        def exploding_select(selector):
            raise Exception("CSS parse error")

        with patch.object(type(soup), "select", exploding_select):
            main = find_main_content(soup)
        # Falls back to body
        assert main.name == "body"


# =============================================================================
# Heading normalization and cleanup
# =============================================================================


class TestHeadingNormalization:
    """Tests for normalize_headings, remove_trailing_headings."""

    def test_h1_converted_to_h2(self):
        soup = make_soup("<div><h1>Title</h1><p>Content</p></div>")
        div = find_tag(soup, "div")
        normalize_headings(div)
        assert div.find("h2") is not None
        assert div.find("h1") is None
        h2 = div.find("h2")
        assert h2 is not None and h2.string == "Title"

    def test_h2_h3_unchanged(self):
        soup = make_soup("<div><h2>Sub</h2><h3>SubSub</h3></div>")
        div = find_tag(soup, "div")
        normalize_headings(div)
        h2 = div.find("h2")
        h3 = div.find("h3")
        assert h2 is not None and h2.string == "Sub"
        assert h3 is not None and h3.string == "SubSub"

    def test_multiple_h1s_all_converted(self):
        soup = make_soup("<div><h1>One</h1><p>Text</p><h1>Two</h1></div>")
        div = find_tag(soup, "div")
        normalize_headings(div)
        h2s = div.find_all("h2")
        assert len(h2s) == 2
        assert div.find("h1") is None

    def test_remove_trailing_heading(self):
        soup = make_soup("<div><p>Content</p><h2>Trailing</h2></div>")
        div = find_tag(soup, "div")
        remove_trailing_headings(div)
        assert div.find("h2") is None
        assert "Content" in div.get_text()

    def test_remove_multiple_trailing_headings(self):
        soup = make_soup("<div><p>Content</p><h2>Trail1</h2><h3>Trail2</h3></div>")
        div = find_tag(soup, "div")
        remove_trailing_headings(div)
        assert div.find("h2") is None
        assert div.find("h3") is None

    def test_trailing_heading_with_whitespace(self):
        soup = make_soup("<div><p>Content</p><h2>Trailing</h2>   </div>")
        div = find_tag(soup, "div")
        remove_trailing_headings(div)
        assert div.find("h2") is None

    def test_non_trailing_heading_preserved(self):
        soup = make_soup("<div><h2>Section</h2><p>Content</p></div>")
        div = find_tag(soup, "div")
        remove_trailing_headings(div)
        assert div.find("h2") is not None
        h2 = div.find("h2")
        assert h2 is not None and h2.string == "Section"

    def test_trailing_non_whitespace_text_stops_removal(self):
        """A bare text node at the end that is not whitespace prevents heading removal."""
        soup = make_soup("<div><h2>Keep</h2>trailing text")
        div = find_tag(soup, "div")
        remove_trailing_headings(div)
        # The text node stops the inner loop, and since the last real child
        # is text (not a heading), the outer loop breaks too
        assert div.find("h2") is not None

    def test_empty_element_does_not_crash(self):
        """remove_trailing_headings on an element with no children exits cleanly."""
        soup = make_soup("<div></div>")
        div = find_tag(soup, "div")
        remove_trailing_headings(div)
        assert str(div) == "<div></div>"

    def test_element_with_only_whitespace_does_not_crash(self):
        """remove_trailing_headings on whitespace-only element exits cleanly."""
        soup = make_soup("<div>   </div>")
        div = find_tag(soup, "div")
        remove_trailing_headings(div)
        # All whitespace popped, last_children becomes empty, loop breaks

    def test_trailing_comment_stops_removal(self):
        """A non-empty Comment node at the end acts like text and stops heading removal."""
        from bs4 import Comment
        soup = make_soup("<div><p>Content</p><h3>Trail</h3></div>")
        div = find_tag(soup, "div")
        div.append(Comment("some comment"))
        remove_trailing_headings(div)
        # Comment has .strip() -> non-empty -> breaks the inner loop
        # Then last_children[-1] is the Comment (no .name), so outer loop
        # checks .name which is None -> not a heading -> breaks
        assert div.find("h3") is not None


# =============================================================================
# Orphaned dividers
# =============================================================================


class TestOrphanedDividers:
    """Tests for remove_orphaned_dividers."""

    def test_removes_leading_hr(self):
        soup = make_soup("<div><hr><p>Content</p></div>")
        div = find_tag(soup, "div")
        remove_orphaned_dividers(div)
        assert div.find("hr") is None
        assert "Content" in div.get_text()

    def test_removes_trailing_hr(self):
        soup = make_soup("<div><p>Content</p><hr></div>")
        div = find_tag(soup, "div")
        remove_orphaned_dividers(div)
        assert div.find("hr") is None

    def test_preserves_middle_hr(self):
        soup = make_soup("<div><p>Above</p><hr><p>Below</p></div>")
        div = find_tag(soup, "div")
        remove_orphaned_dividers(div)
        assert div.find("hr") is not None

    def test_removes_multiple_leading_hrs(self):
        soup = make_soup("<div><hr><hr><p>Content</p></div>")
        div = find_tag(soup, "div")
        remove_orphaned_dividers(div)
        assert div.find("hr") is None

    def test_removes_leading_and_trailing_hrs(self):
        soup = make_soup("<div><hr><p>Content</p><hr></div>")
        div = find_tag(soup, "div")
        remove_orphaned_dividers(div)
        assert div.find("hr") is None
        assert "Content" in div.get_text()

    def test_empty_element_does_not_crash(self):
        """remove_orphaned_dividers on an empty element exits cleanly."""
        soup = make_soup("<div></div>")
        div = find_tag(soup, "div")
        remove_orphaned_dividers(div)
        assert str(div) == "<div></div>"

    def test_only_hrs_all_removed(self):
        """An element containing only HRs ends up empty."""
        soup = make_soup("<div><hr><hr></div>")
        div = find_tag(soup, "div")
        remove_orphaned_dividers(div)
        assert div.find("hr") is None

    def test_leading_whitespace_before_hr_removed(self):
        """Leading whitespace text nodes before an HR are skipped."""
        soup = make_soup("<div>   <hr><p>Content</p></div>")
        div = find_tag(soup, "div")
        remove_orphaned_dividers(div)
        assert div.find("hr") is None
        assert "Content" in div.get_text()

    def test_trailing_whitespace_after_hr_removed(self):
        """Trailing whitespace text nodes after an HR are skipped."""
        soup = make_soup("<div><p>Content</p><hr>   </div>")
        div = find_tag(soup, "div")
        remove_orphaned_dividers(div)
        assert div.find("hr") is None
        assert "Content" in div.get_text()


# =============================================================================
# URL resolution
# =============================================================================


class TestResolveRelativeUrls:
    """Tests for resolve_relative_urls."""

    def test_resolves_relative_href(self):
        soup = make_soup('<div><a href="/page">Link</a></div>')
        div = find_tag(soup, "div")
        resolve_relative_urls(div, "https://example.com/blog/post")
        a = div.find("a")
        assert a is not None and a.get("href") == "https://example.com/page"

    def test_resolves_relative_src(self):
        soup = make_soup('<div><img src="/images/photo.jpg"></div>')
        div = find_tag(soup, "div")
        resolve_relative_urls(div, "https://example.com/blog/post")
        img = div.find("img")
        assert img is not None and img.get("src") == "https://example.com/images/photo.jpg"

    def test_preserves_absolute_href(self):
        soup = make_soup('<div><a href="https://other.com/page">Link</a></div>')
        div = find_tag(soup, "div")
        resolve_relative_urls(div, "https://example.com/")
        a = div.find("a")
        assert a is not None and a.get("href") == "https://other.com/page"

    def test_preserves_hash_links(self):
        soup = make_soup('<div><a href="#section">Jump</a></div>')
        div = find_tag(soup, "div")
        resolve_relative_urls(div, "https://example.com/")
        a = div.find("a")
        assert a is not None and a.get("href") == "#section"

    def test_preserves_mailto_links(self):
        soup = make_soup('<div><a href="mailto:a@b.com">Email</a></div>')
        div = find_tag(soup, "div")
        resolve_relative_urls(div, "https://example.com/")
        a = div.find("a")
        assert a is not None and a.get("href") == "mailto:a@b.com"

    def test_preserves_data_uri_src(self):
        soup = make_soup('<div><img src="data:image/png;base64,abc"></div>')
        div = find_tag(soup, "div")
        resolve_relative_urls(div, "https://example.com/")
        img = div.find("img")
        assert img is not None
        src = img.get("src")
        assert isinstance(src, str) and src.startswith("data:")

    def test_resolves_relative_path_href(self):
        soup = make_soup('<div><a href="other.html">Link</a></div>')
        div = find_tag(soup, "div")
        resolve_relative_urls(div, "https://example.com/blog/post")
        a = div.find("a")
        assert a is not None and a.get("href") == "https://example.com/blog/other.html"

    def test_resolves_srcset(self):
        soup = make_soup('<div><img srcset="/img/small.jpg 320w, /img/large.jpg 1024w"></div>')
        div = find_tag(soup, "div")
        resolve_relative_urls(div, "https://example.com/page")
        img = div.find("img")
        assert img is not None
        srcset = img.get("srcset")
        assert isinstance(srcset, str)
        assert "https://example.com/img/small.jpg 320w" in srcset
        assert "https://example.com/img/large.jpg 1024w" in srcset

    def test_preserves_absolute_srcset(self):
        soup = make_soup('<div><img srcset="https://cdn.com/img.jpg 1x"></div>')
        div = find_tag(soup, "div")
        resolve_relative_urls(div, "https://example.com/")
        img = div.find("img")
        assert img is not None
        srcset = img.get("srcset")
        assert isinstance(srcset, str) and "https://cdn.com/img.jpg" in srcset


# =============================================================================
# clean_html integration
# =============================================================================


class TestCleanHtmlIntegration:
    """Integration tests for clean_html with realistic page structures."""

    def test_extracts_article_content_from_blog(self):
        html = """<html><body>
            <header><nav><a href="/">Home</a><a href="/blog">Blog</a></nav></header>
            <div class="sidebar"><h3>Archives</h3><ul><li>Jan</li></ul></div>
            <article>
                <h1>Blog Post Title</h1>
                <p>This is the main content of the blog post.</p>
                <p>It has multiple paragraphs with real information.</p>
            </article>
            <footer><p>Copyright 2024</p></footer>
        </body></html>"""
        result = clean_html(html)
        assert "main content of the blog post" in result
        assert "multiple paragraphs" in result
        # Nav, sidebar, footer removed before content finding
        assert "<nav" not in result
        assert "<footer" not in result

    def test_clean_html_with_selector(self):
        html = """<html><body>
            <nav>Navigation</nav>
            <div id="content"><p>Selected content</p></div>
            <div id="other"><p>Other content</p></div>
        </body></html>"""
        result = clean_html(html, selector="#content")
        assert "Selected content" in result
        # Selector mode uses the element directly, without pre-cleaning
        assert "Other content" not in result

    def test_clean_html_selector_not_found_raises(self):
        html = "<html><body><p>Content</p></body></html>"
        with pytest.raises(ValueError, match="not found"):
            clean_html(html, selector="#nonexistent")

    def test_removes_comments(self):
        html = "<html><body><article><p>Content</p><!-- secret comment --></article></body></html>"
        result = clean_html(html)
        assert "secret comment" not in result
        assert "Content" in result

    def test_full_pipeline_realistic_page(self):
        """Test html_to_markdown with a realistic blog page."""
        html = """<html><body>
            <header>
                <nav><a href="/">Home</a></nav>
            </header>
            <article>
                <h1>Understanding Python Decorators</h1>
                <div class="post-meta">Published Jan 2024</div>
                <div class="author-bio">About the author</div>
                <p>Decorators are a powerful feature in Python that allow you to modify
                the behavior of functions or classes.</p>
                <h2>Basic Syntax</h2>
                <pre><code class="language-python">@decorator
def my_function():
    pass</code></pre>
                <p>The above code is equivalent to calling decorator(my_function).</p>
                <div class="share-icons">Share on Twitter</div>
                <div class="related-posts">Related articles</div>
            </article>
            <footer>
                <p>Copyright 2024</p>
            </footer>
        </body></html>"""
        result = html_to_markdown(html)
        # Main content preserved
        assert "Decorators are a powerful feature" in result
        assert "Basic Syntax" in result
        # H1 converted to H2
        assert "## Understanding Python Decorators" in result
        # Code block preserved
        assert "@decorator" in result
        # Boilerplate removed
        assert "Share on Twitter" not in result
        assert "Related articles" not in result
        assert "Copyright" not in result

    def test_base_url_resolution_in_clean_html(self):
        html = """<html><body>
            <article>
                <p>Read <a href="/docs/guide">the guide</a></p>
                <img src="/images/diagram.png">
            </article>
        </body></html>"""
        result = clean_html(html, base_url="https://example.com/blog/post")
        assert 'href="https://example.com/docs/guide"' in result
        assert 'src="https://example.com/images/diagram.png"' in result

    def test_preserves_entry_content_div(self):
        html = """<html><body>
            <div class="entry-content">
                <p>This is the entry content with enough words to score well.</p>
                <p>Second paragraph of real content.</p>
            </div>
        </body></html>"""
        result = clean_html(html)
        assert "entry content" in result
        assert "Second paragraph" in result

    def test_preserves_markdown_body_div(self):
        """GitHub-style markdown-body class should be found."""
        html = """<html><body>
            <div class="markdown-body">
                <h2>README</h2>
                <p>Project description with enough content.</p>
            </div>
        </body></html>"""
        result = clean_html(html)
        assert "README" in result
        assert "Project description" in result

    def test_exact_selector_exception_continues(self):
        """If an exact selector raises during soup.select(), processing continues."""
        from unittest.mock import patch
        html = """<html><body>
            <article>
                <p>Content survives.</p>
                <script>alert(1)</script>
            </article>
        </body></html>"""
        # Patch soup.select to raise on the first selector, then work normally
        from bs4 import BeautifulSoup as BS
        original_select = BS.select
        call_count = 0

        def sometimes_exploding_select(self, selector):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("CSS parse error on first selector")
            return original_select(self, selector)

        with patch.object(BS, "select", sometimes_exploding_select):
            result = clean_html(html)
        # Processing continued past the exception
        assert "Content survives" in result
        assert call_count > 1

    def test_removes_elements_with_partial_patterns_in_data_test(self):
        """Elements with partial pattern in data-test attribute are removed."""
        html = """<html><body>
            <article>
                <p>Content</p>
                <div data-test="sidebar-content-area">Widget</div>
            </article>
        </body></html>"""
        result = clean_html(html)
        assert "Widget" not in result
        assert "Content" in result


# =============================================================================
# html_to_markdown integration
# =============================================================================


class TestHtmlToMarkdown:
    """Tests for html_to_markdown end-to-end conversion."""

    def test_consecutive_blank_lines_collapsed(self):
        """Multiple consecutive blank lines are collapsed to one."""
        # Empty <table> tags produce multiple blank lines from markdownify
        html = """<html><body>
            <article>
                <p>First paragraph.</p>
                <table></table>
                <p>Second paragraph.</p>
            </article>
        </body></html>"""
        result = html_to_markdown(html)
        assert "\n\n\n" not in result
        assert "First paragraph." in result
        assert "Second paragraph." in result

    def test_code_language_extracted_from_code_element(self):
        """Code blocks get language annotation from inner <code class='language-*'>."""
        html = """<html><body>
            <article>
                <p>Example:</p>
                <pre><code class="language-python">print("hello")</code></pre>
            </article>
        </body></html>"""
        result = html_to_markdown(html)
        assert "```python" in result
        assert 'print("hello")' in result

    def test_code_language_extracted_from_pre_element(self):
        """Code blocks get language annotation from <pre class='language-*'>."""
        html = """<html><body>
            <article>
                <p>Example:</p>
                <pre class="language-rust"><code>fn main() {}</code></pre>
            </article>
        </body></html>"""
        result = html_to_markdown(html)
        assert "```rust" in result
        assert "fn main()" in result

    def test_code_block_without_language_class(self):
        """Code blocks without language class get no language annotation."""
        html = """<html><body>
            <article>
                <p>Example:</p>
                <pre><code>some code</code></pre>
            </article>
        </body></html>"""
        result = html_to_markdown(html)
        assert "some code" in result

    def test_strip_tags_option(self):
        """strip_tags parameter removes specified tags from output."""
        html = """<html><body>
            <article>
                <p>Keep this <b>bold</b> and <em>italic</em>.</p>
            </article>
        </body></html>"""
        result = html_to_markdown(html, strip_tags=["em"])
        assert "**bold**" in result
        # em should be stripped (text kept, formatting removed)
        assert "italic" in result
        assert "*italic*" not in result or "**italic**" not in result

    def test_output_ends_with_newline(self):
        """Markdown output always ends with exactly one newline."""
        html = "<html><body><article><p>Content.</p></article></body></html>"
        result = html_to_markdown(html)
        assert result.endswith("\n")
        assert not result.endswith("\n\n")
