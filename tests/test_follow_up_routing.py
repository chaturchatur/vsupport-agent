import re
import tempfile

from tests.n8n_harness import REPO_ROOT, get_node, load_workflow, resolved_copy, run_code_node

# ---------------------------------------------------------------------------
# Post-call actions (feature 2)
#
# Covers the branch conditions computed by Decide Actions, the Switch wiring,
# the rows written to follow_ups, the SMS guard rails, and that no branch node
# can fail the execution.
# ---------------------------------------------------------------------------

WORKFLOW = "end-of-call-report"

BRANCH_NODES = [
    "Decide Actions",
    "Route Actions",
    "Build Escalation Row",
    "Insert Escalation Follow-up",
    "Alert Configured?",
    "Send Alert Email",
    "Find Customer",
    "Build SMS",
    "Send Claim SMS",
    "Build Callback Row",
    "Insert Callback Follow-up",
]


def _parsed(**overrides):
    row = {
        "vapi_call_id": "call-abc123",
        "sentiment": "neutral",
        "authenticated": True,
        "claim_number": "CLM-2024-001",
        "resolved_without_human": True,
        "escalation_requested": False,
        "follow_up_needed": False,
        "follow_up_reason": None,
    }
    row.update(overrides)
    return row


def _decide(parsed: dict, stored: dict | None = None, resolve: dict | None = None) -> dict:
    """Run Decide Actions. `resolve` fills deploy-time placeholders, as deploy-n8n.sh would."""
    path = None
    if resolve:
        path = resolved_copy(WORKFLOW, resolve, tempfile.mkdtemp())
    return run_code_node(WORKFLOW, "Decide Actions", [stored or {}], {"Strip Meta": [parsed]}, workflow_path=path)[0]


TWILIO = {"TWILIO_FROM_NUMBER": "+15005550006", "N8N_TWILIO_CREDENTIAL_ID": "twilioCred1"}
ALERT = {
    "ALERT_EMAIL_TO": "oncall@example.com",
    "ALERT_EMAIL_FROM": "alerts@example.com",
    "N8N_SMTP_CREDENTIAL_ID": "smtpCred1",
}


class TestEscalationCondition:
    def test_escalation_requested(self):
        d = _decide(_parsed(escalation_requested=True, resolved_without_human=False))
        assert d["do_escalation"] is True
        assert d["escalation_trigger"] == "caller asked for a human"

    def test_negative_sentiment_alone(self):
        d = _decide(_parsed(sentiment="negative"))
        assert d["do_escalation"] is True
        assert d["escalation_trigger"] == "negative sentiment"

    def test_both_triggers(self):
        d = _decide(_parsed(sentiment="negative", escalation_requested=True))
        assert d["escalation_trigger"] == "caller asked for a human + negative sentiment"

    def test_neither(self):
        d = _decide(_parsed())
        assert d["do_escalation"] is False
        assert d["send_alert"] is False

    def test_negative_sentiment_logged_by_llm_wins_over_neutral_eoc(self):
        """Happy path: the stored row carries the sentiment log_interaction wrote."""
        stored = {"id": 7, "vapi_call_id": "call-abc123", "sentiment": "negative"}
        assert _decide(_parsed(sentiment="neutral"), stored)["do_escalation"] is True

    def test_stored_row_for_another_call_is_ignored(self):
        stored = {"id": 7, "vapi_call_id": "some-other-call", "sentiment": "negative"}
        assert _decide(_parsed(), stored)["do_escalation"] is False

    def test_missing_outcomes_do_not_escalate(self):
        d = _decide(_parsed(escalation_requested=None, resolved_without_human=None, follow_up_needed=None))
        assert (d["do_escalation"], d["do_sms"], d["do_callback"]) == (False, False, False)

    def test_reason_prefers_follow_up_reason(self):
        d = _decide(_parsed(escalation_requested=True, follow_up_reason="Wants to dispute the decision"))
        assert d["escalation_reason"] == "Wants to dispute the decision"


