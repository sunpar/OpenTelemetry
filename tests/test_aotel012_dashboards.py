import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_DIR = ROOT / "infra/signoz/dashboards"
SIGNOZ_README = ROOT / "infra/signoz/README.md"
CONTRACT_DASHBOARD_SCHEMA_VERSION = "agent-otel-trial.dashboard.v1"
COLLECTOR_HEALTH_DASHBOARD = "collector-health.json"
IMPORTABLE_SIGNOZ_DASHBOARD = "agent-telemetry-collected-data.signoz.json"
IMPORTABLE_SIGNOZ_TITLE = "Agent Telemetry - Collected Data"
IMPORTABLE_SIGNOZ_VERSION = "v5"
REQUIRED_CONTRACT_DASHBOARDS = {
    "codex-overview.json",
    "claude-overview.json",
    "team-usage.json",
    "tool-usage.json",
    COLLECTOR_HEALTH_DASHBOARD,
}
REQUIRED_DASHBOARDS = REQUIRED_CONTRACT_DASHBOARDS | {IMPORTABLE_SIGNOZ_DASHBOARD}
REQUIRED_FILTERS = {
    "telemetry.user.email",
    "telemetry.team.id",
    "agent.tool",
    "agent.capture.profile",
}
REQUIRED_IMPORTABLE_FILTERS = REQUIRED_FILTERS | {"service.name"}
IMPORTABLE_WIDGET_FILTERS = {
    "ingest-health": {"service.name"},
}
IMPORTABLE_PANEL_TITLE_PHRASES = (
    "logs received",
    "spans received",
    "metrics received",
    "latest telemetry records",
    "latest traces",
    "events by tool",
    "events by user",
    "events by team",
    "smoke",
    "ingest health",
)
COLLECTOR_HEALTH_PANEL_TITLE_PHRASES = (
    "queue size",
    "queue capacity",
    "send failures",
    "refused",
    "memory limiter",
)
COLLECTOR_SELF_METRICS = (
    "otelcol_exporter_send_failed_log_records",
    "otelcol_exporter_send_failed_spans",
    "otelcol_exporter_send_failed_metric_points",
    "otelcol_receiver_refused_log_records",
    "otelcol_receiver_refused_spans",
    "otelcol_receiver_refused_metric_points",
    "otelcol_processor_refused_log_records",
    "otelcol_processor_refused_spans",
    "otelcol_processor_refused_metric_points",
)
DEPRECATED_COLLECTOR_QUERY_FRAGMENTS = (" + logs", " + spans", " + metric_points")
PROHIBITED_DEFAULT_GROUP_BYS = {
    "agent.session.id",
    "agent.conversation.id",
    "repo.remote",
    "git.branch",
    "command",
    "command.text",
    "file.path",
    "file_path",
}


def _dashboard(name: str):
    return json.loads((DASHBOARD_DIR / name).read_text())


def test_dashboard_files_exist_and_parse_as_json():
    assert {path.name for path in DASHBOARD_DIR.glob("*.json")} == REQUIRED_DASHBOARDS

    for name in REQUIRED_CONTRACT_DASHBOARDS:
        dashboard = _dashboard(name)
        assert dashboard["schema_version"] == CONTRACT_DASHBOARD_SCHEMA_VERSION
        assert dashboard["title"]
        assert dashboard["panels"]


def test_dashboards_include_required_filters():
    for name in REQUIRED_CONTRACT_DASHBOARDS:
        dashboard = _dashboard(name)
        if name == COLLECTOR_HEALTH_DASHBOARD:
            assert not REQUIRED_FILTERS.intersection(set(dashboard["filters"]))
        else:
            assert REQUIRED_FILTERS.issubset(set(dashboard["filters"]))


def test_dashboard_default_group_bys_avoid_high_cardinality_fields():
    for name in REQUIRED_CONTRACT_DASHBOARDS:
        dashboard = _dashboard(name)
        for panel in dashboard["panels"]:
            group_by = set(panel.get("group_by", []))
            assert not group_by.intersection(PROHIBITED_DEFAULT_GROUP_BYS), (
                name,
                panel["title"],
                group_by,
            )


def _importable_dashboard():
    return _dashboard(IMPORTABLE_SIGNOZ_DASHBOARD)


