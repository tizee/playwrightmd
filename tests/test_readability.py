"""Tests for readability-style content extraction rules.

Covers: EXACT_SELECTORS removal, PARTIAL_PATTERNS matching,
ENTRY_POINT_ELEMENTS content finding, score_element, find_main_content,
matches_partial_pattern, normalize_headings, remove_trailing_headings,
remove_orphaned_dividers, resolve_relative_urls, and clean_html integration.
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
