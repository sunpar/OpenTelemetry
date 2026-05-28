SHELL := /bin/sh

.DEFAULT_GOAL := help

ifneq (,$(wildcard .env))
include .env
endif

AOTEL_PUBLIC_ENDPOINT ?= http://localhost:8088
AUTH_API_DB_PATH ?= /data/auth-api.sqlite3
CAPTURE_PROFILE ?= normal
ENDPOINT ?= $(AOTEL_PUBLIC_ENDPOINT)
EXPIRES ?= 90d
GATEWAY_NETWORK ?= agent-otel-gateway
GATEWAY_PORT ?= 8088
PROFILE ?= normal
SIGNOZ_NETWORK ?= signoz-net
SIGNOZ_VENDOR_DIR ?= .vendor/signoz
TOKEN_CAPTURE_PROFILE ?= $(PROFILE)

export AUTH_API_DB_PATH GATEWAY_NETWORK GATEWAY_PORT SIGNOZ_NETWORK

.PHONY: help signoz-up signoz-down gateway-up up down logs user token smoke install-codex install-claude

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
	@printf '%s\n' '  make signoz-up       Clone/start the local SigNoz Docker stack.'
	@printf '%s\n' '  make signoz-down     Stop the local SigNoz Docker stack.'
	@printf '%s\n' '  make up              Start auth-api, Nginx, and Collector gateway.'
	@printf '%s\n' '  make down            Stop the gateway stack.'
	@printf '%s\n' '  make logs            Follow gateway stack logs.'
	@printf '%s\n' '  make user EMAIL=... TEAM=... [NAME=...]'
	@printf '%s\n' '                       Create/update a telemetry user.'
	@printf '%s\n' '  make token EMAIL=... [TOKEN_NAME=...] [EXPIRES=90d] [CAPTURE_PROFILE=normal|max]'
	@printf '%s\n' '                       Issue a telemetry token and print onboarding snippets.'
	@printf '%s\n' '  make smoke TOKEN=... [ENDPOINT=http://localhost:8088]'
	@printf '%s\n' '                       Send test telemetry through the gateway.'
	@printf '%s\n' '  make install-codex ENDPOINT=... TOKEN=... [PROFILE=normal|max]'
	@printf '%s\n' '                       Install Codex telemetry config.'
	@printf '%s\n' '  make install-claude ENDPOINT=... TOKEN=... [PROFILE=normal|max]'
	@printf '%s\n' '                       Write Claude Code telemetry env file.'

signoz-up:
	@mkdir -p .vendor
	@if [ ! -d "$(SIGNOZ_VENDOR_DIR)/.git" ]; then \
		git clone -b main https://github.com/SigNoz/signoz.git "$(SIGNOZ_VENDOR_DIR)"; \
	fi
	@docker network inspect "$(SIGNOZ_NETWORK)" >/dev/null 2>&1 || docker network create "$(SIGNOZ_NETWORK)" >/dev/null
	docker compose -f $(SIGNOZ_VENDOR_DIR)/deploy/docker/docker-compose.yaml up -d --remove-orphans

signoz-down:
	@if [ ! -f "$(SIGNOZ_VENDOR_DIR)/deploy/docker/docker-compose.yaml" ]; then \
		printf '%s\n' 'SigNoz vendor compose file is missing. Run make signoz-up first.'; \
		exit 2; \
	fi
	docker compose -f $(SIGNOZ_VENDOR_DIR)/deploy/docker/docker-compose.yaml down

gateway-up: up

up:
	@docker network inspect "$(SIGNOZ_NETWORK)" >/dev/null 2>&1 || docker network create "$(SIGNOZ_NETWORK)" >/dev/null
	docker compose -f compose/docker-compose.gateway.yml up -d

down:
	docker compose -f compose/docker-compose.gateway.yml down

logs:
	docker compose -f compose/docker-compose.gateway.yml logs -f

user:
	$(call require_var,EMAIL,make user EMAIL=alice@example.com TEAM=quant-dev)
	$(call require_var,TEAM,make user EMAIL=alice@example.com TEAM=quant-dev)
	docker compose -f compose/docker-compose.gateway.yml exec auth-api python /workspace/cli/otelctl/src/otelctl.py --db-path "$(AUTH_API_DB_PATH)" users add --email "$(EMAIL)" --team "$(TEAM)" $(if $(NAME),--name "$(NAME)",)

token:
	$(call require_var,EMAIL,make token EMAIL=alice@example.com)
	docker compose -f compose/docker-compose.gateway.yml exec auth-api python /workspace/cli/otelctl/src/otelctl.py --db-path "$(AUTH_API_DB_PATH)" tokens issue --email "$(EMAIL)" $(if $(TOKEN_NAME),--name "$(TOKEN_NAME)",) --expires "$(EXPIRES)" --capture-profile "$(CAPTURE_PROFILE)" --endpoint "$(ENDPOINT)"

smoke:
	$(call require_var,TOKEN,make smoke TOKEN=<issued-token>)
	python3 scripts/smoke-test-otel.py --endpoint "$(ENDPOINT)" --token "$(TOKEN)"

install-codex:
	$(call require_var,ENDPOINT,make install-codex ENDPOINT=http://localhost:8088 TOKEN=<issued-token>)
	$(call require_var,TOKEN,make install-codex ENDPOINT=http://localhost:8088 TOKEN=<issued-token>)
	bash scripts/install-codex-otel.sh --endpoint "$(ENDPOINT)" --token "$(TOKEN)" --profile "$(PROFILE)"

install-claude:
	$(call require_var,ENDPOINT,make install-claude ENDPOINT=http://localhost:8088 TOKEN=<issued-token>)
	$(call require_var,TOKEN,make install-claude ENDPOINT=http://localhost:8088 TOKEN=<issued-token>)
	bash scripts/install-claude-otel.sh --endpoint "$(ENDPOINT)" --token "$(TOKEN)" --profile "$(or $(PROFILE),normal)" --token-capture-profile "$(TOKEN_CAPTURE_PROFILE)" --output "$(or $(OUTPUT),./claude.otel.env)"
