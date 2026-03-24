#!/usr/bin/env python3
"""
playwrightmd - Convert HTML to Markdown using Playwright

Supports three input modes:
  - URL: playwrightmd https://example.com -o output.md
  - File: playwrightmd page.html -o output.md
  - Stdin: cat page.html | playwrightmd -o output.md
"""

from importlib.metadata import version as get_version

__version__ = get_version("playwrightmd")

import re
import sys
import json
import urllib.error
import urllib.request
from enum import Enum
from types import MappingProxyType
from typing import Literal, cast
from pathlib import Path
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

import click
from bs4 import Comment, BeautifulSoup
from wcwidth import wcswidth
from markdownify import markdownify as md
from patchright.sync_api import (
    Error as PlaywrightError,
    TimeoutError as PlaywrightTimeout,
    sync_playwright,
)


class InputType(Enum):
    URL = "url"
    FILE = "file"
    STDIN = "stdin"


# =============================================================================
# Content Extraction Constants
# =============================================================================

# Entry point elements for finding main content (priority order)
ENTRY_POINT_ELEMENTS = [
    "#post",
    ".post-content",
    ".article-content",
    "#article-content",
    ".article_post",
    ".article-wrapper",
    ".entry-content",
    ".content-article",
    ".instapaper_body",
    ".post",
    ".markdown-body",
    "article",
    '[role="article"]',
    "main",
    '[role="main"]',
]

# Elements to remove exactly
EXACT_SELECTORS = [
    # scripts, styles
    "noscript",
    'script:not([type^="math/"])',
    "style",
    "meta",
    "link",
    # ads
    '.ad:not([class*="gradient"])',
    '[class^="ad-" i]',
    '[class$="-ad" i]',
    '[id^="ad-" i]',
    '[id$="-ad" i]',
    '[role="banner" i]',
    ".promo",
    ".alert",
    # comments
    '[id="comments" i]',
    '[id="comment" i]',
    # header, nav
    "header",
    ".header:not(.banner)",
    "#header",
    "nav",
    ".navigation",
    "#navigation",
    '[role="navigation" i]',
    '[role="dialog" i]',
    '[role*="complementary" i]',
    '[class*="pagination" i]',
    ".menu",
    # metadata
    ".author",
    '[class$="_bio"]',
    "#categories",
    ".contributor",
    ".date",
    "#date",
    "[data-date]",
    ".entry-meta",
    ".meta",
    ".tags",
    "#tags",
    ".toc",
    "#toc",
    ".headline",
    "#headline",
    "#title",
    '[href*="/tag/"]',
    '[href*="/tags/"]',
    '[href*="/topics"]',
    '[href*="author"]',
    '[href*="#toc"]',
    '[href="#top"]',
    '[src*="author"]',
    # footer
    "footer",
    # inputs, forms
    ".aside",
    'aside:not([class*="callout"])',
    "button",
    "canvas",
    "dialog",
    "fieldset",
    "form",
    'input:not([type="checkbox"])',
    "label",
    "option",
    "select",
    "textarea",
    # hidden (note: [hidden] is handled separately by _remove_hidden_elements
    # to preserve Next.js RSC streaming containers that hold article content)
    '[aria-hidden="true"]:not([class*="math"])',
    '[style*="display: none"]:not([class*="math"])',
    '[style*="display:none"]:not([class*="math"])',
    '[style*="visibility: hidden"]',
    '[style*="visibility:hidden"]',
    ".hidden",
    ".invisible",
    # iframes (except video embeds)
    'iframe:not([src*="youtube"]):not([src*="youtu.be"]):not([src*="vimeo"]):not([src*="twitter"]):not([src*="x.com"])',
    # logos
    '[class="logo" i]',
    "#logo",
    # newsletter
    "#newsletter",
    ".subscribe",
    # hidden for print
    ".noprint",
    '[data-print-layout="hide" i]',
    # sidebar
    ".sidebar",
    "#sidebar",
    # other
    ".copyright",
    "#copyright",
    ".licensebox",
    "#page-info",
    "#rss",
    "#feed",
]

# Partial match patterns for removal (case insensitive)
PARTIAL_PATTERNS = [
    "a-statement",
    "access-wall",
    "activitypub",
    "actioncall",
    "addcomment",
    "advert",
    "after_content",
    "afterpost",
    "-alert-",
    "appendix",
    "_archive",
    "around-the-web",
    "article-author",
    "article-banner",
    "article-bottom",
    "article-card",
    "article-date",
    "article-header",
    "article-meta",
    "article-snippet",
    "article-tags",
    "article-title",
    "article-topics",
    "author-bio",
    "author-box",
    "author-info",
    "authored-by",
    "avatar",
    "back-to-top",
    "backlink",
    "bio-block",
    "blog-pager",
    "bookmark-",
    "bottomnav",
    "bottom-of-article",
    "breadcrumb",
    "byline",
    "captcha",
    "card-text",
    "card-media",
    "carousel-container",
    "catlinks",
    "_categories",
    "chapter-list",
    "comments",
    "commentbox",
    "comment-button",
    "comment-content",
    "comment-form",
    "comment-thread",
    "complementary",
    "consent",
    "content-card",
    "context-widget",
    "created-date",
    "creative-commons",
    "_cta",
    "-cta",
    "cta-",
    "dateline",
    "disclaimer",
    "disclosure",
    "discussion",
    "disqus",
    "donate",
    "donation",
    "dropdown",
    "emailsignup",
    "engagement-widget",
    "entry-author-info",
    "entry-categories",
    "entry-date",
    "entry-title",
    "-error",
    "facebook",
    "favorite",
    "featured-content",
    "feedback",
    "feed-links",
    "floating-vid",
    "follower",
    "footnote-back",
    "form-group",
    "for-you",
    "frontmatter",
    "further-reading",
    "gated-",
    "gh-feed",
    "gist-meta",
    "goog-",
    "graph-view",
    "hamburger",
    "header-logo",
    "hero-list",
    "hide-for-print",
    "hide-print",
    "hidden-print",
    "infoline",
    "interlude",
    "interaction",
    "invisible",
    "jumplink",
    "keepreading",
    "keep-reading",
    "keyword_wrap",
    "kicker",
    "labstab",
    "-labels",
    "lastupdated",
    "latest-content",
    "-license",
    "license-",
    "lightbox-popup",
    "like-button",
    "link-box",
    "links-grid",
    "links-title",
    "loading",
    "logo_container",
    "masthead",
    "marketing",
    "-menu",
    "menu-",
    "metadata",
    "might-like",
    "minibio",
    "more-about",
    "_modal",
    "-modal",
    "more-",
    "morenews",
    "morestories",
    "most-read",
    "mw-editsection",
    "mw-cite-backlink",
    "nav-",
    "nav_",
    "navigation-post",
    "next-",
    "newsletter_",
    "newsletterbanner",
    "newsletter-form",
    "newsletter-signup",
    "not-found",
    "nomobile",
    "open-slideshow",
    "other-blogs",
    "outline-view",
    "pagehead",
    "page-header",
    "page-title",
    "paywall",
    "-partners",
    "permission-",
    "plea",
    "popular",
    "post-author",
    "post-bottom",
    "postcomment",
    "postdate",
    "post-date",
    "post-details",
    "post-feeds",
    "post-info",
    "post-links",
    "postlist",
    "post-meta",
    "post-navigation",
    "post-preview",
    "post-snippet",
    "post-tax",
    "post-tag",
    "post-title",
    "post-ufi-button",
    "prev-post",
    "prevnext",
    "prev-next",
    "previousnext",
    "print-none",
    "print-header",
    "privacy-notice",
    "privacy-settings",
    "profile",
    "promo_article",
    "promo-bar",
    "promo-box",
    "pubdate",
    "pub_date",
    "pub-date",
    "publish-date",
    "qr-code",
    "qr_code",
    "_rail",
    "ratingssection",
    "read_also",
    "readmore",
    "read-next",
    "read_time",
    "reading-list",
    "recent-",
    "recentpost",
    "recommend",
    "recirc",
    "register",
    "related",
    "relevant",
    "reversefootnote",
    "_rss",
    "rss-link",
    "screen-reader-text",
    "scroll_to",
    "_search",
    "-search",
    "section-nav",
    "series-banner",
    "share-box",
    "sharedaddy",
    "share-icons",
    "share-post",
    "share-section",
    "sidebar-content",
    "sidebar-wrapper",
    "side-box",
    "side-logo",
    "sign-in-gate",
    "similar-",
    "site-index",
    "site-header",
    "site-logo",
    "site-name",
    "skip-content",
    "skip-to-content",
    "skip-link",
    "-slider",
    "slug-wrap",
    "social-author",
    "social-shar",
    "social-date",
    "speechify-ignore",
    "speedbump",
    "sponsor",
    "sr-only",
    "_stats",
    "story-date",
    "story-navigation",
    "storyreadtime",
    "subject-label",
    "subhead",
    "submenu",
    "-subscribe-",
    "subscriber-drive",
    "subscription-",
    "_tags",
    "tags__item",
    "taxonomy",
    "table-of-contents",
    "tabs-",
    "timestamp",
    "time-read",
    "tip_off",
    "-tout-",
    "toc-container",
    "tooltip",
    "topbar",
    "topic-list",
    "top-wrapper",
    "tree-item",
    "trending",
    "trust-feat",
    "trust-badge",
    "twitter",
    "u-hide",
    "upsell",
    "visually-hidden",
    "welcomebox",
]

