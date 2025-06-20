# Makefile for AI Mail MCP
# Provides convenient commands for development, testing, and deployment

.PHONY: help install install-dev test test-fast test-coverage lint format security clean build docker-build docker-run benchmark health-check monitor setup ci pre-commit docs

# Default Python interpreter
PYTHON ?= python3
PIP ?= pip
VENV_DIR ?= venv

# Project paths
SRC_DIR = src
TESTS_DIR = tests
SCRIPTS_DIR = scripts

# Colors for output
GREEN = \033[0;32m
YELLOW = \033[1;33m
RED = \033[0;31m
NC = \033[0m # No Color

# Default target
help: ## Show this help message
	@echo "$(GREEN)AI Mail MCP - Development Commands$(NC)"
	@echo "=================================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "$(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'

# Development Environment Setup
setup: ## Set up development environment
	@echo "$(GREEN)Setting up development environment...$(NC)"
	$(PYTHON) $(SCRIPTS_DIR)/dev_setup.py --setup

install: ## Install production dependencies
	@echo "$(GREEN)Installing production dependencies...$(NC)"
	$(PIP) install -e .

install-dev: ## Install development dependencies
	@echo "$(GREEN)Installing development dependencies...$(NC)"
	$(PIP) install -e .[dev]

# Code Quality
format: ## Format code with black and isort
	@echo "$(GREEN)Formatting code...$(NC)"
	black $(SRC_DIR) $(TESTS_DIR) $(SCRIPTS_DIR)
	isort $(SRC_DIR) $(TESTS_DIR) $(SCRIPTS_DIR)

lint: ## Run linting checks
	@echo "$(GREEN)Running linting checks...$(NC)"
	black --check $(SRC_DIR) $(TESTS_DIR) $(SCRIPTS_DIR)
	isort --check-only $(SRC_DIR) $(TESTS_DIR) $(SCRIPTS_DIR)
	flake8 $(SRC_DIR) $(TESTS_DIR) $(SCRIPTS_DIR)
	mypy $(SRC_DIR)

security: ## Run security checks
	@echo "$(GREEN)Running security checks...$(NC)"
	bandit -r $(SRC_DIR)/
	safety check

# Testing
test: ## Run full test suite
	@echo "$(GREEN)Running test suite...$(NC)"
	pytest $(TESTS_DIR)/ -v

test-fast: ## Run fast tests (exclude slow tests)
	@echo "$(GREEN)Running fast tests...$(NC)"
	pytest $(TESTS_DIR)/ -v -m "not slow"

test-coverage: ## Run tests with coverage report
	@echo "$(GREEN)Running tests with coverage...$(NC)"
	pytest $(TESTS_DIR)/ -v --cov=$(SRC_DIR) --cov-report=term-missing --cov-report=html

test-performance: ## Run performance tests
	@echo "$(GREEN)Running performance tests...$(NC)"
	pytest $(TESTS_DIR)/ -v -m "performance"

# Build and Package
build: ## Build package
	@echo "$(GREEN)Building package...$(NC)"
	$(PYTHON) -m build

clean: ## Clean build artifacts
	@echo "$(GREEN)Cleaning build artifacts...$(NC)"
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name .mypy_cache -exec rm -rf {} +
	rm -f .coverage
	rm -rf htmlcov/

# Docker
docker-build: ## Build Docker image
	@echo "$(GREEN)Building Docker image...$(NC)"
	docker build -t ai-mail-mcp:latest .

docker-run: ## Run Docker container
	@echo "$(GREEN)Running Docker container...$(NC)"
	docker-compose up -d

docker-stop: ## Stop Docker container
	@echo "$(GREEN)Stopping Docker container...$(NC)"
	docker-compose down

docker-logs: ## Show Docker container logs
	@echo "$(GREEN)Showing Docker logs...$(NC)"
	docker-compose logs -f

# Monitoring and Maintenance
benchmark: ## Run performance benchmarks
	@echo "$(GREEN)Running performance benchmarks...$(NC)"
	$(PYTHON) $(SCRIPTS_DIR)/benchmark.py

health-check: ## Run database health check
	@echo "$(GREEN)Running health check...$(NC)"
	$(PYTHON) $(SCRIPTS_DIR)/health_check.py --full-check

monitor: ## Run monitoring (once)
	@echo "$(GREEN)Running monitoring cycle...$(NC)"
	$(PYTHON) $(SCRIPTS_DIR)/monitor.py --once

monitor-daemon: ## Run monitoring daemon
	@echo "$(GREEN)Starting monitoring daemon...$(NC)"
	$(PYTHON) $(SCRIPTS_DIR)/monitor.py --daemon

# Git Hooks
pre-commit: ## Install pre-commit hooks
	@echo "$(GREEN)Installing pre-commit hooks...$(NC)"
	pre-commit install

pre-commit-run: ## Run pre-commit on all files
	@echo "$(GREEN)Running pre-commit on all files...$(NC)"
	pre-commit run --all-files

# CI/CD
ci: ## Run all CI checks locally
	@echo "$(GREEN)Running CI checks...$(NC)"
	$(PYTHON) $(SCRIPTS_DIR)/dev_setup.py --ci

ci-quick: ## Run quick CI checks (no performance tests)
	@echo "$(GREEN)Running quick CI checks...$(NC)"
	make lint
	make test-fast
	make security

# Development Utilities
dev-install: install-dev pre-commit ## Quick development setup
	@echo "$(GREEN)Development environment ready!$(NC)"

dev-check: format lint test-fast security ## Quick development check
	@echo "$(GREEN)Development checks completed!$(NC)"

dev-reset: clean install-dev ## Reset development environment
	@echo "$(GREEN)Development environment reset!$(NC)"

# Documentation
docs: ## Generate documentation
	@echo "$(GREEN)Generating documentation...$(NC)"
	# Add documentation generation commands here when implemented

docs-serve: ## Serve documentation locally
	@echo "$(GREEN)Serving documentation...$(NC)"
	# Add documentation serving commands here when implemented

# Database Management
db-backup: ## Create database backup
	@echo "$(GREEN)Creating database backup...$(NC)"
	$(PYTHON) $(SCRIPTS_DIR)/health_check.py --backup

db-optimize: ## Optimize database
	@echo "$(GREEN)Optimizing database...$(NC)"
	$(PYTHON) $(SCRIPTS_DIR)/health_check.py --optimize

db-cleanup: ## Clean up old database entries
	@echo "$(GREEN)Cleaning up database...$(NC)"
	$(PYTHON) $(SCRIPTS_DIR)/health_check.py --cleanup 30

# Release Management
version: ## Show current version
	@echo "$(GREEN)Current version:$(NC)"
	$(PYTHON) -c "import ai_mail_mcp; print(ai_mail_mcp.__version__)"

tag-release: ## Create release tag (requires VERSION env var)
	@if [ -z "$(VERSION)" ]; then echo "$(RED)Please set VERSION environment variable$(NC)"; exit 1; fi
	@echo "$(GREEN)Creating release tag v$(VERSION)...$(NC)"
	git tag -a v$(VERSION) -m "Release version $(VERSION)"
	git push origin v$(VERSION)

# Utility targets
check-env: ## Check development environment
	@echo "$(GREEN)Checking development environment...$(NC)"
	@echo "Python version: $(shell $(PYTHON) --version)"
	@echo "Pip version: $(shell $(PIP) --version)"
	@echo "Virtual environment: $(VIRTUAL_ENV)"
	@echo "Project root: $(shell pwd)"

print-make-version: ## Print make version (for debugging)
	@echo "$(GREEN)Make version:$(NC) $(MAKE_VERSION)"

# Example usage targets
example-send: ## Send example message (requires running server)
	@echo "$(GREEN)Sending example message...$(NC)"
	$(PYTHON) examples/direct_integration.py

example-docker: ## Run example in Docker
	@echo "$(GREEN)Running example in Docker...$(NC)"
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# Maintenance automation
auto-update: ## Update dependencies automatically
	@echo "$(GREEN)Updating dependencies...$(NC)"
	pre-commit autoupdate
	$(PIP) install --upgrade pip setuptools wheel

# Integration tests
test-integration: ## Run integration tests
	@echo "$(GREEN)Running integration tests...$(NC)"
	pytest $(TESTS_DIR)/ -v -m "integration"

test-all: ## Run all tests including slow ones
	@echo "$(GREEN)Running all tests...$(NC)"
	pytest $(TESTS_DIR)/ -v --cov=$(SRC_DIR) --cov-report=term-missing

# Quality gates (for CI)
quality-gate: lint security test-coverage ## Run quality gate checks
	@echo "$(GREEN)All quality gates passed!$(NC)"

# Development workflow shortcuts
dev-ready: clean install-dev pre-commit test-fast lint ## Prepare for development
	@echo "$(GREEN)Ready for development!$(NC)"

commit-ready: format lint test-fast security ## Check if ready to commit
	@echo "$(GREEN)Ready to commit!$(NC)"

release-ready: clean build test security docs ## Check if ready for release
	@echo "$(GREEN)Ready for release!$(NC)"

# Show project status
status: ## Show project status
	@echo "$(GREEN)AI Mail MCP Project Status$(NC)"
	@echo "=========================="
	@echo "Git status:"
	@git status --short || echo "Not a git repository"
	@echo ""
	@echo "Recent commits:"
	@git log --oneline -5 || echo "No git history"
	@echo ""
	@echo "Package info:"
	@$(PYTHON) -c "import ai_mail_mcp; print(f'Version: {ai_mail_mcp.__version__}')" 2>/dev/null || echo "Package not installed"
	@echo ""
	@echo "Test coverage:"
	@coverage report --show-missing 2>/dev/null || echo "No coverage data"

# Help with common tasks
quickstart: ## Quick start guide
	@echo "$(GREEN)AI Mail MCP Quick Start$(NC)"
	@echo "======================="
	@echo "1. Set up development environment: $(YELLOW)make setup$(NC)"
	@echo "2. Run tests: $(YELLOW)make test$(NC)"
	@echo "3. Check code quality: $(YELLOW)make lint$(NC)"
	@echo "4. Format code: $(YELLOW)make format$(NC)"
	@echo "5. Run CI checks: $(YELLOW)make ci$(NC)"
	@echo "6. Build package: $(YELLOW)make build$(NC)"
	@echo ""
	@echo "For more commands: $(YELLOW)make help$(NC)"
