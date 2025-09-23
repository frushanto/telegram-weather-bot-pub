# Operating system detection
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

APP := app.py

# ====== DEPLOY VARS (loaded from .env.deploy if present) ======
# Example .env.deploy:
# SSH_HOST=ivan@203.0.113.10
# PROJECT_DIR=/home/ivan/telegram-weather-bot-pub
# BRANCH=main
-include .env.deploy

SSH_HOST ?=
PROJECT_DIR ?=
BRANCH ?= main
SSH_OPTS ?= -o StrictHostKeyChecking=accept-new

.PHONY: default venv install run-dev run-prod test clean clean-venv prod-up prod-logs prod-restart freeze format deploy deploy-logs

default: run-dev

# 1) Create virtual environment
venv:
ifeq ($(OS),Windows_NT)
	@if not exist $(VENV) $(PY) -m venv $(VENV)
else
	@test -d $(VENV) || $(PY) -m venv $(VENV)
endif

# 2) Install dependencies
install: venv
ifeq ($(OS),Windows_NT)
	$(PIPBIN) install -r requirements.txt
	@if exist requirements-dev.txt $(PIPBIN) install -r requirements-dev.txt
else
	$(PIPBIN) install -U pip
	$(PIPBIN) install -r requirements.txt
	@test -f requirements-dev.txt && $(PIPBIN) install -r requirements-dev.txt || true
endif

# 3) Run DEV locally
run-dev: venv install
ifeq ($(OS),Windows_NT)
	@if not exist .env.dev (echo "File .env.dev not found. Create it with BOT_TOKEN=..." && exit 1)
	$(PYBIN) -c "import os; [os.environ.setdefault(k,v) for k,v in [line.strip().split('=',1) for line in open('.env.dev') if '=' in line]]; import subprocess; subprocess.run(['$(PYBIN)', '$(APP)'])"
else
	@test -f .env.dev || (echo "File .env.dev not found. Create it with BOT_TOKEN=..." && exit 1)
	bash -c "source $(VENV)/bin/activate && export $$(cat .env.dev | xargs) && python $(APP)"
endif

# 4) Run PROD locally (for testing)
run-prod: venv install
ifeq ($(OS),Windows_NT)
	@if not exist .env.prod (echo "File .env.prod not found. Create it with BOT_TOKEN=..." && exit 1)
	$(PYBIN) -c "import os; [os.environ.setdefault(k,v) for k,v in [line.strip().split('=',1) for line in open('.env.prod') if '=' in line]]; import subprocess; subprocess.run(['$(PYBIN)', '$(APP)'])"
else
	@test -f .env.prod || (echo "File .env.prod not found. Create it with BOT_TOKEN=..." && exit 1)
	bash -c "source $(VENV)/bin/activate && export $$(cat .env.prod | xargs) && python $(APP)"
endif

# 5) Tests (without coverage). Added install dependency to ensure dev dependencies are installed
test: venv install
	$(PYTEST) -q

# 5.1) Coverage locally
coverage: venv
	$(PYTEST) --cov=weatherbot --cov-report=term-missing --cov-report=xml -q
	@echo "coverage.xml created; check term-missing output above for gaps"

# 5.1.1) Coverage with HTML report (to htmlcov folder)
coverage-html: venv
	$(PYTEST) --cov=weatherbot --cov-report=term-missing --cov-report=xml --cov-report=html -q
	@echo "HTML report created at ./htmlcov/index.html"

# 5.2) Upload coverage to Codecov
codecov: coverage
ifeq (,$(CODECOV_TOKEN))
	@echo "CODECOV_TOKEN not set; skipping Codecov upload"
else
	@echo "Uploading coverage to Codecov...";
	curl -s https://uploader.codecov.io/latest/$(shell uname | tr '[:upper:]' '[:lower:]')/codecov -o codecov;
	chmod +x codecov;
	./codecov -t $(CODECOV_TOKEN) -f coverage.xml -F local || echo "Codecov upload failed";
endif

# 5.3) Full cycle: tests + coverage + upload (if token available)
test-all: coverage codecov

# 6) Code linting
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

# 7) Docker commands (manually on server if you SSH)
prod-up:
	docker compose --env-file .env.prod up -d --build

prod-logs:
	docker compose logs -f --tail=100

prod-restart:
	docker compose restart

# 7) Cleanup
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

# 8) Dependencies
freeze: venv
ifeq ($(OS),Windows_NT)
	@echo "Freezing runtime dependencies (prod): requirements.txt"
	$(VENV)\Scripts\pip freeze > requirements.lock
else
	@echo "Freezing runtime dependencies (prod): requirements.lock"
	$(VENV)/bin/pip freeze > requirements.lock
endif
	@echo "(For dev dependencies use pip-compile or separate lock if needed)"

# 9) Code formatting
format: venv install
ifeq ($(OS),Windows_NT)
	$(VENV)\Scripts\black.exe .
	$(VENV)\Scripts\isort.exe .
else
	$(VENV)/bin/black .
	$(VENV)/bin/isort .
endif

# 10) DEPLOY: git pull + docker compose on remote server
deploy:
	@test -n "$(SSH_HOST)" || (echo "SSH_HOST not set. Create .env.deploy with SSH_HOST, PROJECT_DIR, BRANCH"; exit 1)
	@test -n "$(PROJECT_DIR)" || (echo "PROJECT_DIR not set. Create .env.deploy"; exit 1)
	ssh $(SSH_OPTS) $(SSH_HOST) 'set -e; cd $(PROJECT_DIR) && \
		git fetch --all && git checkout $(BRANCH) && git pull && \
		docker compose --env-file .env.prod up -d --build'

deploy-logs:
	@test -n "$(SSH_HOST)" || (echo "SSH_HOST not set. Create .env.deploy"; exit 1)
	@test -n "$(PROJECT_DIR)" || (echo "PROJECT_DIR not set. Create .env.deploy"; exit 1)
	ssh $(SSH_OPTS) $(SSH_HOST) 'cd $(PROJECT_DIR) && docker compose logs -f --tail=120'

# 11) SSH connection to server
ssh-connect:
	@test -n "$(SSH_HOST)" || (echo "SSH_HOST not set. Create .env.deploy with SSH_HOST, PROJECT_DIR, BRANCH"; exit 1)
	ssh $(SSH_OPTS) $(SSH_HOST)

# 12) Local deploy (when already on server)
local-deploy:
	git fetch --all 
	git checkout $(BRANCH) 
	git pull
	docker compose --env-file .env.prod up -d --build

local-logs:
	docker compose logs -f --tail=120

# 13) Manual storage backup (runs in current venv)
backup-now: venv
	$(PYBIN) -c "import asyncio; from weatherbot.jobs.backup import perform_backup; asyncio.run(perform_backup()); print('Manual backup done')"

# 14) Pre-commit hook installation
pre-commit-install: venv
ifeq ($(OS),Windows_NT)
	$(VENV)\Scripts\pip install pre-commit
	$(VENV)\Scripts\pre-commit install --install-hooks
else
	$(VENV)/bin/pip install pre-commit
	$(VENV)/bin/pre-commit install --install-hooks
endif

# 15) CI parity targets
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