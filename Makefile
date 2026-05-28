SHELL := /bin/sh

.DEFAULT_GOAL := help

.PHONY: help signoz-up signoz-down gateway-up up down logs user token smoke install-codex install-claude

define require_var
	@if [ -z "$($(1))" ]; then \
		printf '%s\n' 'Missing required variable: $(1)'; \
		printf '%s\n' 'Usage: $(2)'; \
		exit 2; \
	fi
endef

define not_implemented
	@printf '%s\n' 'Target "$(1)" is not implemented yet.'
	@printf '%s\n' '$(2)'
	@exit 2
endef

help:
	@printf '%s\n' 'Agent OpenTelemetry Trial'
	@printf '%s\n' ''
	@printf '%s\n' 'Available targets:'
	@printf '%s\n' '  make signoz-up       Start the local SigNoz backend once compose/docker-compose.signoz.yml exists.'
	@printf '%s\n' '  make signoz-down     Stop the local SigNoz backend once compose/docker-compose.signoz.yml exists.'
	@printf '%s\n' '  make up              Start the gateway stack once compose/docker-compose.gateway.yml exists.'
	@printf '%s\n' '  make down            Stop the gateway stack once compose/docker-compose.gateway.yml exists.'
	@printf '%s\n' '  make logs            Follow gateway stack logs once compose/docker-compose.gateway.yml exists.'
	@printf '%s\n' '  make user EMAIL=... TEAM=...'
	@printf '%s\n' '                       Create/update a telemetry user once otelctl and Compose are implemented.'
	@printf '%s\n' '  make token EMAIL=... Issue a telemetry token once otelctl and Compose are implemented.'
	@printf '%s\n' '  make smoke TOKEN=... Send test telemetry once scripts/smoke-test-otel.py exists.'
	@printf '%s\n' '  make install-codex ENDPOINT=... TOKEN=...'
	@printf '%s\n' '                       Install Codex telemetry config once the installer exists.'
	@printf '%s\n' '  make install-claude ENDPOINT=... TOKEN=...'
	@printf '%s\n' '                       Install Claude Code telemetry env.'

signoz-up:
	$(call not_implemented,$@,compose/docker-compose.signoz.yml is planned for AOTEL-008.)

signoz-down:
	$(call not_implemented,$@,compose/docker-compose.signoz.yml is planned for AOTEL-008.)

gateway-up:
	$(call not_implemented,$@,compose/docker-compose.gateway.yml is planned for AOTEL-007.)

up:
	$(call not_implemented,$@,compose/docker-compose.gateway.yml is planned for AOTEL-007.)

down:
	$(call not_implemented,$@,compose/docker-compose.gateway.yml is planned for AOTEL-007.)

logs:
	$(call not_implemented,$@,compose/docker-compose.gateway.yml is planned for AOTEL-007.)

user:
	$(call require_var,EMAIL,make user EMAIL=alice@example.com TEAM=quant-dev)
	$(call require_var,TEAM,make user EMAIL=alice@example.com TEAM=quant-dev)
	$(call not_implemented,$@,otelctl user commands are planned for AOTEL-004 and Compose wiring is planned for AOTEL-007.)

token:
	$(call require_var,EMAIL,make token EMAIL=alice@example.com)
	$(call not_implemented,$@,otelctl token commands are planned for AOTEL-004 and Compose wiring is planned for AOTEL-007.)

smoke:
	$(call require_var,TOKEN,make smoke TOKEN=<issued-token>)
	$(call not_implemented,$@,scripts/smoke-test-otel.py is planned for AOTEL-009.)

install-codex:
	$(call require_var,ENDPOINT,make install-codex ENDPOINT=http://localhost:8088 TOKEN=<issued-token>)
	$(call require_var,TOKEN,make install-codex ENDPOINT=http://localhost:8088 TOKEN=<issued-token>)
	$(call not_implemented,$@,scripts/install-codex-otel.sh is planned for AOTEL-010.)

install-claude:
	$(call require_var,ENDPOINT,make install-claude ENDPOINT=http://localhost:8088 TOKEN=<issued-token>)
	$(call require_var,TOKEN,make install-claude ENDPOINT=http://localhost:8088 TOKEN=<issued-token>)
	@bash scripts/install-claude-otel.sh --endpoint "$(ENDPOINT)" --token "$(TOKEN)" --profile "$(or $(PROFILE),normal)" --output "$(or $(OUTPUT),./claude.otel.env)"
