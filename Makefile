# ============================================================
# Project Makefile for local dev, testing, Docker, and deploy
# ------------------------------------------------------------
# - Cross-platform venv (Windows / *nix)
# - Local run in DEV/PROD modes
# - Lint/format/test/coverage (parity with CI)
# - Docker compose helpers (up/down/restart/logs)
# - Clean deploy over SSH: stop/remove → hard reset → build/up
# ============================================================

# ---------- 0) OS detection and Python tool paths ----------
ifeq ($(OS),Windows_NT)
	SHELL := cmd.exe
	PY := python
	VENV := .venv
	PYBIN := $(VENV)\Scripts\python.exe
	PIPBIN := $(VENV)\Scripts\pip.exe
	PYTEST := $(PYBIN) -m pytest
else
	SHELL := /bin/sh
	PY := python3
	VENV := .venv
	PYBIN := $(VENV)/bin/python
	PIPBIN := $(VENV)/bin/pip
	PYTEST := $(PYBIN) -m pytest
endif

# ---------- 1) Basic config ----------
APP := app.py

# ---------- 2) Deploy config (loaded from .env.deploy if present) ----------
# Example .env.deploy:
# SSH_HOST=ivan@203.0.113.10
# PROJECT_DIR=/home/ivan/telegram-weather-bot-pub
# BRANCH=main
-include .env.deploy

SSH_HOST ?=
PROJECT_DIR ?=
BRANCH ?= main
SSH_OPTS ?= -o StrictHostKeyChecking=accept-new

# ---------- 3) Phony targets ----------
.PHONY: \
	default venv install run-dev run-prod \
	test coverage coverage-html codecov test-all \
	lint format-check format \
	prod-up prod-logs prod-restart prod-down prod-clean \
	clean clean-venv freeze \
	deploy deploy-clean deploy-logs deploy-prune \
	ssh-connect local-deploy local-logs \
	backup-now pre-commit-install \
	ci-test ci-security ci-all

# ---------- 4) Default ----------
default: run-dev

# ---------- 5) Virtual environment ----------
venv:
ifeq ($(OS),Windows_NT)
	@if not exist $(VENV) $(PY) -m venv $(VENV)
else
	@test -d $(VENV) || $(PY) -m venv $(VENV)
endif

# ---------- 6) Dependencies install (prod + dev if available) ----------
install: venv
ifeq ($(OS),Windows_NT)
	$(PIPBIN) install -r requirements.txt
	@if exist requirements-dev.txt $(PIPBIN) install -r requirements-dev.txt
else
	$(PIPBIN) install -U pip
	$(PIPBIN) install -r requirements.txt
	@test -f requirements-dev.txt && $(PIPBIN) install -r requirements-dev.txt || true
endif

# ---------- 7) Run locally in DEV mode (uses .env.dev) ----------
run-dev: venv install
ifeq ($(OS),Windows_NT)
	@if not exist .env.dev (echo File .env.dev not found. Create it with BOT_TOKEN=... && exit 1)
	$(PYBIN) -c "from dotenv import load_dotenv, find_dotenv; import os; load_dotenv(find_dotenv('.env.dev')); os.execv('$(PYBIN)', ['$(PYBIN)', '$(APP)'])"
else
	@test -f .env.dev || (echo "File .env.dev not found. Create it with BOT_TOKEN=..." && exit 1)
	bash -c "source $(VENV)/bin/activate && set -a && . .env.dev && set +a && python $(APP)"
endif

# ---------- 8) Run locally in PROD mode (uses .env.prod) ----------
run-prod: venv install
ifeq ($(OS),Windows_NT)
	@if not exist .env.prod (echo File .env.prod not found. Create it with BOT_TOKEN=... && exit 1)
	$(PYBIN) -c "from dotenv import load_dotenv, find_dotenv; import os; load_dotenv(find_dotenv('.env.prod')); os.execv('$(PYBIN)', ['$(PYBIN)', '$(APP)'])"
else
	@test -f .env.prod || (echo "File .env.prod not found. Create it with BOT_TOKEN=..." && exit 1)
	bash -c "source $(VENV)/bin/activate && set -a && . .env.prod && set +a && python $(APP)"