# Navigation indicators (for text content detection)
NAVIGATION_INDICATORS = [
    "advertisement",
    "all rights reserved",
    "banner",
    "cookie",
    "comments",
    "copyright",
    "follow me",
    "follow us",
    "footer",
    "header",
    "homepage",
    "login",
    "menu",
    "more articles",
    "more like this",
    "most read",
    "nav",
    "navigation",
    "newsletter",
    "popular",
    "privacy",
    "recommended",
    "register",
    "related",
    "responses",
    "share",
    "sidebar",
    "sign in",
    "sign up",
    "signup",
    "social",
    "sponsored",
    "subscribe",
    "terms",
    "trending",
]

# Content indicators (positive signals)
CONTENT_INDICATORS = [
    "admonition",
    "article",
    "content",
    "entry",
    "image",
    "img",
    "font",
    "figure",
    "figcaption",
    "pre",
    "main",
    "post",
    "story",
    "table",
]

# Footnote selectors
FOOTNOTE_INLINE_SELECTORS = [
    "sup.reference",
    'sup[id^="fnr"]',
    'span[id^="fnr"]',
    'span[class*="footnote_ref"]',
    'span[class*="footnote-ref"]',
    "a.citation",
    'a[href^="#fn"]',
    'a[href^="#cite"]',
    "a.footnote-anchor",
    'a[role="doc-biblioref"]',
]

FOOTNOTE_LIST_SELECTORS = [
    "div.footnote ol",
    "div.footnotes ol",
    'div[role="doc-endnotes"]',
    "ol.footnotes-list",
    "ol.footnotes",
    "ol.references",
    "section.footnotes ol",
]


# =============================================================================
# Page Metadata & Frontmatter
# =============================================================================


@dataclass
class PageMetadata:
    """Structured metadata extracted from a web page."""

    title: str | None = None
    author: str | None = None
    published: str | None = None
    description: str | None = None
    source: str | None = None
    site: str | None = None
    image: str | None = None


# Article-like JSON-LD types whose metadata we extract
_JSONLD_ARTICLE_TYPES = frozenset(
    {"Article", "BlogPosting", "NewsArticle", "TechArticle", "ScholarlyArticle", "Report"}
)


def extract_metadata(html: str, url: str) -> PageMetadata:
    """Extract page metadata from HTML <head> tags.

    Priority per field (first non-empty wins):
      title:       og:title > <title> > JSON-LD headline > twitter:title
      author:      article:author > meta[name=author] > JSON-LD author
      published:   article:published_time > JSON-LD datePublished
      description: og:description > meta[name=description] > JSON-LD > twitter:description
      site:        og:site_name > JSON-LD publisher
      image:       og:image
    """
    soup = BeautifulSoup(html, "lxml")

    def og(prop: str) -> str | None:
        tag = soup.find("meta", property=prop)
        return tag["content"].strip() if tag and tag.get("content") else None

    def meta_name(name: str) -> str | None:
        tag = soup.find("meta", attrs={"name": name})
        return tag["content"].strip() if tag and tag.get("content") else None

    def html_title() -> str | None:
        tag = soup.find("title")
        return tag.get_text(strip=True) if tag else None

    # Parse JSON-LD for article types
    jsonld_title = None
    jsonld_author = None
    jsonld_published = None
    jsonld_description = None
    jsonld_publisher = None

    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError):
            continue

        items = data if isinstance(data, list) else [data]
        for item in items:
            if not isinstance(item, dict):
                continue
            ld_type = item.get("@type", "")
            if ld_type not in _JSONLD_ARTICLE_TYPES:
                continue

            jsonld_title = jsonld_title or item.get("headline")
            jsonld_description = jsonld_description or item.get("description")
            jsonld_published = jsonld_published or item.get("datePublished")

            # Author: string, object, or array
            raw_author = item.get("author")
            if raw_author and not jsonld_author:
                if isinstance(raw_author, str):
                    jsonld_author = raw_author
                elif isinstance(raw_author, dict):
                    jsonld_author = raw_author.get("name")
                elif isinstance(raw_author, list):
                    names = []
                    for a in raw_author:
                        if isinstance(a, str):
                            names.append(a)
                        elif isinstance(a, dict) and a.get("name"):
                            names.append(a["name"])
                    jsonld_author = ", ".join(names) if names else None

            # Publisher
            raw_pub = item.get("publisher")
            if raw_pub and not jsonld_publisher:
                if isinstance(raw_pub, str):
                    jsonld_publisher = raw_pub
                elif isinstance(raw_pub, dict):
                    jsonld_publisher = raw_pub.get("name")

    return PageMetadata(
        title=og("og:title") or html_title() or jsonld_title or meta_name("twitter:title"),
        author=og("article:author") or meta_name("author") or jsonld_author,
        published=og("article:published_time") or jsonld_published,
        description=(
            og("og:description")
            or meta_name("description")
            or jsonld_description
            or meta_name("twitter:description")
        ),
        source=url,
        site=og("og:site_name") or jsonld_publisher,
        image=og("og:image"),
    )


