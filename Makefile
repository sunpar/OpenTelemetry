SHELL := /bin/sh

.DEFAULT_GOAL := help

ifneq (,$(wildcard .env))
include .env
endif

AOTEL_PUBLIC_ENDPOINT ?= http://localhost:8088
AOTEL_OTLP_UPSTREAM ?=
AUTH_API_DB_PATH ?= ./auth-api.sqlite3
AUTH_API_HOST ?= $(GATEWAY_HOST)
AUTH_API_PORT ?= $(GATEWAY_PORT)
CAPTURE_PROFILE ?= normal
DOCKER_COMPOSE ?= docker compose
ENDPOINT ?= $(AOTEL_PUBLIC_ENDPOINT)
EXPIRES ?= 90d
GATEWAY_NETWORK ?= agent-otel-gateway
GATEWAY_HOST ?= 127.0.0.1
GATEWAY_PORT ?= 8088
PROFILE ?= normal
PYTHON ?= python3
SIGNOZ_NETWORK ?= signoz-net
SIGNOZ_COMPOSE_OVERRIDE ?= compose/docker-compose.signoz.override.yml
SIGNOZ_VENDOR_DIR ?= .vendor/signoz
TOKEN_CAPTURE_PROFILE ?= $(PROFILE)
AUTH_API_NATIVE_PYTHONPATH := packages/auth-core/src:services/auth-api/src
OTELCTL_NATIVE_PYTHONPATH := packages/auth-core/src:cli/otelctl/src

export AOTEL_OTLP_UPSTREAM AUTH_API_DB_PATH AUTH_API_HOST AUTH_API_PORT GATEWAY_HOST GATEWAY_NETWORK GATEWAY_PORT SIGNOZ_NETWORK

.PHONY: help install-dev lint test static-check legacy-compose-config compose-config check native-up up down user token smoke install-codex install-claude

define require_var
	@if [ -z "$($(1))" ]; then \
		printf '%s\n' 'Missing required variable: $(1)'; \
		printf '%s\n' 'Usage: $(2)'; \
		exit 2; \
	fi
endef

help:
	@printf '%s\n' 'Agent OpenTelemetry Trial'
	@printf '%s\n' ''
	@printf '%s\n' 'Available targets:'
	@printf '%s\n' '  make install-dev      Install local packages and validation tools.'
	@printf '%s\n' '  make lint             Run Ruff.'
	@printf '%s\n' '  make test             Run the Python test suite.'
	@printf '%s\n' '  make static-check     Run docs/static checks and git diff --check.'
	@printf '%s\n' '  make check            Run lint, tests, and static checks.'
	@printf '%s\n' '  AOTEL_OTLP_UPSTREAM=... make native-up'
	@printf '%s\n' '                       Start the native FastAPI auth/gateway runtime.'
	@printf '%s\n' '  make up              Alias for native-up.'
	@printf '%s\n' '  make down            Explain how to stop the foreground native runtime.'
	@printf '%s\n' '  make legacy-compose-config'
	@printf '%s\n' '                       Validate legacy Docker Compose reference files.'
	@printf '%s\n' '  make user EMAIL=... TEAM=... [NAME=...]'
	@printf '%s\n' '                       Create/update a telemetry user.'
	@printf '%s\n' '  make token EMAIL=... [TOKEN_NAME=...] [EXPIRES=90d] [CAPTURE_PROFILE=normal|max]'
	@printf '%s\n' '                       Issue a telemetry token and print onboarding snippets.'
	@printf '%s\n' '  AOTEL_SMOKE_TOKEN=... make smoke [ENDPOINT=http://localhost:8088]'
	@printf '%s\n' '                       Send test telemetry through the gateway.'
	@printf '%s\n' '  make install-codex ENDPOINT=... TOKEN=... [PROFILE=normal|max]'
	@printf '%s\n' '                       Install Codex telemetry config.'
	@printf '%s\n' '  make install-claude ENDPOINT=... TOKEN=... [PROFILE=normal|max]'
	@printf '%s\n' '                       Write Claude Code telemetry env file.'

install-dev:
	$(PYTHON) -m pip install -r requirements-dev.txt