endif

# ---------- 9) Tests / coverage / codecov ----------
test: venv install
	$(PYTEST) -q

coverage: venv
	$(PYTEST) --cov=weatherbot --cov-report=term-missing --cov-report=xml -q
	@echo "coverage.xml created; check term-missing output above for gaps"

coverage-html: venv
	$(PYTEST) --cov=weatherbot --cov-report=term-missing --cov-report=xml --cov-report=html -q
	@echo "HTML report created at ./htmlcov/index.html"

codecov: coverage
ifeq (,$(CODECOV_TOKEN))
	@echo "CODECOV_TOKEN not set; skipping Codecov upload"
else
	@echo "Uploading coverage to Codecov..."
	curl -s https://uploader.codecov.io/latest/$(shell uname | tr '[:upper:]' '[:lower:]')/codecov -o codecov
	chmod +x codecov
	./codecov -t $(CODECOV_TOKEN) -f coverage.xml -F local || echo "Codecov upload failed"
endif

test-all: coverage codecov

# ---------- 10) Lint / format ----------
lint: venv
ifeq ($(OS),Windows_NT)
	$(VENV)\Scripts\flake8.exe .
else
	$(VENV)/bin/flake8 .
endif

format-check: venv
ifeq ($(OS),Windows_NT)
	$(VENV)\Scripts\black.exe --check .
	$(VENV)\Scripts\isort.exe --check-only .
else
	$(VENV)/bin/black --check .
	$(VENV)/bin/isort --check-only .
endif

format: venv install
ifeq ($(OS),Windows_NT)
	$(VENV)\Scripts\black.exe .
	$(VENV)\Scripts\isort.exe .
else
	$(VENV)/bin/black .
	$(VENV)/bin/isort .
endif

# ---------- 11) Docker (when already on the server) ----------
# Start (build) in background with production env
prod-up:
	docker compose --env-file .env.prod up -d --build

# Tail logs (last 100 lines)
prod-logs:
	docker compose logs -f --tail=100

# Restart running services
prod-restart:
	docker compose restart

# Stop + remove containers (and orphans) safely
prod-down:
	docker compose --env-file .env.prod down --remove-orphans

# Extra cleanup of stopped containers for this project
prod-clean: prod-down
	# Remove any stopped containers belonging to this compose project
	docker compose rm -f || true

# ---------- 12) Cleanup workspace ----------
clean:
ifeq ($(OS),Windows_NT)
	for /d /r . %%d in ("__pycache__") do @if exist "%%d" rd /s /q "%%d"
	for /r . %%f in ("*.pyc") do @if exist "%%f" del /q "%%f"
else
	find . -name "__pycache__" -type d -prune -exec rm -rf {} +; true
	find . -name "*.pyc" -delete; true
endif

clean-venv:
ifeq ($(OS),Windows_NT)
	if exist $(VENV) rd /s /q $(VENV)
else
	rm -rf $(VENV)
endif

# ---------- 13) Freeze dependencies (runtime lock) ----------
freeze: venv
ifeq ($(OS),Windows_NT)
	@echo "Freezing runtime dependencies: requirements.lock"
	$(VENV)\Scripts\pip freeze > requirements.lock
else
	@echo "Freezing runtime dependencies: requirements.lock"
	$(VENV)/bin/pip freeze > requirements.lock
endif
	@echo "(For dev dependencies use pip-compile or keep a separate lockfile)"

# ---------- 14) Remote deploy helpers over SSH ----------
# Simple deploy: pull and up (kept for compatibility)
deploy:
	@test -n "$(SSH_HOST)" || (echo "SSH_HOST not set. Create .env.deploy with SSH_HOST, PROJECT_DIR, BRANCH"; exit 1)
	@test -n "$(PROJECT_DIR)" || (echo "PROJECT_DIR not set. Create .env.deploy"; exit 1)
	ssh $(SSH_OPTS) $(SSH_HOST) 'set -e; cd $(PROJECT_DIR) && \
		git fetch --all && git checkout $(BRANCH) && git pull && \
		docker compose --env-file .env.prod up -d --build'