# Frontmatter field order
_FRONTMATTER_FIELDS = ["title", "author", "published", "description", "site", "source", "image"]


def format_frontmatter(meta: PageMetadata) -> str:
    """Render PageMetadata as a YAML frontmatter block.

    Returns empty string if no meaningful fields are present
    (source-only is not considered meaningful).
    """
    pairs = []
    for field in _FRONTMATTER_FIELDS:
        value = getattr(meta, field)
        if value is not None:
            pairs.append((field, value))

    # Don't emit frontmatter if only source is present (or nothing)
    meaningful = [k for k, _ in pairs if k != "source"]
    if not meaningful:
        return ""

    lines = ["---"]
    for key, value in pairs:
        escaped = str(value).replace("\\", "\\\\").replace('"', '\\"')
        lines.append(f'{key}: "{escaped}"')
    lines.append("---")
    lines.append("")

    return "\n".join(lines)


# =============================================================================
# FxTwitter API Integration
# =============================================================================


@dataclass
class FxTwitterTweet:
    text: str
    author_name: str
    author_handle: str
    photos: list[str]
    article_title: str | None = None
    article_content: str | None = None
    article_cover: str | None = None


def is_x_twitter_url(url: str) -> bool:
    """Check if URL is from x.com or twitter.com."""
    parsed = urlparse(url)
    hostname = parsed.hostname or ""
    return hostname in ("x.com", "twitter.com") or hostname.endswith((".x.com", ".twitter.com"))


def extract_tweet_id(url: str) -> str | None:
    """Extract tweet/article ID from x.com/twitter.com URL."""
    match = re.search(r"/(status|article)/(\d+)", url)
    return match.group(2) if match else None


def extract_username(url: str) -> str | None:
    """Extract username from x.com/twitter.com URL."""
    match = re.search(r"/([a-zA-Z0-9_]{1,15})/(status|article)/", url)
    return match.group(1) if match else None


def fetch_fxtwitter(url: str, timeout: int = 30000) -> FxTwitterTweet | None:
    """
    Fetch tweet/article content from FxTwitter API.
    Returns None if fetch fails or content not found.
    """
    username = extract_username(url)
    tweet_id = extract_tweet_id(url)

    if not username or not tweet_id:
        return None

    api_url = f"https://api.fxtwitter.com/{username}/status/{tweet_id}"

    try:
        req = urllib.request.Request(
            api_url,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; playwrightmd/1.0)",
                "Accept": "application/json",
            },
        )

        with urllib.request.urlopen(req, timeout=timeout // 1000) as response:
            data = json.loads(response.read().decode("utf-8"))

        if data.get("code") != 200 or not data.get("tweet"):
            return None

        tweet = data["tweet"]

        # Handle article content
        article_title = None
        article_content = None
        article_cover = None

        if tweet.get("article"):
            article = tweet["article"]
            article_title = article.get("title", "")
            article_cover = (
                article.get("cover_media", {}).get("media_info", {}).get("original_img_url")
            )

            # Render article content from Draft.js blocks
            if "content" in article:
                article_content = render_article_content(article["content"])

        # Get text with facets (formatting)
        raw_text = tweet.get("raw_text", {})
        text = raw_text.get("text", tweet.get("text", ""))
        facets = raw_text.get("facets", [])

        # Apply facets for formatting
        if facets:
            text = apply_facets(text, facets)

        # Get photos
        photos = []
        if tweet.get("media", {}).get("photos"):
            photos = [p.get("url", "") for p in tweet["media"]["photos"] if p.get("url")]

        return FxTwitterTweet(
            text=text,
            author_name=tweet.get("author", {}).get("name", ""),
            author_handle=tweet.get("author", {}).get("screen_name", ""),
            photos=photos,
            article_title=article_title,
            article_content=article_content,
            article_cover=article_cover,
        )

    except (urllib.error.URLError, json.JSONDecodeError, KeyError):
        return None


def apply_facets(text: str, facets: list[dict]) -> str:
    """Apply formatting facets to text (italic, links, mentions)."""
    if not facets:
        return text

    # Filter out media facets
    facets = [f for f in facets if f.get("type") != "media"]

    markers = []
    for facet in facets:
        indices = facet.get("indices", [0, 0])
        f_type = facet.get("type", "")

        if f_type == "italic":
            markers.append((indices[0], "open", "<em>"))
            markers.append((indices[1], "close", "</em>"))
        elif f_type == "mention" and facet.get("text"):
            url = f"https://x.com/{facet['text']}"
            markers.append((indices[0], "open", f'<a href="{url}">'))
            markers.append((indices[1], "close", "</a>"))
        elif f_type == "url" and facet.get("original"):
            url = facet.get("replacement") or facet["original"]
            if facet.get("replacement"):
                # Use display text (e.g. "example.com/path…") so markdownify
                # produces [display](full_url) instead of <full_url> autolink.
                link_text = escape_html(facet.get("display") or url)
                link_html = f'<a href="{url}">{link_text}</a>'
                markers.append((indices[0], "replace_open", link_html))
                markers.append((indices[1], "replace_close", ""))
            else:
                markers.append((indices[0], "open", f'<a href="{url}">'))
                markers.append((indices[1], "close", "</a>"))

    return apply_markers(text, markers) if markers else text


def escape_html(text: str) -> str:
    """Escape HTML special characters."""
    return (
        text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    )


def apply_markers(text: str, markers: list[tuple[int, str, str]]) -> str:
    """Apply sorted (offset, open/close, tag) markers to text with HTML escaping.

    Shared by apply_facets() and render_inline_content() which both build
    a markers list then splice HTML tags into escaped text at byte offsets.
    """
    if not markers:
        return escape_html(text)

    # Sort: by offset, close before open at same position, replace_close before others
    def marker_sort_key(m: tuple[int, str, str]) -> tuple[int, int]:
        order = {"replace_close": 0, "close": 1, "open": 2, "replace_open": 3}
        return (m[0], order.get(m[1], 2))

    markers.sort(key=marker_sort_key)

    result: list[str] = []
    pos = 0
    for offset, kind, tag in markers:
        if kind == "replace_close":
            # Skip text from previous pos to this offset (consumed by replace_open)
            pos = offset
            continue
        if offset > pos:
            result.append(escape_html(text[pos:offset]))
        result.append(tag)
        if kind == "replace_open":
            # Skip the replaced text span — pos will be advanced by replace_close
            pos = offset
        else:
            pos = offset

    if pos < len(text):
        result.append(escape_html(text[pos:]))

    return "".join(result)


def render_article_content(content: dict) -> str:
    """Render Draft.js article content to HTML."""
    blocks = content.get("blocks", [])
    entity_map = content.get("entityMap", [])

    parts = []
    i = 0

    while i < len(blocks):
        block = blocks[i]

        # Group list items
        if block.get("type") == "unordered-list-item":
            items = []
            while i < len(blocks) and blocks[i].get("type") == "unordered-list-item":
                items.append(f"<li>{render_inline_content(blocks[i], entity_map)}</li>")
                i += 1
            parts.append(f"<ul>{''.join(items)}</ul>")
            continue

        html = render_block(block, entity_map)
        if html:
            parts.append(html)
        i += 1

    return "".join(parts)


def render_block(block: dict, entity_map: list) -> str:
    """Render a single Draft.js block to HTML."""
    text = block.get("text", "")
    block_type = block.get("type", "unstyled")

    if not text.strip() and block_type == "unstyled":
        return ""

    inline_content = render_inline_content(block, entity_map)

    if block_type == "unstyled":
        return f"<p>{inline_content}</p>"
    elif block_type == "header-two":
        return f"<h2>{inline_content}</h2>"
    elif block_type == "header-three":
        return f"<h3>{inline_content}</h3>"
    elif block_type == "atomic":
        return render_atomic_block(block, entity_map)
    else:
        return f"<p>{inline_content}</p>"


def render_inline_content(block: dict, entity_map: list) -> str:
    """Render inline content with formatting."""
    text = block.get("text", "")
    if not text:
        return ""

    markers = []

    # Process inline style ranges (bold)
    for style_range in block.get("inlineStyleRanges", []):
        if style_range.get("style") == "Bold":
            markers.append((style_range["offset"], "open", "<strong>"))
            markers.append((style_range["offset"] + style_range["length"], "close", "</strong>"))

    # Process entity ranges (links)
    for entity_range in block.get("entityRanges", []):
        key = str(entity_range.get("key", ""))
        entity = next((e for e in entity_map if e.get("key") == key), None)
        if entity and entity.get("value", {}).get("type") == "LINK":
            url = entity["value"]["data"].get("url", "")
            markers.append((entity_range["offset"], "open", f'<a href="{url}">'))
            markers.append((entity_range["offset"] + entity_range["length"], "close", "</a>"))

    # Process mentions
    for mention in block.get("data", {}).get("mentions", []):
        url = f"https://x.com/{mention.get('text', '')}"
        markers.append((mention["fromIndex"], "open", f'<a href="{url}">'))
        markers.append((mention["toIndex"], "close", "</a>"))

    # Process URLs
    for url_data in block.get("data", {}).get("urls", []):
        url = url_data.get("text", "")
        markers.append((url_data["fromIndex"], "open", f'<a href="{url}">'))
        markers.append((url_data["toIndex"], "close", "</a>"))

    return apply_markers(text, markers)


def render_atomic_block(block: dict, entity_map: list) -> str:
    """Render atomic blocks (media, code)."""
    entity_ranges = block.get("entityRanges", [])
    if not entity_ranges:
        return ""

    key = str(entity_ranges[0].get("key", ""))
    entity = next((e for e in entity_map if e.get("key") == key), None)
    if not entity:
        return ""

    entity_value = entity.get("value", {})
    entity_type = entity_value.get("type", "")

    if entity_type == "MARKDOWN":
        markdown = entity_value.get("data", {}).get("markdown", "")
        # Strip code fences
        match = re.match(r"^```(\w*)\n([\s\S]*?)\n?```$", markdown)
        if match:
            lang = match.group(1)
            code = match.group(2)
            lang_attr = f' class="language-{lang}" data-lang="{lang}"' if lang else ""
            return f"<pre><code{lang_attr}>{escape_html(code)}</code></pre>"
        return f"<pre><code>{escape_html(markdown)}</code></pre>"

    return ""


def fxtwitter_to_markdown(tweet: FxTwitterTweet, source_url: str) -> str:
    """Convert FxTwitter tweet/article to markdown."""
    meta = PageMetadata(
        title=tweet.article_title or f"Post by @{tweet.author_handle}",
        author=f"{tweet.author_name} (@{tweet.author_handle})",
        source=source_url,
        site="X (Twitter)",
    )
    frontmatter = format_frontmatter(meta)

    lines = []
    if frontmatter:
        lines.append(frontmatter)

    # Article content or tweet text
    if tweet.article_content:
        # Convert article HTML to markdown
        html = tweet.article_content
        if tweet.article_cover:
            html = f'<img src="{tweet.article_cover}" alt="Cover image">{html}'
        content_md = md(html, heading_style="atx", bullets="-")
        lines.append(content_md)
    else:
        # Regular tweet
        if tweet.text:
            content_md = md(tweet.text, heading_style="atx", bullets="-")
            lines.append(content_md)

        # Add photos
        for photo_url in tweet.photos:
            lines.append("")
            lines.append(f"![]({photo_url})")

    return "\n".join(lines)


# =============================================================================
# URL Detection and Input Handling
# =============================================================================


def detect_input_type(input_arg: str | None) -> InputType:
    """Detect whether input is a URL, file path, or stdin."""
    if input_arg is None or input_arg == "-":
        return InputType.STDIN
    if input_arg.startswith(("http://", "https://")):
        return InputType.URL
    if Path(input_arg).exists():
        return InputType.FILE
    # Assume URL if it looks like a domain
    if "." in input_arg and not input_arg.startswith("/"):
        return InputType.URL
    raise ValueError(f"Cannot determine input type for: {input_arg}")


DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"
)