def _widget_query_text(widget: dict) -> str:
    query = widget["query"]
    if query["queryType"] == "clickhouse_sql":
        return "\n".join(item["query"] for item in query["clickhouse_sql"])

    if query["queryType"] == "builder":
        parts = []
        for item in query["builder"]["queryData"]:
            parts.append(item.get("filter", {}).get("expression", ""))
            parts.extend(group["key"] for group in item.get("groupBy", []))
        return "\n".join(parts)

    return ""


def test_importable_signoz_dashboard_uses_live_dashboard_shape():
    dashboard = _importable_dashboard()

    assert dashboard["title"] == IMPORTABLE_SIGNOZ_TITLE
    assert dashboard["version"] == IMPORTABLE_SIGNOZ_VERSION
    assert isinstance(dashboard["variables"], dict)
    assert isinstance(dashboard["layout"], list)
    assert isinstance(dashboard["widgets"], list)
    assert len(dashboard["layout"]) == len(dashboard["widgets"])
    assert {item["i"] for item in dashboard["layout"]} == {
        widget["id"] for widget in dashboard["widgets"]
    }

    variable_names = {variable["name"] for variable in dashboard["variables"].values()}
    assert REQUIRED_IMPORTABLE_FILTERS.issubset(variable_names)

    for widget in dashboard["widgets"]:
        assert widget["id"]
        assert widget["title"]
        assert widget["panelTypes"] in {"graph", "value", "table", "list", "trace"}
        assert widget["timePreferance"] == "GLOBAL_TIME"
        assert widget["query"]["queryType"] in {"builder", "clickhouse_sql"}
        assert "selectedLogFields" in widget
        assert "selectedTracesFields" in widget


def test_importable_signoz_dashboard_answers_collection_questions():
    dashboard = _importable_dashboard()
    panel_text = "\n".join(widget["title"].lower() for widget in dashboard["widgets"])

    for expected in IMPORTABLE_PANEL_TITLE_PHRASES:
        assert expected in panel_text


def test_importable_signoz_dashboard_references_filters_without_bad_group_bys():
    dashboard = _importable_dashboard()

    for widget in dashboard["widgets"]:
        expected_filters = IMPORTABLE_WIDGET_FILTERS.get(
            widget["id"], REQUIRED_IMPORTABLE_FILTERS
        )
        query_text = _widget_query_text(widget)
        for variable_name in expected_filters:
            assert f"{{{{.{variable_name}}}}}" in query_text, widget["id"]

        for field_name in PROHIBITED_DEFAULT_GROUP_BYS:
            assert field_name not in query_text, widget["id"]


def test_collector_health_dashboard_tracks_resilience_indicators():
    dashboard = _dashboard(COLLECTOR_HEALTH_DASHBOARD)
    panel_text = "\n".join(panel["title"].lower() for panel in dashboard["panels"])

    for expected in COLLECTOR_HEALTH_PANEL_TITLE_PHRASES:
        assert expected in panel_text


def test_collector_health_dashboard_uses_collector_self_metric_names():
    dashboard = _dashboard(COLLECTOR_HEALTH_DASHBOARD)
    query_text = "\n".join(panel["query"] for panel in dashboard["panels"])

    for metric_name in COLLECTOR_SELF_METRICS:
        assert metric_name in query_text

    for deprecated_fragment in DEPRECATED_COLLECTOR_QUERY_FRAGMENTS:
        assert deprecated_fragment not in query_text
    assert "signal" not in set(dashboard["filters"])

    for panel in dashboard["panels"]:
        assert "signal" not in set(panel.get("group_by", []))


def test_signoz_readme_documents_dashboard_import_limitations():
    readme = SIGNOZ_README.read_text()

    assert "infra/signoz/dashboards" in readme
    assert "manual import" in readme.lower()
    assert "schema" in readme.lower()
    assert IMPORTABLE_SIGNOZ_DASHBOARD in readme
    assert IMPORTABLE_SIGNOZ_TITLE in readme


def test_signoz_readme_documents_manual_org_setup_and_opamp_sideline():
    readme = SIGNOZ_README.read_text()

    assert "Agent Telemetry Trial" in readme
    assert "first admin" in readme.lower()
    assert "do not commit" in readme.lower()
    assert "OpAMP" in readme
    assert "--manager-config" in readme
    assert "cannot create agent without orgId" in readme
