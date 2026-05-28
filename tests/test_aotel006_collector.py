from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCAL_CONFIG = ROOT / "infra/otel/collector.local.yaml"
PROD_CONFIG = ROOT / "infra/otel/collector.prod.yaml"
NORMALIZE_FRAGMENT = ROOT / "infra/otel/processors/normalize-agent-fields.yaml"


def _load_yaml(path: Path):
    return _parse_yaml_subset(path.read_text().splitlines())


def _parse_yaml_subset(lines: list[str]):
    content = [
        (len(line) - len(line.lstrip(" ")), line.strip())
        for line in lines
        if line.strip() and not line.lstrip().startswith("#")
    ]

    def parse_block(index: int, indent: int):
        if index >= len(content):
            return {}, index
        if content[index][0] == indent and content[index][1].startswith("- "):
            return parse_list(index, indent)
        return parse_mapping(index, indent)

    def parse_list(index: int, indent: int):
        result = []
        while index < len(content):
            line_indent, text = content[index]
            if line_indent != indent or not text.startswith("- "):
                break

            item = text[2:]
            index += 1
            if ": " in item or item.endswith(":"):
                key, value = item.split(":", 1)
                entry = {}
                if value.strip():
                    entry[key] = parse_scalar(value.strip())
                else:
                    entry[key], index = parse_block(index, indent + 2)
                if index < len(content) and content[index][0] == indent + 2:
                    more, index = parse_mapping(index, indent + 2)
                    entry.update(more)
                result.append(entry)
            else:
                result.append(parse_scalar(item))
        return result, index

    def parse_mapping(index: int, indent: int):
        result = {}
        while index < len(content):
            line_indent, text = content[index]
            if line_indent < indent or text.startswith("- "):
                break
            if line_indent > indent:
                break
            key, value = text.split(":", 1)
            index += 1
            if value.strip():
                result[key] = parse_scalar(value.strip())
            else:
                result[key], index = parse_block(index, indent + 2)
        return result, index

    parsed, next_index = parse_block(0, 0)
    assert next_index == len(content)
    return parsed


def parse_scalar(value: str):
    if value.startswith("[") and value.endswith("]"):
        return [parse_scalar(part.strip()) for part in value[1:-1].split(",")]
    if value in {"true", "false"}:
        return value == "true"
    if value.isdigit():
        return int(value)
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def test_collector_yaml_files_parse():
    for path in [LOCAL_CONFIG, PROD_CONFIG, NORMALIZE_FRAGMENT]:
        loaded = _load_yaml(path)
        assert isinstance(loaded, dict)


def test_collector_receives_otlp_http_with_metadata():
    for path in [LOCAL_CONFIG, PROD_CONFIG]:
        config = _load_yaml(path)
        http_receiver = config["receivers"]["otlp"]["protocols"]["http"]

        assert http_receiver["endpoint"] == "0.0.0.0:4318"
        assert http_receiver["include_metadata"] is True


def test_collector_maps_trusted_headers_to_resource_attributes():
    expected_attributes = {
        "telemetry.user.email": "metadata.x-telemetry-user",
        "telemetry.user.id": "metadata.x-telemetry-user-id",
        "telemetry.team.id": "metadata.x-telemetry-team",
        "telemetry.token.id": "metadata.x-telemetry-token-id",
        "telemetry.source.ip": "metadata.x-telemetry-source-ip",
        "agent.capture.profile": "metadata.x-telemetry-capture-profile",
    }

    for path in [LOCAL_CONFIG, PROD_CONFIG]:
        config = _load_yaml(path)
        attributes = config["processors"]["resource/tenant_from_headers"]["attributes"]
        by_key = {attribute["key"]: attribute for attribute in attributes}

        for key, context in expected_attributes.items():
            assert by_key[key]["from_context"] == context
            assert by_key[key]["action"] == "upsert"

        assert by_key["service.namespace"]["value"] == "agent-otel"
        assert by_key["service.namespace"]["action"] == "upsert"


def test_collector_normalizes_codex_and_claude_for_all_signals():
    for path in [LOCAL_CONFIG, PROD_CONFIG, NORMALIZE_FRAGMENT]:
        config = _load_yaml(path)
        transform = config["processors"]["transform/agent_normalize"]

        for statement_group in [
            "log_statements",
            "trace_statements",
            "metric_statements",
        ]:
            statements = transform[statement_group][0]["statements"]
            joined = "\n".join(statements)
            assert 'set(attributes["agent.tool"], "codex")' in joined
            assert 'attributes["service.name"] == "codex"' in joined
            assert 'set(attributes["agent.tool"], "claude_code")' in joined
            assert 'attributes["service.name"] == "claude-code"' in joined


def test_collector_exporter_has_queue_retry_and_internal_signoz_endpoint():
    local = _load_yaml(LOCAL_CONFIG)
    prod = _load_yaml(PROD_CONFIG)

    local_exporter = local["exporters"]["otlp/signoz"]
    assert local_exporter["endpoint"] == "signoz-otel-collector:4317"

    prod_exporter = prod["exporters"]["otlp/signoz"]
    assert prod_exporter["endpoint"] == "${env:SIGNOZ_OTLP_GRPC_ENDPOINT}"

    for exporter in [local_exporter, prod_exporter]:
        assert exporter["tls"]["insecure"] is True
        assert exporter["sending_queue"]["enabled"] is True
        assert exporter["sending_queue"]["queue_size"] == 5000
        assert exporter["retry_on_failure"]["enabled"] is True
        assert exporter["retry_on_failure"]["initial_interval"] == "5s"
        assert exporter["retry_on_failure"]["max_interval"] == "30s"
        assert exporter["retry_on_failure"]["max_elapsed_time"] == "10m"


def test_collector_pipelines_cover_logs_traces_and_metrics():
    expected_processors = [
        "memory_limiter",
        "resource/tenant_from_headers",
        "transform/agent_normalize",
        "batch",
    ]

    for path in [LOCAL_CONFIG, PROD_CONFIG]:
        config = _load_yaml(path)
        pipelines = config["service"]["pipelines"]

        for signal in ["logs", "traces", "metrics"]:
            pipeline = pipelines[signal]
            assert pipeline["receivers"] == ["otlp"]
            assert pipeline["processors"] == expected_processors
            assert "otlp/signoz" in pipeline["exporters"]

        assert "clickhouse" not in config.get("exporters", {})
        assert "aws_s3" not in config.get("exporters", {})
