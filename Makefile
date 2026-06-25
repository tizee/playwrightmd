.PHONY: install sync test dev clean help fmt lint typecheck clean-browsers _warn-orphans

# Patchright (patched playwright) browsers are stored in a shared system cache:
#   macOS:  ~/Library/Caches/ms-playwright/
#   Linux:  ~/.cache/ms-playwright/
# The install target uses a stamp file keyed to uv.lock so browsers are
# only reinstalled when dependencies change (i.e., patchright version bumps).

STAMP := .patchright-installed

# Cross-platform browser cache path
BROWSER_CACHE := $(shell \
	if [ "$$(uname -s)" = "Darwin" ]; then \
		echo "$$HOME/Library/Caches/ms-playwright"; \
	else \
		echo "$$HOME/.cache/ms-playwright"; \
	fi)

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: sync $(STAMP) ## Full setup: sync deps + install browsers
	@$(MAKE) --no-print-directory _warn-orphans

sync: ## Sync Python dependencies
	uv sync

$(STAMP): uv.lock
	uv run patchright install chromium
	@touch $@

_warn-orphans:
	@cache="$(BROWSER_CACHE)"; \
	if [ ! -d "$$cache" ]; then exit 0; fi; \
	active=$$(uv run python _check_browsers.py 2>/dev/null || echo ""); \
	if [ -z "$$active" ]; then exit 0; fi; \
	orphans=$$(find "$$cache" -maxdepth 1 -type d \( -name 'chromium-*' -o -name 'chromium_headless_shell-*' \) \
		| while read d; do \
			rev=$$(basename "$$d" | grep -oE '[0-9]+$$'); \
			if ! echo "$$active" | grep -qw "$$rev"; then \
				du -sh "$$d" 2>/dev/null; \
			fi; \
		done); \
	if [ -n "$$orphans" ]; then \
		echo ""; \
		echo "  WARNING: Orphaned browser revisions found in $$cache"; \
		echo "$$orphans" | while read line; do echo "    $$line"; done; \
		echo ""; \
		echo "  Run 'make clean-browsers' to reclaim disk space."; \
		echo ""; \
	fi

install-tool: sync ## Install as global uv tool + install browsers for it
	uv lock --upgrade-package patchright
	uv sync
	uv run patchright install chromium
	@touch $(STAMP)
	uv tool install . --reinstall
	uv tool run --from playwrightmd patchright install chromium
	@$(MAKE) --no-print-directory _warn-orphans

test: ## Run tests
	uv run pytest tests/ -v

fmt: ## Format code with ruff
	uv run ruff format src/ tests/

lint: ## Lint code with ruff
	uv run ruff check src/ tests/

typecheck: ## Type check with pyright
	uv run pyright

dev: install test ## Setup dev environment and run tests

clean-browsers: ## Remove orphaned browser revisions from shared cache
	@cache="$(BROWSER_CACHE)"; \
	if [ ! -d "$$cache" ]; then echo "No browser cache found at $$cache"; exit 0; fi; \
	active=$$(uv run python _check_browsers.py 2>/dev/null || echo ""); \
	if [ -z "$$active" ]; then echo "Cannot determine active browser revisions. Run 'make install' first."; exit 1; fi; \
	orphans=$$(find "$$cache" -maxdepth 1 -type d \( -name 'chromium-*' -o -name 'chromium_headless_shell-*' \) \
		| while read d; do \
			rev=$$(basename "$$d" | grep -oE '[0-9]+$$'); \
			if ! echo "$$active" | grep -qw "$$rev"; then \
				echo "$$d"; \
			fi; \
		done); \
	if [ -z "$$orphans" ]; then \
		echo "No orphaned browser revisions found."; \
	else \
		echo "Removing orphaned browser revisions:"; \
		for d in $$orphans; do \
			size=$$(du -sh "$$d" 2>/dev/null | cut -f1); \
			echo "  $$d ($$size)"; \
			rm -rf "$$d"; \
		done; \
		echo "Done."; \
	fi

clean: ## Remove build artifacts and caches
	rm -rf dist/ build/ *.egg-info .pytest_cache $(STAMP) .playwright-installed
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
