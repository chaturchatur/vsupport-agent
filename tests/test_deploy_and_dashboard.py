import json
import re

import pytest

from scripts.resolve_n8n_placeholders import PlaceholderError, build_payload, resolve_placeholders
from tests.n8n_harness import REPO_ROOT, WORKFLOWS_DIR

# ---------------------------------------------------------------------------
# Deploy-time placeholder resolution and the Grafana dashboard (feature 4)
#
# Nothing here talks to n8n, VAPI, Supabase or Grafana.
# ---------------------------------------------------------------------------

FULL_ENV = {
    "VAPI_ASSISTANT_ID": "asst-test-0001",
    "SUPABASE_URL": "https://example-ref.supabase.co/",
    "ALERT_EMAIL_TO": "oncall@example.com",
    "ALERT_EMAIL_FROM": "alerts@example.com",
    "N8N_SMTP_CREDENTIAL_ID": "smtpCred1",
    "TWILIO_FROM_NUMBER": "+15005550006",
    "N8N_TWILIO_CREDENTIAL_ID": "twilioCred1",
}


def _text(name: str) -> str:
    return (WORKFLOWS_DIR / f"{name}.json").read_text(encoding="utf-8")


class TestPlaceholderResolution:
    @pytest.mark.parametrize("name", ["end-of-call-report", "pre-call-context", "lookup-caller", "log-interaction"])
    def test_full_env_leaves_no_placeholders(self, name):
        resolved = resolve_placeholders(_text(name), FULL_ENV)
        assert not re.search(r"__[A-Z0-9_]+__", resolved)
        json.loads(resolved)

    def test_optional_values_resolve_to_empty(self):
        payload = build_payload(_text("end-of-call-report"), {})
        nodes = {n["name"]: n for n in payload["nodes"]}
        assert "const ALERT_EMAIL_TO = '';" in nodes["Decide Actions"]["parameters"]["jsCode"]
        assert "const TWILIO_FROM_NUMBER = '';" in nodes["Decide Actions"]["parameters"]["jsCode"]
        # no dangling credential references for services that are not set up
        assert "credentials" not in nodes["Send Claim SMS"]
        assert "credentials" not in nodes["Send Alert Email"]
        # existing credentials are untouched
        assert nodes["Upsert Interaction"]["credentials"]["supabaseApi"]["id"]

    def test_credentials_kept_when_configured(self):
        nodes = {n["name"]: n for n in build_payload(_text("end-of-call-report"), FULL_ENV)["nodes"]}
        assert nodes["Send Claim SMS"]["credentials"]["twilioApi"]["id"] == "twilioCred1"
        assert nodes["Send Alert Email"]["credentials"]["smtp"]["id"] == "smtpCred1"

    def test_required_value_missing_fails_the_deploy(self):
        with pytest.raises(PlaceholderError, match="VAPI_ASSISTANT_ID"):
            build_payload(_text("pre-call-context"), {"SUPABASE_URL": "https://example-ref.supabase.co"})
        with pytest.raises(PlaceholderError, match="SUPABASE_URL"):
            build_payload(_text("pre-call-context"), {"VAPI_ASSISTANT_ID": "asst-test-0001"})

    def test_supabase_url_trailing_slash_removed(self):
        payload = build_payload(_text("pre-call-context"), FULL_ENV)
        urls = [n["parameters"]["url"] for n in payload["nodes"] if n["type"].endswith("httpRequest")]
        assert urls == [
            "=https://example-ref.supabase.co/rest/v1/customers",
            "=https://example-ref.supabase.co/rest/v1/interactions",
        ]

    @pytest.mark.parametrize("bad", ["x'; process.exit(); '", 'a"b', "={{ $env.SECRET }}", "line\nbreak"])
    def test_values_that_could_escape_a_string_are_refused(self, bad):
        with pytest.raises(PlaceholderError):
            resolve_placeholders(_text("end-of-call-report"), {**FULL_ENV, "ALERT_EMAIL_TO": bad})

    def test_read_only_fields_are_stripped(self):
        payload = build_payload(_text("end-of-call-report"), FULL_ENV)
        for key in ("id", "active", "createdAt", "updatedAt", "versionId"):
            assert key not in payload

    def test_new_env_keys_documented_with_empty_values(self):
        example = (REPO_ROOT / ".env.example").read_text(encoding="utf-8")
        for key in (
            "TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_FROM_NUMBER", "N8N_TWILIO_CREDENTIAL_ID",
            "ALERT_EMAIL_TO", "ALERT_EMAIL_FROM", "N8N_SMTP_CREDENTIAL_ID",
        ):
            assert re.search(rf"^{key}=\s*$", example, re.MULTILINE), key


class TestEveryWorkflowIsDocumented:
    def test_each_json_has_a_matching_md(self):
        for path in WORKFLOWS_DIR.glob("*.json"):
            assert path.with_suffix(".md").exists(), path.name


class TestGrafanaDashboard:
    def _dashboard(self):
        return json.loads((REPO_ROOT / "grafana" / "dashboard.json").read_text(encoding="utf-8"))

    def _queries(self):
        return {
            panel["title"]: " ".join(t["rawSql"] for t in panel["targets"])
            for panel in self._dashboard()["panels"]
        }

    def test_expected_panels_exist(self):
        titles = set(self._queries())
        assert {
            "Calls per day", "Containment rate", "Escalations per day",
            "Sentiment mix", "Authenticated share", "Average call duration",
        } <= titles

    def test_panels_read_only_the_view_and_interactions(self):
        for title, sql in self._queries().items():
            tables = set(re.findall(r"\bFROM\s+([a-z_]+)", sql))
            assert tables and tables <= {"v_call_outcomes_daily", "interactions"}, title
            assert not re.search(r"\b(INSERT|UPDATE|DELETE|DROP|ALTER)\b", sql, re.IGNORECASE), title

    def test_view_columns_used_by_panels_exist(self):
        view_sql = (REPO_ROOT / "supabase" / "migrations" / "007_interaction_outcomes.sql").read_text(encoding="utf-8")
        view_columns = set(re.findall(r"AS (\w+)\s*(?:,|\n)", view_sql.split("CREATE OR REPLACE VIEW")[1]))
        for title, sql in self._queries().items():
            if "v_call_outcomes_daily" not in sql:
                continue
            used = set(re.findall(r"\b(day|calls|authenticated_calls|scored_calls|contained_calls|escalations|containment_rate)\b", sql))
            assert used <= view_columns, (title, used - view_columns)

    def test_data_source_is_an_import_time_input(self):
        dashboard = self._dashboard()
        assert dashboard["__inputs"][0]["pluginId"] in ("grafana-postgresql-datasource", "postgres")
        for panel in dashboard["panels"]:
            assert panel["datasource"]["uid"] == "${DS_SUPABASE}"

    def test_nothing_secret_is_committed(self):
        for name in ("dashboard.json", "README.md"):
            text = (REPO_ROOT / "grafana" / name).read_text(encoding="utf-8")
            assert not re.search(r"postgres(ql)?://\S+:\S+@", text), name
            assert "supabase.co" not in text.replace("<project-ref>.supabase.co", ""), name
            assert not re.search(r"eyJ[A-Za-z0-9_-]{20,}", text), name  # JWT-shaped keys