WaitUntilType = Literal["load", "domcontentloaded", "networkidle", "commit"]

WAIT_UNTIL_CHOICES = list(WaitUntilType.__args__)  # type: ignore[attr-defined]


# Chromium args that reduce detection surface and speed up launch.
# Curated from Scrapling's engine constants — only args relevant to
# a single-page fetcher (no crawler-specific flags like page pooling).
STEALTH_ARGS = (
    "--disable-blink-features=AutomationControlled",
    "--no-first-run",
    "--no-service-autorun",
    "--no-pings",
    "--disable-infobars",
    "--disable-breakpad",
    "--disable-hang-monitor",
    "--disable-session-crashed-bubble",
    "--password-store=basic",
    "--homepage=about:blank",
    # Fingerprint hardening
    "--disable-sync",
    "--disable-translate",
    "--disable-logging",
    "--mute-audio",
    "--hide-scrollbars",
    "--lang=en-US",
    "--accept-lang=en-US",
    "--start-maximized",
    "--force-color-profile=srgb",
    "--font-render-hinting=none",
    "--disable-client-side-phishing-detection",
    "--disable-background-networking",
    "--metrics-recording-only",
    "--safebrowsing-disable-auto-update",
    "--autoplay-policy=user-gesture-required",
    # WebRTC leak prevention (important when using proxies)
    "--webrtc-ip-handling-policy=disable_non_proxied_udp",
    "--force-webrtc-ip-handling-policy",
    # Misc performance/stealth
    "--disable-dev-shm-usage",
    "--disable-renderer-backgrounding",
    "--disable-backgrounding-occluded-windows",
    "--disable-ipc-flooding-protection",
    "--disable-background-timer-throttling",
    "--enable-features=NetworkService,NetworkServiceInProcess",
    "--disable-features=AudioServiceOutOfProcess,TranslateUI",
    "--blink-settings=primaryHoverType=2,availableHoverTypes=2,primaryPointerType=4,availablePointerTypes=4",
)

# Context options that present a realistic desktop browser fingerprint.
# Frozen via MappingProxyType so callers can't accidentally mutate shared state.
STEALTH_CONTEXT_OPTIONS: MappingProxyType[str, object] = MappingProxyType({
    "screen": MappingProxyType({"width": 1920, "height": 1080}),
    "viewport": MappingProxyType({"width": 1920, "height": 1080}),
    "locale": "en-US",
    "timezone_id": "America/New_York",
    "color_scheme": "dark",
    "device_scale_factor": 2,
    "is_mobile": False,
    "has_touch": False,
    "ignore_https_errors": True,
})