class TestAlertEmail:
    def test_no_alert_when_unconfigured(self):
        d = _decide(_parsed(escalation_requested=True))
        assert d["do_escalation"] is True  # the follow_ups row is still written
        assert d["send_alert"] is False
        assert d["alert_email_to"] == ""

    def test_alert_when_configured(self):
        d = _decide(_parsed(escalation_requested=True), resolve=ALERT)
        assert d["send_alert"] is True
        assert d["alert_email_to"] == "oncall@example.com"

    def test_recipient_is_never_hard_coded(self):
        workflow = load_workflow(WORKFLOW)
        email = get_node(workflow, "Send Alert Email")
        assert email["parameters"]["toEmail"].startswith("={{")
        text = (REPO_ROOT / "n8n" / "workflows" / f"{WORKFLOW}.json").read_text(encoding="utf-8")
        assert "__ALERT_EMAIL_TO__" in text
        assert not re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", text), "no literal email address in the export"

    def test_alert_body_has_no_caller_details(self):
        body = get_node(load_workflow(WORKFLOW), "Send Alert Email")["parameters"]["text"]
        for leak in ("summary", "caller_name", "phone_number", "claim_number", "reason"):
            assert leak not in body


class TestSmsCondition:
    def test_skipped_silently_without_twilio_config(self):
        assert _decide(_parsed())["do_sms"] is False

    def test_sent_when_resolved_authenticated_and_configured(self):
        d = _decide(_parsed(), resolve=TWILIO)
        assert d["do_sms"] is True
        assert d["sms_from"] == "+15005550006"

    def test_needs_both_twilio_values(self):
        assert _decide(_parsed(), resolve={"TWILIO_FROM_NUMBER": "+15005550006"})["do_sms"] is False

    def test_not_sent_when_unauthenticated(self):
        assert _decide(_parsed(authenticated=False), resolve=TWILIO)["do_sms"] is False

    def test_not_sent_when_not_resolved(self):
        assert _decide(_parsed(resolved_without_human=False), resolve=TWILIO)["do_sms"] is False

    def test_not_sent_without_a_valid_claim_number(self):
        assert _decide(_parsed(claim_number=None), resolve=TWILIO)["do_sms"] is False
        assert _decide(_parsed(claim_number="CLM 1;drop"), resolve=TWILIO)["do_sms"] is False


class TestBuildSms:
    DECISION = {"vapi_call_id": "call-abc123", "claim_number": "CLM-2024-001", "sms_from": "+15005550006"}
    CUSTOMER = {"id": 1, "claim_number": "CLM-2024-001", "claim_status": "approved", "phone_number": "+14155551234"}

    def _build(self, rows, decision=None):
        return run_code_node(WORKFLOW, "Build SMS", rows, {"Decide Actions": [decision or self.DECISION]})

    def test_goes_to_the_number_on_the_customers_row(self):
        sms = self._build([self.CUSTOMER])[0]
        assert sms["to"] == "+14155551234"
        assert sms["from"] == "+15005550006"
        assert "CLM-2024-001" in sms["body"] and "approved" in sms["body"]

    def test_status_text_comes_from_the_database_row(self):
        sms = self._build([{**self.CUSTOMER, "claim_status": "pending"}])[0]
        assert "under review" in sms["body"]

    def test_no_customer_row_no_sms(self):
        assert self._build([{}]) == []

    def test_lookup_error_no_sms(self):
        assert self._build([{"error": "timeout"}]) == []

    def test_ambiguous_match_no_sms(self):
        assert self._build([self.CUSTOMER, {**self.CUSTOMER, "id": 2}]) == []

    def test_claim_number_must_match_the_row(self):
        assert self._build([{**self.CUSTOMER, "claim_number": "CLM-2024-009"}]) == []

    def test_number_must_be_e164(self):
        assert self._build([{**self.CUSTOMER, "phone_number": "(415) 555-1234"}]) == []

    def test_unknown_status_no_sms(self):
        assert self._build([{**self.CUSTOMER, "claim_status": "mystery"}]) == []

    def test_sms_only_uses_values_from_build_sms(self):
        """The Twilio node must not read a phone number from anywhere else."""
        twilio = get_node(load_workflow(WORKFLOW), "Send Claim SMS")["parameters"]
        assert twilio["to"] == "={{ $json.to }}"
        assert twilio["from"] == "={{ $json.from }}"
        find = get_node(load_workflow(WORKFLOW), "Find Customer")["parameters"]
        assert find["tableId"] == "customers"


