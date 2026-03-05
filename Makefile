.PHONY: install sync test dev clean help fmt lint typecheck

# Playwright browsers are stored in a shared system cache:
#   macOS:  ~/Library/Caches/ms-playwright/
#   Linux:  ~/.cache/ms-playwright/
# The install target uses a stamp file keyed to uv.lock so browsers are
# only reinstalled when dependencies change (i.e., playwright version bumps).

STAMP := .playwright-installed

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: sync $(STAMP) ## Full setup: sync deps + install browsers

sync: ## Sync Python dependencies
	uv sync

$(STAMP): uv.lock
	uv run playwright install chromium
	@touch $@

install-tool: install ## Install as global uv tool
	uv tool install . --reinstall

test: ## Run tests
	uv run pytest tests/ -v

fmt: ## Format code with ruff
	uv run ruff format src/ tests/

lint: ## Lint code with ruff
	uv run ruff check src/ tests/

typecheck: ## Type check with pyright
	uv run pyright

dev: install test ## Setup dev environment and run tests

clean: ## Remove build artifacts and caches
	rm -rf dist/ build/ *.egg-info .pytest_cache $(STAMP)
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
