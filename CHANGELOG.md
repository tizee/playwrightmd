# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.5.0] - 2026-03-06

### Changed
- Replace playwright with patchright (patched Playwright fork) for stealth browser automation
- Add 30+ curated Chromium stealth args from Scrapling for anti-detection and fingerprint hardening
- Add realistic browser context options (screen size, color scheme, device scale factor, WebRTC leak prevention)
- Remove manual `navigator.webdriver` JavaScript hack (patchright handles this natively at CDP level)
- Update default User-Agent to match bundled Chromium 145

### Improved
- Freeze `STEALTH_CONTEXT_OPTIONS` with `MappingProxyType` to prevent accidental mutation of shared state
- Add narrow error catch for missing patchright browser with actionable install hint
- Skip stealth args in `render_local_html` (local content never contacts remote servers)
- Update Makefile to use `patchright install chromium` instead of `playwright install chromium`

## [0.4.3] - 2026-03-06

### Added
- FxTwitter API support for X/Twitter URLs — fetches tweet content without browser launch
- Readability-style content extraction with 600+ pattern removal rules
- Absolute URL resolution for relative links in markdown output
- Comprehensive test coverage for content extraction in test_readability.py
- pyright and ruff dev dependencies with full configuration
- Makefile targets for fmt, lint, and typecheck

### Changed
- Remove FxTwitter diagnostic prints from stderr for clean output

## [0.4.2] - 2026-03-03

### Changed
- Migrated from argparse to Click for modern CLI experience
- Added `--version` flag with colorful output (cyan/green)
- Error messages now displayed in red
- Version dynamically read from package metadata

## [0.4.1] - 2026-03-03

### Fixed
- HTTP prefetch now falls back to Playwright on HTTP errors (403, 500, etc.) and connection failures instead of crashing
- Added test coverage for prefetch fallback behavior

### Changed
- HTML file processing tests now use `--no-js` to avoid Playwright dependency in unit tests

## [0.4.0] - 2026-03-01

### Added
- HTTP prefetch before Playwright: all URL fetches now start with a lightweight urllib request with `Accept: text/markdown, text/html` header, returning markdown directly from Cloudflare-enabled sites without launching a browser

### Changed
- Default `--wait-until` changed from `networkidle` to `domcontentloaded` to avoid timeouts on sites with persistent background network activity (analytics, beacons)
- Removed secondary `networkidle` wait inside `fetch_with_playwright` that was forcing all wait strategies to degrade to `networkidle`

### Documentation
- Updated README.md with Cloudflare Markdown for Agents section, prefetch architecture, and new `--wait-until` default
- Updated AGENTS.md with two-tier fetching strategy and updated pipeline description

## [0.3.0] - 2026-02-13

### Added
- Cloudflare Markdown for Agents support: tool now sends `Accept: text/markdown, text/html` header to request Markdown directly from Cloudflare-enabled sites, reducing token consumption by ~80%
- Content-Type handling: automatically detects `text/markdown` response and skips HTML parsing
- X-Markdown-Tokens logging: logs token count to stderr for budget estimation when present

### Changed
- Improved URL fetch logic for markdown/text file extensions with Cloudflare fallback

### Fixed
- Accept header now properly set for all HTTP requests (urllib and Playwright)

### Documentation
- Updated AGENTS.md with Cloudflare Markdown for Agents documentation

## [0.2.0] - 2025-01-01

### Added
- Link truncation feature with `--truncate-link` CLI option
- CLI args overhaul with better argument handling
- Text file detection and passthrough handling (.txt, .json, .xml, .yaml, .csv, .toml, etc.)
- Automated testing for markdown and text file detection

### Added
- Initial release with HTML to Markdown conversion using Playwright

[Unreleased]: https://github.com/tizee/playwrightmd/compare/v0.5.0...HEAD
[0.5.0]: https://github.com/tizee/playwrightmd/compare/v0.4.3...v0.5.0
[0.4.3]: https://github.com/tizee/playwrightmd/compare/v0.4.2...v0.4.3
[0.4.2]: https://github.com/tizee/playwrightmd/releases/tag/v0.4.2
[0.4.1]: https://github.com/tizee/playwrightmd/releases/tag/v0.4.1
[0.4.0]: https://github.com/tizee/playwrightmd/releases/tag/v0.4.0
[0.3.0]: https://github.com/tizee/playwrightmd/releases/tag/v0.3.0
[0.2.0]: https://github.com/tizee/playwrightmd/releases/tag/v0.2.0