def fetch_with_playwright(
    url: str,
    timeout: int = 30000,
    wait_for: str | None = None,
    user_agent: str | None = None,
    proxy_url: str | None = None,
    headless: bool = True,
    wait_until: WaitUntilType = "domcontentloaded",
) -> str:
    """Fetch URL using Playwright (patchright) and return rendered HTML."""
    with sync_playwright() as p:
        launch_args: dict = {
            "headless": headless,
            "args": list(STEALTH_ARGS),
        }

        if proxy_url:
            launch_args["proxy"] = {"server": proxy_url}

        browser = p.chromium.launch(**launch_args)

        # Unfreeze MappingProxyType into plain dicts for patchright's API
        context_opts: dict = {
            k: dict(v) if isinstance(v, MappingProxyType) else v
            for k, v in STEALTH_CONTEXT_OPTIONS.items()
        }
        context_opts["user_agent"] = user_agent or DEFAULT_USER_AGENT

        context = browser.new_context(**context_opts)

        page = context.new_page()

        # Cloudflare Markdown for Agents support
        page.set_extra_http_headers({"Accept": "text/markdown, text/html"})

        try:
            page.goto(url, timeout=timeout, wait_until=wait_until)

            if wait_for:
                page.wait_for_selector(wait_for, timeout=timeout)

            html = page.content()
        finally:
            context.close()
            browser.close()

    return html


