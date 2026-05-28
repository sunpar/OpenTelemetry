import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_DIR = ROOT / "infra/signoz/dashboards"
REQUIRED_DASHBOARDS = {
    "codex-overview.json",
    "claude-overview.json",
    "team-usage.json",
    "tool-usage.json",
    "collector-health.json",
}
REQUIRED_FILTERS = {
    "telemetry.user.email",
    "telemetry.team.id",
    "agent.tool",
    "agent.capture.profile",
}
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


def _dashboard(path: Path):
    return json.loads(path.read_text())


def test_dashboard_files_exist_and_parse_as_json():
    assert {path.name for path in DASHBOARD_DIR.glob("*.json")} == REQUIRED_DASHBOARDS

    for name in REQUIRED_DASHBOARDS:
        dashboard = _dashboard(DASHBOARD_DIR / name)
        assert dashboard["schema_version"] == "agent-otel-trial.dashboard.v1"
        assert dashboard["title"]
        assert dashboard["panels"]


def test_dashboards_include_required_filters():
    for name in REQUIRED_DASHBOARDS:
        dashboard = _dashboard(DASHBOARD_DIR / name)
        if name == "collector-health.json":
            assert not REQUIRED_FILTERS.intersection(set(dashboard["filters"]))
        else:
            assert REQUIRED_FILTERS.issubset(set(dashboard["filters"]))


def test_dashboard_default_group_bys_avoid_high_cardinality_fields():
    for name in REQUIRED_DASHBOARDS:
        dashboard = _dashboard(DASHBOARD_DIR / name)
        for panel in dashboard["panels"]:
            group_by = set(panel.get("group_by", []))
            assert not group_by.intersection(PROHIBITED_DEFAULT_GROUP_BYS), (
                name,
                panel["title"],
                group_by,
            )


def test_collector_health_dashboard_tracks_resilience_indicators():
    dashboard = _dashboard(DASHBOARD_DIR / "collector-health.json")
    panel_text = "\n".join(panel["title"].lower() for panel in dashboard["panels"])

    for expected in ["queue size", "queue capacity", "send failures", "refused", "memory limiter"]:
        assert expected in panel_text


def test_collector_health_dashboard_uses_collector_self_metric_names():
    dashboard = _dashboard(DASHBOARD_DIR / "collector-health.json")
    query_text = "\n".join(panel["query"] for panel in dashboard["panels"])

    for metric_name in [
        "otelcol_exporter_send_failed_log_records",
        "otelcol_exporter_send_failed_spans",
        "otelcol_exporter_send_failed_metric_points",
        "otelcol_receiver_refused_log_records",
        "otelcol_receiver_refused_spans",
        "otelcol_receiver_refused_metric_points",
        "otelcol_processor_refused_log_records",
        "otelcol_processor_refused_spans",
        "otelcol_processor_refused_metric_points",
    ]:
        assert metric_name in query_text

    assert " + logs" not in query_text
    assert " + spans" not in query_text
    assert " + metric_points" not in query_text
    assert "signal" not in set(dashboard["filters"])

    for panel in dashboard["panels"]:
        assert "signal" not in set(panel.get("group_by", []))


def test_signoz_readme_documents_dashboard_import_limitations():
    readme = (ROOT / "infra/signoz/README.md").read_text()

    assert "infra/signoz/dashboards" in readme
    assert "manual import" in readme.lower()
    assert "schema" in readme.lower()