class TestCallbackCondition:
    def test_follow_up_needed(self):
        d = _decide(_parsed(follow_up_needed=True, follow_up_reason="Send the documents list"))
        assert d["do_callback"] is True
        assert d["callback_reason"] == "Send the documents list"

    def test_follow_up_without_reason_gets_placeholder(self):
        assert _decide(_parsed(follow_up_needed=True))["callback_reason"]

    def test_no_follow_up(self):
        assert _decide(_parsed())["do_callback"] is False

    def test_escalation_and_callback_can_both_fire(self):
        d = _decide(_parsed(escalation_requested=True, follow_up_needed=True))
        assert d["do_escalation"] is True and d["do_callback"] is True


class TestFollowUpRows:
    DECISION = {"vapi_call_id": "call-abc123", "escalation_reason": "negative sentiment", "callback_reason": "Call back"}

    def test_escalation_row(self):
        row = run_code_node(WORKFLOW, "Build Escalation Row", [{}], {"Decide Actions": [self.DECISION]})[0]
        assert row == {"vapi_call_id": "call-abc123", "kind": "escalation", "reason": "negative sentiment"}

    def test_callback_row(self):
        row = run_code_node(WORKFLOW, "Build Callback Row", [{}], {"Decide Actions": [self.DECISION]})[0]
        assert row == {"vapi_call_id": "call-abc123", "kind": "callback", "reason": "Call back"}

    def test_rows_match_the_follow_ups_table(self):
        sql = (REPO_ROOT / "supabase" / "migrations" / "008_follow_ups.sql").read_text(encoding="utf-8")
        for column in ("id", "vapi_call_id", "kind", "reason", "status", "created_at"):
            assert re.search(rf"^\s+{column}\s", sql, re.MULTILINE), column
        assert "CHECK (kind IN ('escalation', 'callback'))" in sql
        assert re.search(r"status\s+TEXT NOT NULL DEFAULT 'open'", sql)


class TestRoutingAndFailureIsolation:
    def test_switch_routes_on_the_three_flags(self):
        workflow = load_workflow(WORKFLOW)
        switch = get_node(workflow, "Route Actions")
        rules = switch["parameters"]["rules"]["values"]
        assert [r["conditions"]["conditions"][0]["leftValue"] for r in rules] == [
            "={{ $json.do_escalation }}",
            "={{ $json.do_sms }}",
            "={{ $json.do_callback }}",
        ]
        # a call can need more than one action
        assert switch["parameters"]["options"]["allMatchingOutputs"] is True
        outputs = workflow["connections"]["Route Actions"]["main"]
        assert [o[0]["node"] for o in outputs] == ["Build Escalation Row", "Find Customer", "Build Callback Row"]

    def test_switch_runs_after_the_interaction_is_stored(self):
        connections = load_workflow(WORKFLOW)["connections"]
        chain, node = [], "Upsert Interaction"
        while node != "Route Actions":
            node = connections[node]["main"][0][0]["node"]
            chain.append(node)
        assert chain == ["Build Outcome Patch", "Merge Outcomes", "Decide Actions", "Route Actions"]

    def test_no_branch_node_can_fail_the_execution(self):
        workflow = load_workflow(WORKFLOW)
        for name in BRANCH_NODES:
            assert get_node(workflow, name).get("onError") == "continueRegularOutput", name

    def test_webhook_responds_before_any_processing(self):
        webhook = get_node(load_workflow(WORKFLOW), "Webhook")
        assert webhook["parameters"]["responseMode"] == "onReceived"
        assert webhook["parameters"]["authentication"] == "headerAuth"

    def test_every_connection_points_at_a_real_node(self):
        workflow = load_workflow(WORKFLOW)
        names = {n["name"] for n in workflow["nodes"]}
        for source, outputs in workflow["connections"].items():
            assert source in names
            for output in outputs["main"]:
                for target in output:
                    assert target["node"] in names