def render_local_html(
    html_content: str,
    timeout: int = 30000,
    headless: bool = True,
    wait_until: WaitUntilType = "domcontentloaded",
) -> str:
    """Render local HTML with patchright to execute any JavaScript.

    No stealth args needed -- local content never contacts a remote server.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page()

        try:
            page.set_content(html_content, timeout=timeout, wait_until=wait_until)
            rendered_html = page.content()
        finally:
            browser.close()

    return rendered_html


# =============================================================================
# Content Extraction Module
# =============================================================================
#
# Readability-style content extraction pipeline. Selects the "main content"
# from a full HTML document and prepares it for markdown conversion.
#
# UX Design Goal
# --------------
# Given any web page, produce a clean reading experience: the article body
# with images and code blocks, free of chrome (nav, ads, sidebars, metadata).
# When in doubt, prefer losing marginal content over including noise.
#
# Pipeline (invoked by clean_html)
# --------------------------------
#
#   Raw HTML string
#        |
#        v
#   +-----------------------+
#   | BeautifulSoup parse   |  "lxml" parser
#   +-----------------------+
#        |
#        v
#   +-----------------------+
#   | Exact selector strip  |  Remove ~100 CSS selectors: <script>, <nav>,
#   |                       |  <footer>, <aside>, ads, forms, hidden els...
#   +-----------------------+
#        |
#        v
#   +-----------------------+
#   | Partial pattern strip |  Remove elements whose class/id/data-testid
#   |                       |  contain any of ~300 substrings: "breadcrumb",
#   |                       |  "sidebar", "newsletter", "related", ...
#   +-----------------------+
#        |
#        v
#   +-----------------------+
#   | Main content finder   |  Try ENTRY_POINT_ELEMENTS in priority order
#   | (score_element)       |  (#post, .post-content, article, main, ...),
#   |                       |  score each by word count, <p> count, link
#   |                       |  density, content-class indicators, footnotes.
#   |                       |  Pick highest score. Fallback: <body>.
#   +-----------------------+
#        |
#        v
#   +-----------------------+
#   | URL resolution        |  href, src, srcset -> absolute (if base_url)
#   +-----------------------+
#        |
#        v
#   +-----------------------+
#   | Post-cleanup          |  - Remove HTML comments
#   |                       |  - H1 -> H2 (normalize_headings)
#   |                       |  - Strip trailing empty headings
#   |                       |  - Strip leading/trailing orphan <hr>
#   +-----------------------+
#        |
#        v
#   Cleaned HTML string (ready for markdownify)
#
# Selector override: when the user passes --selector/-s, the entire
# strip + score pipeline is skipped; we use that CSS selector directly.
#


def score_element(element) -> int:
    """Score an element for content likelihood."""
    score = 0

    # Get text content
    text = element.get_text() or ""
    words = len(text.split())
    score += words

    # Paragraph count
    paragraphs = len(element.find_all("p"))
    score += paragraphs * 10

    # Link density (penalize high link density)
    links = len(element.find_all("a"))
    link_density = links / (words or 1)
    score -= int(link_density * 5)

    # Image density
    images = len(element.find_all("img"))
    image_density = images / (words or 1)
    score -= int(image_density * 3)

    # Content indicators in class/id
    classes = element.get("class")
    class_name = " ".join(classes).lower() if classes else ""
    elem_id = (element.get("id") or "").lower()

    for indicator in CONTENT_INDICATORS:
        if indicator in class_name or indicator in elem_id:
            score += 15

    # Check for footnotes
    for selector in FOOTNOTE_INLINE_SELECTORS[:3]:
        try:
            if element.select_one(selector):
                score += 10
                break
        except Exception:
            pass

    return score


def find_main_content(soup):
    """Find the main content element using priority selectors and scoring."""
    candidates = []

    for selector in ENTRY_POINT_ELEMENTS:
        try:
            elements = soup.select(selector)
            for element in elements:
                # Calculate score
                element_score = score_element(element)
                # Add priority bonus (earlier selectors get higher bonus)
                priority_bonus = (
                    len(ENTRY_POINT_ELEMENTS) - ENTRY_POINT_ELEMENTS.index(selector)
                ) * 40
                candidates.append((element, element_score + priority_bonus))
        except Exception:
            continue

    if not candidates:
        return soup.body or soup

    # Sort by score descending
    candidates.sort(key=lambda x: x[1], reverse=True)

    return candidates[0][0]


_RE_BRACKET_EXPR = re.compile(r"\[[^\]]*\]")


def matches_partial_pattern(value: str | None) -> bool:
    """Check if value matches any partial removal pattern.

    Tailwind CSS uses bracket notation for arbitrary values, e.g.
    ``md:[--fd-nav-height:0px]``.  These can contain substrings like
    ``nav-`` that would false-positive against our partial patterns.
    Strip ``[...]`` fragments before matching so CSS custom-property
    references don't accidentally nuke content containers.
    """
    if not value:
        return False
    value_lower = _RE_BRACKET_EXPR.sub("", value).lower()
    return any(pattern in value_lower for pattern in PARTIAL_PATTERNS)


_PARTIAL_SKIP_TAGS = frozenset({"html", "head", "body", "[document]"})

# Minimum word count below which we retry with partial patterns disabled.
# Matches defuddle's self-healing approach: aggressive extraction that
# falls back to conservative mode when it over-strips.
_MIN_WORD_COUNT = 50


def _has_significant_text(element, threshold: int = 10) -> bool:
    """Check if an element contains paragraphs with real text content.

    Clutter blocks (navigation, social widgets, related posts) rarely
    have <p> tags with substantial prose.  Content wrappers do.
    """
    for p in element.find_all("p"):
        text = p.get_text(strip=True)
        if len(text.split()) >= threshold:
            return True
    return False


def _remove_by_partial_patterns(root, main_content) -> None:
    """Remove clutter elements inside *root* that match partial patterns.

    Two layers of protection prevent destroying real content:
    1. Ancestor protection — never remove an element whose subtree
       contains *main_content* (defuddle's ``el.contains(mainContent)``).
    2. Content-density guard — never remove an element that contains
       paragraphs with real text (>=20 words).  Clutter blocks rarely
       have substantial paragraph text; content wrappers do.
    """
    for element in list(root.find_all(True)):
        # Skip elements already destroyed by a parent's decompose()
        if element.attrs is None:
            continue
        if element.name in _PARTIAL_SKIP_TAGS:
            continue
        # Ancestor protection: never remove an element that contains
        # mainContent — this mirrors defuddle's el.contains(mainContent).
        if main_content in element.descendants:
            continue

        classes = element.get("class")
        class_attr = " ".join(classes) if classes else ""
        id_attr = element.get("id") or ""
        data_testid = element.get("data-testid") or ""
        data_test = element.get("data-test") or ""

        for attr_value in [class_attr, id_attr, data_testid, data_test]:
            if matches_partial_pattern(attr_value):
                # Content-density guard: don't remove elements with
                # substantial paragraph text — they're likely content
                # wrappers, not clutter.
                if _has_significant_text(element):
                    break
                element.decompose()
                break


def _word_count(element) -> int:
    """Count words in an element's text content."""
    text = element.get_text() or ""
    return len(text.split())


# Minimum word count for a [hidden] element to be considered content-bearing.
# Next.js RSC streaming containers hold full articles (hundreds of words);
# UI-only hidden elements (skip-nav links, tooltips) rarely exceed this.
_HIDDEN_CONTENT_THRESHOLD = 20


def _remove_hidden_elements(soup) -> None:
    """Remove [hidden] elements that don't contain substantial text.

    Next.js RSC streaming places server-rendered content inside
    ``<div hidden id="S:N">`` containers.  Blindly removing all
    ``[hidden]`` elements destroys the article body on these pages.
    Only remove hidden elements whose text content is below the
    threshold — real content containers are preserved.
    """
    for el in list(soup.select("[hidden]")):
        if _word_count(el) < _HIDDEN_CONTENT_THRESHOLD:
            el.decompose()


def _postprocess(main_content, soup, base_url: str | None) -> str:
    """Shared post-processing: URL resolution, comments, headings, dividers."""
    if base_url:
        resolve_relative_urls(main_content, base_url)

    for comment in main_content.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()

    normalize_headings(main_content)
    remove_trailing_headings(main_content)
    remove_orphaned_dividers(main_content)
    return str(main_content)


def clean_html(html: str, selector: str | None = None, base_url: str | None = None) -> str:
    """
    Remove scripts, styles, and other non-content elements.

    Pipeline order (inspired by defuddle):
      1. Exact selector removal  — safe, deterministic (scripts/nav/footer)
      2. find_main_content       — on intact DOM while content is still there
      3. Partial pattern removal  — scoped inside mainContent, with ancestor protection
      4. Word-count retry         — if <50 words, re-parse without partial patterns
      5. Post-processing          — URL resolution, heading normalization, etc.
    """
    soup = BeautifulSoup(html, "lxml")

    if selector:
        main_content = soup.select_one(selector)
        if not main_content:
            raise ValueError(f"Selector '{selector}' not found in page")
        return _postprocess(main_content, soup, base_url)

    # Step 1: Remove deterministic non-content elements (scripts, nav, footer, forms, etc.)
    for css_selector in EXACT_SELECTORS:
        try:
            for element in soup.select(css_selector):
                element.decompose()
        except Exception:
            continue

    # Step 1b: Content-aware [hidden] removal — skip elements with
    # substantial text (Next.js RSC streaming containers, etc.)
    _remove_hidden_elements(soup)

    # Step 2: Find main content BEFORE partial pattern removal.
    # The DOM still has all content-bearing elements intact.
    main_content = find_main_content(soup)

    # Step 3: Remove clutter inside main_content using partial patterns.
    # Ancestor protection prevents destroying main_content's parent chain.
    _remove_by_partial_patterns(main_content, main_content)

    # Step 4: Self-healing retry — if aggressive partial removal left
    # too little content, re-parse from scratch without partial patterns.
    # This mirrors defuddle's multi-level retry (wordCount < 200 → retry
    # with removePartialSelectors: false).
    wc = _word_count(main_content)
    if wc < _MIN_WORD_COUNT:
        soup_retry = BeautifulSoup(html, "lxml")
        for css_selector in EXACT_SELECTORS:
            try:
                for element in soup_retry.select(css_selector):
                    element.decompose()
            except Exception:
                continue
        _remove_hidden_elements(soup_retry)
        retry_content = find_main_content(soup_retry)
        retry_wc = _word_count(retry_content)
        # Keep retry only if it recovered substantially more content.
        # The retry must itself clear the minimum threshold AND be >2x
        # the original — this prevents small-but-legitimate pages from
        # having clutter restored just because it adds a few words.
        if retry_wc >= _MIN_WORD_COUNT and retry_wc > wc * 2:
            main_content = retry_content
            soup = soup_retry

    # Step 5: Post-processing
    return _postprocess(main_content, soup, base_url)


def resolve_relative_urls(element, base_url: str) -> None:
    """Convert relative URLs to absolute URLs in href, src, srcset attributes."""
    # Resolve href
    for el in element.find_all(href=True):
        href = el.get("href")
        if href and not href.startswith(("http://", "https://", "#", "javascript:", "mailto:")):
            el["href"] = urljoin(base_url, href)

    # Resolve src
    for el in element.find_all(src=True):
        src = el.get("src")
        if src and not src.startswith(("http://", "https://", "data:")):
            el["src"] = urljoin(base_url, src)

    # Resolve srcset
    for el in element.find_all(srcset=True):
        srcset = el.get("srcset")
        if srcset:
            entries = []
            for entry in srcset.split(","):
                parts = entry.strip().split()
                if parts:
                    url = parts[0]
                    if not url.startswith(("http://", "https://", "data:")):
                        url = urljoin(base_url, url)
                    entries.append(f"{url} {' '.join(parts[1:])}" if len(parts) > 1 else url)
            el["srcset"] = ", ".join(entries)


def normalize_headings(element) -> None:
    """Convert H1 to H2, keep other headings."""
    for h1 in element.find_all("h1"):
        h1.name = "h2"


def remove_trailing_headings(element) -> None:
    """Remove headings at the end with no content after them."""
    while True:
        # Get last child
        last_children = list(element.children)
        while last_children and not getattr(last_children[-1], "name", None):
            # Skip trailing whitespace text nodes
            if hasattr(last_children[-1], "strip"):
                if not last_children[-1].strip():
                    last_children.pop()
                else:
                    break
            else:
                last_children.pop()  # pragma: no cover

        if not last_children:
            break

        last = last_children[-1]
        if last.name in ("h1", "h2", "h3", "h4", "h5", "h6"):
            last.decompose()
        else:
            break


def remove_orphaned_dividers(element) -> None:
    """Remove leading and trailing HR elements."""
    from bs4.element import NavigableString

    # Remove leading HRs
    while True:
        first_child = getattr(element, "contents", [])
        if not first_child:
            break
        first = first_child[0]
        if hasattr(first, "name") and first.name == "hr":
            first.decompose()
        elif isinstance(first, NavigableString) and not str(first).strip():
            first.extract()
        else:
            break

    # Remove trailing HRs
    while True:
        last_child = getattr(element, "contents", [])
        if not last_child:
            break
        last = last_child[-1]
        if hasattr(last, "name") and last.name == "hr":
            last.decompose()
        elif isinstance(last, NavigableString) and not str(last).strip():
            last.extract()
        else:
            break


def _extract_code_language(el) -> str | None:
    """Extract language from a <pre> element's child <code> class.

    markdownify passes the <pre> tag to code_language_callback, but the
    language class (e.g. 'language-python') is typically on the inner
    <code> element.  Check both <pre> and its first <code> child.
    """
    # Check <pre> itself
    cls = el.get("class")
    if cls:
        return cls[0].replace("language-", "")
    # Check inner <code> child
    code = el.find("code")
    if code:
        cls = code.get("class")
        if cls:
            return cls[0].replace("language-", "")
    return None


def html_to_markdown(
    html: str,
    strip_tags: list[str] | None = None,
    selector: str | None = None,
    base_url: str | None = None,
) -> str:
    """Convert HTML to Markdown with content extraction."""
    cleaned = clean_html(html, selector=selector, base_url=base_url)

    # Convert to markdown with sensible defaults
    markdown = md(
        cleaned,
        heading_style="atx",
        bullets="-",
        code_language_callback=lambda el: _extract_code_language(el),
        strip=strip_tags or [],
    )

    # Clean up excessive whitespace
    lines = markdown.split("\n")
    cleaned_lines = []
    prev_empty = False

    for line in lines:
        is_empty = not line.strip()
        if is_empty and prev_empty:
            continue
        cleaned_lines.append(line.rstrip())
        prev_empty = is_empty

    return "\n".join(cleaned_lines).strip() + "\n"


def truncate_markdown_links(markdown: str, max_length: int = 42) -> str:
    """Truncate URLs in markdown links that exceed max_length display width."""

    # Pattern matches markdown links: [text](url) or [text](url "title")
    link_pattern = re.compile(r'\[([^\]]+)\]\(([^\s\)]+)(\s+"[^"]*")?\)')

    def truncate_url(match: re.Match) -> str:
        text = match.group(1)
        url = match.group(2)
        title = match.group(3) or ""

        # Use wcswidth to calculate display width (handles CJK/Unicode correctly)
        if wcswidth(url) > max_length:
            # Truncate to fit within max_length display width
            truncated = ""
            current_width = 0
            for char in url:
                char_width = wcswidth(char)
                if current_width + char_width > max_length - 1:  # Reserve 1 for ellipsis
                    break
                truncated += char
                current_width += char_width
            return f"[{text}]({truncated}…{title})"
        return match.group(0)

    return link_pattern.sub(truncate_url, markdown)


MARKDOWN_EXTENSIONS = frozenset(
    {
        ".md",
        ".markdown",
        ".mdown",
        ".mkdn",
        ".mkd",
        ".mdwn",
        ".mdtxt",
        ".mdtext",
        ".rmd",
    }
)

TEXT_EXTENSIONS = frozenset(
    {
        ".txt",
        ".text",
        ".json",
        ".xml",
        ".yaml",
        ".yml",
        ".csv",
        ".toml",
        ".ini",
        ".cfg",
        ".conf",
        ".log",
        ".rdf",
        ".n3",
        ".ttl",
        ".nt",
    }
)


def is_markdown_file(path: str) -> bool:
    """Check if file path has a markdown extension."""
    return Path(path).suffix.lower() in MARKDOWN_EXTENSIONS


def is_markdown_content_type(content_type: str | None) -> bool:
    """Check if Content-Type header indicates markdown."""
    if not content_type:
        return False
    return "markdown" in content_type.lower()


def is_text_file(path: str) -> bool:
    """Check if file path has a text file extension."""
    return Path(path).suffix.lower() in TEXT_EXTENSIONS


def is_text_content_type(content_type: str | None) -> bool:
    """Check if Content-Type header indicates plain text."""
    if not content_type:
        return False
    return "text/plain" in content_type.lower()


def is_binary_content_type(content_type: str | None) -> bool:
    """Check if Content-Type header indicates binary (non-text) content."""
    if not content_type:
        return False
    ct = content_type.lower().split(";")[0].strip()
    # text/* and application/json, application/xml are decodable
    if ct.startswith("text/"):
        return False
    if ct in ("application/json", "application/xml", "application/xhtml+xml"):
        return False
    return True


def http_prefetch(
    url: str,
    timeout: int = 30000,
    user_agent: str | None = None,
) -> tuple[str, str | None]:
    """Lightweight HTTP fetch with Cloudflare Markdown for Agents support.

    Returns (content, content_type). Logs markdown token count to stderr
    when the X-Markdown-Tokens header is present.
    Raises ValueError for binary (non-text) content types.
    """
    headers = {
        "User-Agent": user_agent or DEFAULT_USER_AGENT,
        "Accept": "text/markdown, text/html",
    }
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout // 1000) as response:
        content_type = response.getheader("Content-Type")

        if is_binary_content_type(content_type):
            ct_display = content_type.split(";")[0].strip() if content_type else content_type
            raise ValueError(
                f"URL points to binary content ({ct_display}), not a web page. "
                "playwrightmd only handles text-based content (HTML, Markdown, plain text)."
            )

        content = response.read().decode("utf-8")

        if is_markdown_content_type(content_type):
            markdown_tokens = response.getheader("X-Markdown-Tokens")
            if markdown_tokens:
                print(f"[Cloudflare] Markdown tokens: {markdown_tokens}", file=sys.stderr)

        return content, content_type


def _is_content_empty(html: str) -> bool:
    """Check if HTML produces no meaningful markdown after content extraction.

    Runs the same clean_html + markdownify pipeline used for final output.
    Returns True when the result is empty or whitespace-only — this reliably
    detects SPA/Next.js pages where the page shell (nav/footer) is present
    but the main content area hasn't been hydrated yet.
    """
    try:
        md = html_to_markdown(html)
        return len(md.strip()) == 0
    except Exception:
        return True


def get_html_content(
    input_arg: str | None,
    input_type: InputType,
    timeout: int = 30000,
    wait_for: str | None = None,
    no_js: bool = False,
    user_agent: str | None = None,
    proxy_url: str | None = None,
    headless: bool = True,
    wait_until: WaitUntilType = "domcontentloaded",
) -> tuple[str, bool, str | None]:
    """
    Get HTML content based on input type.
    Returns (content, is_markdown, base_url).

    For x.com/twitter.com URLs, uses FxTwitter API as fallback.
    """
    if input_type == InputType.URL:
        assert input_arg is not None
        url = input_arg
        # Add https:// if no protocol specified
        if not url.startswith(("http://", "https://")):
            url = "https://" + input_arg

        # Known text/markdown file extensions — simple fetch, no Playwright
        if is_markdown_file(url) or is_text_file(url):
            content, content_type = http_prefetch(url, timeout, user_agent)
            if is_markdown_content_type(content_type):
                return (content, True, url)
            if is_text_content_type(content_type):
                return (content, True, url)
            return (content, False, url)

        # x.com/twitter.com URLs — try FxTwitter API first
        if is_x_twitter_url(url):
            tweet = fetch_fxtwitter(url, timeout)
            if tweet:
                return (fxtwitter_to_markdown(tweet, url), True, url)

        # Lightweight HTTP prefetch — may short-circuit Playwright
        try:
            content, content_type = http_prefetch(url, timeout, user_agent)
            if is_markdown_content_type(content_type):
                return (content, True, url)
            # For HTML responses, skip Playwright if --no-js
            if no_js:
                return (content, False, url)
        except urllib.error.URLError:
            if no_js:
                raise

        # Fall back to Playwright for JS-rendered content
        playwright_kwargs = dict(
            timeout=timeout,
            wait_for=wait_for,
            user_agent=user_agent,
            proxy_url=proxy_url,
            headless=headless,
            wait_until=wait_until,
        )
        html = fetch_with_playwright(url, **playwright_kwargs)

        # Auto-retry with networkidle for SPA/Next.js pages that need hydration.
        # Only retry when using the default wait_until (domcontentloaded) — if the
        # user explicitly chose a strategy, respect their choice.
        if wait_until == "domcontentloaded" and _is_content_empty(html):
            click.echo(
                "Content empty after domcontentloaded, retrying with networkidle…",
                err=True,
            )
            html = fetch_with_playwright(url, **{**playwright_kwargs, "wait_until": "networkidle"})

        return (html, False, url)

    if input_type == InputType.FILE:
        assert input_arg is not None
        if is_markdown_file(input_arg) or is_text_file(input_arg):
            return (Path(input_arg).read_text(encoding="utf-8"), True, None)
        html = Path(input_arg).read_text(encoding="utf-8")
        if no_js:
            return (html, False, None)
        return (
            render_local_html(html, timeout=timeout, headless=headless, wait_until=wait_until),
            False,
            None,
        )

    if input_type == InputType.STDIN:
        html = sys.stdin.read()
        if no_js:
            return (html, False, None)
        return (
            render_local_html(html, timeout=timeout, headless=headless, wait_until=wait_until),
            False,
            None,
        )

    raise ValueError(f"Unknown input type: {input_type}")


def write_output(markdown: str, output: str | None) -> None:
    """Write markdown to file or stdout."""
    if output:
        Path(output).write_text(markdown, encoding="utf-8")
    else:
        click.echo(markdown, nl=False)


def validate_truncate_link(
    ctx: click.Context, param: click.Parameter, value: int | None
) -> int | None:
    """Callback: if --truncate-link is used without value, default to 42."""
    return value


@click.command()
@click.argument("input", required=False)
@click.argument("output", required=False)
@click.option(
    "-o", "--output", "output_opt", help="Output file (alternative to positional argument)"
)
@click.option(
    "--wait-for", metavar="SELECTOR", help="CSS selector to wait for before extracting content"
)
@click.option(
    "--timeout",
    type=int,
    default=30000,
    metavar="MS",
    help="Page load timeout in milliseconds (default: 30000)",
)
@click.option("--no-js", is_flag=True, help="Skip Playwright rendering, use simple HTTP fetch")
@click.option(
    "-s",
    "--selector",
    metavar="CSS",
    help="CSS selector for main content (e.g., 'article', '.content', '#main')",
)
@click.option("--user-agent", metavar="UA", help="Custom User-Agent string")
@click.option(
    "--proxy-url", metavar="URL", help="Proxy URL for requests (e.g., 'http://proxy:8080')"
)
@click.option(
    "--headless/--no-headless",
    default=True,
    help="Run browser in headless mode (default: headless)",
)
@click.option(
    "--wait-until",
    type=click.Choice(WAIT_UNTIL_CHOICES),
    default="domcontentloaded",
    help="When to consider navigation succeeded",
)
@click.option("--ignore-robots-txt", is_flag=True, help="Ignore robots.txt restrictions")
@click.option("--raw", is_flag=True, help="Output raw HTML without converting to Markdown")
@click.option(
    "--no-frontmatter", is_flag=True, help="Suppress YAML frontmatter in markdown output"
)
@click.option(
    "--truncate-link",
    type=int,
    default=None,
    is_eager=True,
    callback=validate_truncate_link,
    metavar="N",
    help="Truncate URLs in markdown links longer than N chars (default: 42)",
)
@click.option("--version", "show_version", is_flag=True, help="Show version information")
def main(
    input: str | None,
    output: str | None,
    output_opt: str | None,
    wait_for: str | None,
    timeout: int,
    no_js: bool,
    selector: str | None,
    user_agent: str | None,
    proxy_url: str | None,
    headless: bool,
    wait_until: str,
    ignore_robots_txt: bool,
    raw: bool,
    no_frontmatter: bool,
    truncate_link: int | None,
    show_version: bool,
) -> int:
    """Convert HTML to Markdown using Playwright for JS-rendered content.

    \b
    Examples:
      playwrightmd https://example.com output.md
      playwrightmd https://example.com -o output.md
      playwrightmd page.html output.md
      cat page.html | playwrightmd output.md
      curl -s https://example.com | playwrightmd
    """
    if show_version:
        click.secho("playwrightmd ", fg="cyan", bold=True, nl=False)
        click.secho(__version__, fg="green", bold=True)
        click.secho("Convert HTML to Markdown using Playwright", fg="white")
        return 0

    # Determine output file: prefer positional arg, fallback to -o/--output flag
    output_file = output if output else output_opt
    # Click guarantees wait_until is one of WAIT_UNTIL_CHOICES
    wait_until_typed = cast(WaitUntilType, wait_until)

    try:
        input_type = detect_input_type(input)

        content, is_markdown, base_url = get_html_content(
            input,
            input_type,
            timeout=timeout,
            wait_for=wait_for,
            no_js=no_js,
            user_agent=user_agent,
            proxy_url=proxy_url,
            headless=headless,
            wait_until=wait_until_typed,
        )

        if raw:
            out_content = content
        elif is_markdown:
            # Skip conversion, output raw markdown (Twitter/Cloudflare already formatted)
            out_content = content
        else:
            out_content = html_to_markdown(content, selector=selector, base_url=base_url)

            # Prepend YAML frontmatter with page metadata
            if not no_frontmatter and input_type == InputType.URL and input:
                url = input if input.startswith(("http://", "https://")) else "https://" + input
                frontmatter = format_frontmatter(extract_metadata(content, url))
                if frontmatter:
                    out_content = frontmatter + "\n" + out_content

        # Apply link truncation if requested
        if truncate_link is not None:
            out_content = truncate_markdown_links(out_content, max_length=truncate_link)

        write_output(out_content, output_file)

        return 0

    except PlaywrightTimeout:
        click.secho(f"Error: Page load timed out after {timeout}ms", fg="red", err=True)
        return 1
    except PlaywrightError as e:
        msg = str(e)
        if "Executable doesn't exist" in msg or "browserType.launch" in msg:
            click.secho(
                "Error: Browser not found. Run 'patchright install chromium' to install it.",
                fg="red",
                err=True,
            )
        else:
            click.secho(f"Error: {e}", fg="red", err=True)
        return 1
    except ValueError as e:
        click.secho(f"Error: {e}", fg="red", err=True)
        return 1
    except Exception as e:
        click.secho(f"Error: {e}", fg="red", err=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
