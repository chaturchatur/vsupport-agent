import json
import re

from tests.n8n_harness import REPO_ROOT, get_node, load_workflow, run_code_node

# ---------------------------------------------------------------------------
# Post-call outcome persistence (feature 1)
#
# Covers: the structuredDataPlan schema, the Parse EOC Envelope mapping
# (including what happens when VAPI omits fields), the outcome patch that is
# merged onto a row already written by log_interaction, and migration 007.
# ---------------------------------------------------------------------------

WORKFLOW = "end-of-call-report"

OUTCOME_COLUMNS = [
    "call_reason",
    "authenticated",
    "claim_number",
    "claim_status",
    "resolved_without_human",
    "escalation_requested",
    "follow_up_needed",
    "follow_up_reason",
    "duration_seconds",
    "ended_reason",
]


def _make_eoc_envelope(structured_data: dict | None = None, **message_overrides):
    """Build the n8n webhook item for a VAPI end-of-call-report."""
    message = {
        "type": "end-of-call-report",
        "endedReason": "customer-ended-call",
        "durationSeconds": 187.4,
        "call": {"id": "call-abc123", "customer": {"number": "+14155551234"}},
        "analysis": {
            "summary": "Caller checked claim status for CLM-2024-001.",
            "structuredData": structured_data
            if structured_data is not None
            else {
                "callReason": "claim status check",
                "authenticated": True,
                "claimNumber": "clm-2024-001",
                "claimStatus": "approved",
                "callerName": "Sarah Johnson",
                "sentiment": "positive",
                "resolvedWithoutHuman": True,
                "escalationRequested": False,
                "followUpNeeded": False,
                "followUpReason": "",
            },
        },
    }
    message.update(message_overrides)
    return {"body": {"message": message}}


def _parse(envelope: dict) -> dict:
    return run_code_node(WORKFLOW, "Parse EOC Envelope", [envelope])[0]


class TestStructuredDataPlan:
    """The analysis schema must declare every field the workflow reads."""

    def _properties(self):
        config = json.loads((REPO_ROOT / "vapi" / "assistant_config.json").read_text(encoding="utf-8"))
        return config["analysisPlan"]["structuredDataPlan"]["schema"]["properties"]

    def test_new_outcome_fields_declared(self):
        props = self._properties()
        assert props["resolvedWithoutHuman"]["type"] == "boolean"
        assert props["escalationRequested"]["type"] == "boolean"
        assert props["followUpNeeded"]["type"] == "boolean"
        assert props["followUpReason"]["type"] == "string"

    def test_existing_field_names_unchanged(self):
        props = self._properties()
        for name in (
            "callReason", "authenticated", "claimNumber", "claimStatus", "escalated", "callerName",
            "dobVerified", "callbackPromised", "faqTopics", "authFailureReason", "callDurationCategory",
        ):
            assert name in props

    def test_every_field_the_parser_reads_is_declared(self):
        """VAPI only extracts declared fields (see .agent/Gotchas.md)."""
        code = get_node(load_workflow(WORKFLOW), "Parse EOC Envelope")["parameters"]["jsCode"]
        read_by_parser = set(re.findall(r"\bsd\.([A-Za-z]+)", code))
        assert read_by_parser, "expected the parser to read structuredData fields"
        assert read_by_parser <= set(self._properties())


class TestParseEocOutcomeMapping:
    def test_full_report_maps_every_outcome_column(self):
        row = _parse(_make_eoc_envelope())
        assert row["is_eoc"] is True
        assert row["call_reason"] == "claim status check"
        assert row["authenticated"] is True
        assert row["claim_number"] == "CLM-2024-001"  # upper-cased
        assert row["claim_status"] == "approved"
        assert row["resolved_without_human"] is True
        assert row["escalation_requested"] is False
        assert row["follow_up_needed"] is False
        assert row["follow_up_reason"] is None  # empty string -> NULL
        assert row["duration_seconds"] == 187
        assert row["ended_reason"] == "customer-ended-call"
        assert row["caller_phone_digits"] == "14155551234"

    def test_existing_columns_keep_their_behaviour(self):
        row = _parse(_make_eoc_envelope())
        assert row["caller_name"] == "Sarah Johnson"
        assert row["phone_number"] == "+14155551234"
        assert row["summary"] == "Caller checked claim status for CLM-2024-001."
        assert row["sentiment"] == "positive"
        assert row["vapi_call_id"] == "call-abc123"
        assert row["timestamp"]

    def test_missing_structured_data_defaults_to_null_not_false(self):
        """An unanalysed call is 'not scored'; it must not count as not-contained."""
        row = _parse(_make_eoc_envelope(structured_data={}))
        for column in OUTCOME_COLUMNS:
            if column in ("duration_seconds", "ended_reason"):
                continue
            assert row[column] is None, column
        assert row["caller_name"] == "Unknown"
        assert row["sentiment"] == "neutral"

    def test_missing_analysis_and_call_metadata(self):
        envelope = {"body": {"message": {"type": "end-of-call-report", "call": {"id": "call-x"}}}}
        row = _parse(envelope)
        assert row["is_eoc"] is True
        assert row["vapi_call_id"] == "call-x"
        assert row["summary"] == "No summary available"
        assert row["phone_number"] == ""
        for column in OUTCOME_COLUMNS:
            assert row[column] is None, column
        assert row["caller_phone_digits"] is None

    def test_duration_derived_from_timestamps_when_missing(self):
        envelope = _make_eoc_envelope(
            durationSeconds=None,
            startedAt="2026-11-10T15:00:00.000Z",
            endedAt="2026-11-10T15:02:30.000Z",
        )
        del envelope["body"]["message"]["durationSeconds"]
        assert _parse(envelope)["duration_seconds"] == 150

    def test_invalid_values_are_rejected(self):
        row = _parse(
            _make_eoc_envelope(
                structured_data={
                    "claimStatus": "denied",                      # not an allowed status
                    "claimNumber": "CLM-1,phone_digits.gt.0",     # filter-injection attempt
                    "authenticated": "maybe",
                    "sentiment": "furious",
                },
                durationSeconds=-5,
            )
        )
        assert row["claim_status"] is None
        assert row["claim_number"] is None
        assert row["authenticated"] is None
        assert row["sentiment"] == "neutral"
        assert row["duration_seconds"] is None

    def test_legacy_fields_used_as_fallback(self):
        """'escalated' and 'callbackPromised' pre-date the new fields."""
        row = _parse(_make_eoc_envelope(structured_data={"escalated": True, "callbackPromised": True}))
        assert row["escalation_requested"] is True
        assert row["follow_up_needed"] is True

    def test_new_fields_win_over_legacy_fields(self):
        row = _parse(_make_eoc_envelope(structured_data={"escalated": True, "escalationRequested": False}))
        assert row["escalation_requested"] is False

    def test_non_eoc_event_is_dropped(self):
        row = _parse({"body": {"message": {"type": "status-update"}}})
        assert row == {"is_eoc": False}

    def test_ten_digit_caller_id_gets_country_code(self):
        envelope = _make_eoc_envelope()
        envelope["body"]["message"]["call"]["customer"]["number"] = "4155551234"
        assert _parse(envelope)["caller_phone_digits"] == "14155551234"


