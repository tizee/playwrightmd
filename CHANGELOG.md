# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/tizee/playwrightmd/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/tizee/playwrightmd/releases/tag/v0.3.0
[0.2.0]: https://github.com/tizee/playwrightmd/releases/tag/v0.2.0