# Clean deploy: stop → remove → hard reset to origin/BRANCH → pull images → rebuild & up
deploy-clean:
	@test -n "$(SSH_HOST)" || (echo "SSH_HOST not set. Create .env.deploy with SSH_HOST, PROJECT_DIR, BRANCH"; exit 1)
	@test -n "$(PROJECT_DIR)" || (echo "PROJECT_DIR not set. Create .env.deploy"; exit 1)
	ssh $(SSH_OPTS) $(SSH_HOST) '\
		set -euo pipefail; \
		cd $(PROJECT_DIR); \
		echo "[1/5] Stop & remove containers"; \
		docker compose --env-file .env.prod down --remove-orphans || true; \
		docker compose rm -f || true; \
		echo "[2/5] Hard reset to origin/$(BRANCH)"; \
		git fetch --all; \
		git checkout $(BRANCH); \
		git reset --hard origin/$(BRANCH); \
		echo "[3/5] Pull base images (if any)"; \
		docker compose --env-file .env.prod pull || true; \
		echo "[4/5] Rebuild & start"; \
		docker compose --env-file .env.prod up -d --build --force-recreate --remove-orphans; \
		echo "[5/5] Recent logs"; \
		docker compose logs --tail=60 || true \
	'

# Optional: free disk space by pruning unused images and builder cache (keeps volumes)
deploy-prune:
	@test -n "$(SSH_HOST)" || (echo "SSH_HOST not set. Create .env.deploy"; exit 1)
	@test -n "$(PROJECT_DIR)" || (echo "PROJECT_DIR not set. Create .env.deploy"; exit 1)
	ssh $(SSH_OPTS) $(SSH_HOST) '\
		set -euo pipefail; \
		docker image prune -f; \
		docker builder prune -f \
	'

# Logs on remote host
deploy-logs:
	@test -n "$(SSH_HOST)" || (echo "SSH_HOST not set. Create .env.deploy"; exit 1)
	@test -n "$(PROJECT_DIR)" || (echo "PROJECT_DIR not set. Create .env.deploy"; exit 1)
	ssh $(SSH_OPTS) $(SSH_HOST) 'cd $(PROJECT_DIR) && docker compose logs -f --tail=120'

# ---------- 15) Raw SSH helper ----------
ssh-connect:
	@test -n "$(SSH_HOST)" || (echo "SSH_HOST not set. Create .env.deploy with SSH_HOST, PROJECT_DIR, BRANCH"; exit 1)
	ssh $(SSH_OPTS) $(SSH_HOST)

# ---------- 16) Local deploy (when you are already on the server) ----------
local-deploy:
	git fetch --all
	git checkout $(BRANCH)
	git reset --hard origin/$(BRANCH)
	docker compose --env-file .env.prod up -d --build --force-recreate --remove-orphans

local-logs:
	docker compose logs -f --tail=120

# ---------- 17) Manual storage backup (runs in current venv) ----------
backup-now: venv
	$(PYBIN) -c "import asyncio; from weatherbot.jobs.backup import perform_backup; asyncio.run(perform_backup()); print('Manual backup done')"

# ---------- 18) Pre-commit hook installation ----------
pre-commit-install: venv
ifeq ($(OS),Windows_NT)
	$(VENV)\Scripts\pip install pre-commit
	$(VENV)\Scripts\pre-commit install --install-hooks
else
	$(VENV)/bin/pip install pre-commit
	$(VENV)/bin/pre-commit install --install-hooks
endif

# ---------- 19) CI parity: tests + security ----------
ci-test: venv install
	@echo "[ci-test] Black check"; $(VENV)/bin/black --check .
	@echo "[ci-test] isort check"; $(VENV)/bin/isort --check-only .
	@echo "[ci-test] flake8"; $(VENV)/bin/flake8 .
	@echo "[ci-test] pytest with coverage"; $(PYTEST) --cov=weatherbot --cov-report=xml --cov-report=term-missing tests/
	@echo "[ci-test] Done"

ci-security: venv install
	@echo "[ci-security] Bandit scan"; $(VENV)/bin/bandit -c .bandit -r weatherbot/
	@echo "[ci-security] Done"

ci-all: ci-test ci-security
	@echo "[ci-all] Complete"