lint:
	$(PYTHON) -m ruff check .

test:
	$(PYTHON) -m pytest -q

static-check:
	$(PYTHON) scripts/check-docs.py
	git diff --check
	git diff --cached --check

legacy-compose-config:
	$(DOCKER_COMPOSE) -f compose/docker-compose.gateway.yml config >/dev/null
	$(DOCKER_COMPOSE) -f compose/docker-compose.signoz.yml config >/dev/null
	DOCKER_COMPOSE="$(DOCKER_COMPOSE)" SIGNOZ_VENDOR_DIR="$(SIGNOZ_VENDOR_DIR)" SIGNOZ_COMPOSE_OVERRIDE="$(SIGNOZ_COMPOSE_OVERRIDE)" bash scripts/check-signoz-compose-config.sh

compose-config: legacy-compose-config

check: lint test static-check

native-up:
	$(call require_var,AOTEL_OTLP_UPSTREAM,AOTEL_OTLP_UPSTREAM=http://127.0.0.1:4318 make native-up)
	PYTHONPATH=$(AUTH_API_NATIVE_PYTHONPATH) $(PYTHON) -m uvicorn auth_api.app:app --host "$(AUTH_API_HOST)" --port "$(AUTH_API_PORT)"

up: native-up

down:
	@printf '%s\n' 'The native FastAPI gateway runs in the foreground; stop it with Ctrl-C or your process supervisor.'

user:
	$(call require_var,EMAIL,make user EMAIL=alice@example.com TEAM=quant-dev)
	$(call require_var,TEAM,make user EMAIL=alice@example.com TEAM=quant-dev)
	PYTHONPATH=$(OTELCTL_NATIVE_PYTHONPATH) $(PYTHON) cli/otelctl/src/otelctl.py --db-path "$(AUTH_API_DB_PATH)" users add --email "$(EMAIL)" --team "$(TEAM)" $(if $(NAME),--name "$(NAME)",)

token:
	$(call require_var,EMAIL,make token EMAIL=alice@example.com)
	PYTHONPATH=$(OTELCTL_NATIVE_PYTHONPATH) $(PYTHON) cli/otelctl/src/otelctl.py --db-path "$(AUTH_API_DB_PATH)" tokens issue --email "$(EMAIL)" $(if $(TOKEN_NAME),--name "$(TOKEN_NAME)",) --expires "$(EXPIRES)" --capture-profile "$(CAPTURE_PROFILE)" --endpoint "$(ENDPOINT)"

smoke:
	@if [ -z "$${AOTEL_SMOKE_TOKEN:-}" ] && [ -z "$(TOKEN)" ]; then \
		printf '%s\n' 'Missing required token source: set AOTEL_SMOKE_TOKEN or pass TOKEN for local-only testing'; \
		printf '%s\n' 'Usage: AOTEL_SMOKE_TOKEN=<issued-token> make smoke'; \
		exit 2; \
	fi
	AOTEL_SMOKE_TOKEN="$${AOTEL_SMOKE_TOKEN:-$(TOKEN)}" $(PYTHON) scripts/smoke-test-otel.py --endpoint "$(ENDPOINT)"

install-codex:
	$(call require_var,ENDPOINT,make install-codex ENDPOINT=http://localhost:8088 TOKEN=<issued-token>)
	$(call require_var,TOKEN,make install-codex ENDPOINT=http://localhost:8088 TOKEN=<issued-token>)
	bash scripts/install-codex-otel.sh --endpoint "$(ENDPOINT)" --token "$(TOKEN)" --profile "$(PROFILE)"

install-claude:
	$(call require_var,ENDPOINT,make install-claude ENDPOINT=http://localhost:8088 TOKEN=<issued-token>)
	$(call require_var,TOKEN,make install-claude ENDPOINT=http://localhost:8088 TOKEN=<issued-token>)
	bash scripts/install-claude-otel.sh --endpoint "$(ENDPOINT)" --token "$(TOKEN)" --profile "$(or $(PROFILE),normal)" --token-capture-profile "$(TOKEN_CAPTURE_PROFILE)" --output "$(or $(OUTPUT),./claude.otel.env)"