class TestOutcomePatch:
    """Outcome columns are merged onto the row log_interaction already wrote."""

    def _parsed_row(self):
        row = _parse(_make_eoc_envelope())
        row.pop("is_eoc")
        return row

    def test_patch_has_outcomes_and_key_only(self):
        parsed = self._parsed_row()
        patch = run_code_node(WORKFLOW, "Build Outcome Patch", [{}], {"Strip Meta": [parsed]})[0]
        assert patch["vapi_call_id"] == "call-abc123"
        assert set(patch) == set(OUTCOME_COLUMNS) | {"vapi_call_id", "caller_phone_digits"}
        # the LLM-written summary / sentiment / name on the existing row are not overwritten
        for kept in ("summary", "sentiment", "caller_name", "phone_number", "timestamp"):
            assert kept not in patch

    def test_no_call_id_means_no_patch(self):
        parsed = self._parsed_row()
        parsed["vapi_call_id"] = ""
        assert run_code_node(WORKFLOW, "Build Outcome Patch", [{}], {"Strip Meta": [parsed]}) == []


class TestWorkflowWiring:
    def test_upsert_keeps_unique_constraint_dedup(self):
        node = get_node(load_workflow(WORKFLOW), "Upsert Interaction")
        assert node["parameters"]["operation"] == "create"
        assert node["parameters"]["tableId"] == "interactions"
        assert node["onError"] == "continueRegularOutput"

    def test_merge_matches_on_vapi_call_id(self):
        node = get_node(load_workflow(WORKFLOW), "Merge Outcomes")
        assert node["parameters"]["operation"] == "update"
        assert "vapi_call_id=eq." in node["parameters"]["filterString"]
        assert node["onError"] == "continueRegularOutput"

    def test_strip_meta_removes_only_the_flag(self):
        out = run_code_node(WORKFLOW, "Strip Meta", [{"is_eoc": True, "summary": "s", "vapi_call_id": "c"}])
        assert out == [{"summary": "s", "vapi_call_id": "c"}]


class TestMigration007:
    def _sql(self):
        return (REPO_ROOT / "supabase" / "migrations" / "007_interaction_outcomes.sql").read_text(encoding="utf-8")

    def test_every_outcome_column_added_as_nullable(self):
        sql = self._sql()
        for column in OUTCOME_COLUMNS:
            match = re.search(rf"ADD COLUMN IF NOT EXISTS {column}\s+(\w+)([^,;\n]*)", sql)
            assert match, column
            assert "NOT NULL" not in match.group(2).upper(), column

    def test_parser_only_writes_columns_that_exist(self):
        """autoMapInputData sends every key as a column, so an unknown key breaks the insert."""
        base = (REPO_ROOT / "supabase" / "migrations" / "001_initial_schema.sql").read_text(encoding="utf-8")
        row = _parse(_make_eoc_envelope())
        row.pop("is_eoc")
        for key in row:
            assert re.search(rf"\b{key}\b", base + self._sql()), key

    def test_daily_view_definition(self):
        sql = self._sql()
        assert "VIEW v_call_outcomes_daily" in sql
        for alias in ("calls", "authenticated_calls", "contained_calls", "escalations", "containment_rate"):
            assert re.search(rf"AS {alias}\b", sql), alias
        assert "resolved_without_human" in sql and "NOT COALESCE(escalation_requested, FALSE)" in sql
