import json

import pytest

from tests.n8n_harness import REPO_ROOT, get_node, load_workflow, resolved_copy, run_code_node

# ---------------------------------------------------------------------------
# Pre-call context (feature 3)
#
# VAPI sends `assistant-request` before an inbound call connects (only when the
# phone number has no assistant assigned) and expects, within 7.5 seconds:
#   { "assistantId": "...", "assistantOverrides": { "variableValues": {...} } }
#
# Covers: the assistant-request envelope, phone normalisation, the response for
# known / unknown callers and for failed lookups, and the prompt/config changes.
# ---------------------------------------------------------------------------

WORKFLOW = "pre-call-context"
ASSISTANT_ID = "asst-test-0001"
VARIABLES = {
    "callerKnown", "firstName", "claimNumber", "claimStatus",
    "lastCallSummary", "lastCallSentiment", "callerNumber",
}
CUSTOMER = {"id": 1, "first_name": "Sarah", "claim_number": "CLM-2024-001", "claim_status": "approved"}
LAST_CALL = {
    "summary": "Caller checked claim status.\nClaim approved.",
    "sentiment": "negative",
    "timestamp": "2026-11-09T15:00:00+00:00",
}


def _make_assistant_request(number: str | None = "+14155551234", call_id: str = "call-abc123"):
    """Build the n8n webhook item for a VAPI assistant-request."""
    call = {"id": call_id, "type": "inboundPhoneCall"}
    if number is not None:
        call["customer"] = {"number": number}
    return {"body": {"message": {"type": "assistant-request", "call": call}}}


def _parse(envelope: dict) -> dict:
    return run_code_node(WORKFLOW, "Parse Assistant Request", [envelope])[0]


def _pick(envelope: dict, customer_rows: list) -> dict:
    parsed = _parse(envelope)
    return run_code_node(WORKFLOW, "Pick Customer", customer_rows, {"Parse Assistant Request": [parsed]})[0]


@pytest.fixture
def respond(tmp_path):
    """Run the whole Code-node chain and return the body VAPI would receive."""
    path = resolved_copy(WORKFLOW, {"VAPI_ASSISTANT_ID": ASSISTANT_ID}, tmp_path)

    def _respond(envelope: dict, customer_rows: list, interaction_rows: list) -> dict:
        parsed = _parse(envelope)
        picked = run_code_node(WORKFLOW, "Pick Customer", customer_rows, {"Parse Assistant Request": [parsed]})[0]
        return run_code_node(
            WORKFLOW,
            "Build Response",
            interaction_rows,
            {"Parse Assistant Request": [parsed], "Pick Customer": [picked]},
            workflow_path=path,
        )[0]

    return _respond


class TestAssistantRequestEnvelope:
    def test_envelope_structure(self):
        message = _make_assistant_request()["body"]["message"]
        assert message["type"] == "assistant-request"
        assert message["call"]["customer"]["number"] == "+14155551234"

    def test_envelope_serializable(self):
        payload = _make_assistant_request()
        assert json.loads(json.dumps(payload)) == payload

    def test_parse_e164_caller(self):
        parsed = _parse(_make_assistant_request("+14155551234"))
        assert parsed == {
            "is_assistant_request": True,
            "phone_number": "+14155551234",
            "phone_digits": "14155551234",
            "error": "",
        }

    @pytest.mark.parametrize("raw", ["4155551234", "(415) 555-1234", "1-415-555-1234", "14155551234"])
    def test_same_normalisation_as_lookup_caller(self, raw):
        """Whatever lookup-caller turns into E.164, pre-call-context must turn into the same."""
        tool_call = {"body": {"message": {"toolCallList": [{"id": "tc", "function": {"arguments": {"phone_number": raw}}}]}}}
        expected = run_code_node("lookup-caller", "Parse Envelope", [tool_call])[0]["phone_number"]
        assert _parse(_make_assistant_request(raw))["phone_number"] == expected == "+14155551234"

    def test_caller_number_at_message_level(self):
        envelope = _make_assistant_request(None)
        envelope["body"]["message"]["customer"] = {"number": "+14155551234"}
        assert _parse(envelope)["phone_digits"] == "14155551234"

    def test_withheld_caller_id(self):
        parsed = _parse(_make_assistant_request(None))
        assert parsed["error"] == "no_phone"
        assert parsed["phone_digits"] == "0"  # can never match a customer

    def test_garbage_caller_id(self):
        parsed = _parse(_make_assistant_request("anonymous"))
        assert parsed["error"] == "invalid_phone"
        assert parsed["phone_digits"] == "0"

    def test_other_event_types_are_flagged(self):
        parsed = _parse({"body": {"message": {"type": "status-update"}}})
        assert parsed["is_assistant_request"] is False

    def test_empty_body(self):
        assert _parse({})["is_assistant_request"] is False


class TestPickCustomer:
    def test_single_match_is_known(self):
        picked = _pick(_make_assistant_request(), [CUSTOMER])
        assert picked["caller_known"] is True
        assert picked["first_name"] == "Sarah"
        assert picked["phone_digits"] == "14155551234"

    def test_no_match_is_unknown(self):
        picked = _pick(_make_assistant_request(), [{}])  # alwaysOutputData: one empty item
        assert picked["caller_known"] is False
        assert picked["phone_digits"] == "0"  # no history lookup for unknown callers

    def test_two_customers_on_one_number_is_unknown(self):
        assert _pick(_make_assistant_request(), [CUSTOMER, {**CUSTOMER, "id": 2}])["caller_known"] is False

    def test_lookup_error_is_unknown(self):
        """A failed or timed-out HTTP request arrives as an item with no id."""
        assert _pick(_make_assistant_request(), [{"error": {"message": "timeout of 2500ms exceeded"}}])["caller_known"] is False


class TestResponse:
    def test_known_caller_response(self, respond):
        body = respond(_make_assistant_request(), [CUSTOMER], [LAST_CALL])
        assert body["assistantId"] == ASSISTANT_ID
        values = body["assistantOverrides"]["variableValues"]
        assert set(values) == VARIABLES
        assert values["callerKnown"] == "true"
        assert values["firstName"] == "Sarah"
        assert values["claimNumber"] == "CLM-2024-001"
        assert values["claimStatus"] == "approved"
        assert values["lastCallSummary"] == "Caller checked claim status. Claim approved."
        assert values["lastCallSentiment"] == "negative"
        assert values["callerNumber"] == "+14155551234"

    def test_known_caller_greeting_uses_first_name_and_asks_only_for_dob(self, respond):
        greeting = respond(_make_assistant_request(), [CUSTOMER], [LAST_CALL])["assistantOverrides"]["firstMessage"]
        assert "Sarah" in greeting
        assert "date of birth" in greeting
        assert "phone number" not in greeting
        # nothing about the claim or the previous call may be in the greeting
        for secret in ("CLM-2024-001", "approved", "claim status"):
            assert secret not in greeting

    def test_unknown_caller_response(self, respond):
        body = respond(_make_assistant_request("+19995550000"), [{}], [{}])
        assert body["assistantId"] == ASSISTANT_ID
        values = body["assistantOverrides"]["variableValues"]
        assert set(values) == VARIABLES
        assert values["callerKnown"] == "false"
        assert all(values[name] == "" for name in VARIABLES - {"callerKnown"})
        # no firstMessage override: the assistant's own greeting (today's flow) is used
        assert "firstMessage" not in body["assistantOverrides"]

    def test_lookup_error_still_returns_default_assistant(self, respond):
        body = respond(_make_assistant_request(), [{"error": "ETIMEDOUT"}], [{"error": "ETIMEDOUT"}])
        assert body["assistantId"] == ASSISTANT_ID
        assert body["assistantOverrides"]["variableValues"]["callerKnown"] == "false"
        assert "firstMessage" not in body["assistantOverrides"]

    def test_known_caller_with_failed_history_lookup(self, respond):
        values = respond(_make_assistant_request(), [CUSTOMER], [{"error": "ETIMEDOUT"}])["assistantOverrides"]["variableValues"]
        assert values["callerKnown"] == "true"
        assert values["lastCallSummary"] == ""
        assert values["lastCallSentiment"] == ""

    def test_known_caller_first_call(self, respond):
        values = respond(_make_assistant_request(), [CUSTOMER], [{}])["assistantOverrides"]["variableValues"]
        assert values["callerKnown"] == "true"
        assert values["lastCallSentiment"] == ""

    def test_most_recent_interaction_wins(self, respond):
        older = {"summary": "Older call.", "sentiment": "positive", "timestamp": "2026-10-01T10:00:00+00:00"}
        values = respond(_make_assistant_request(), [CUSTOMER], [older, LAST_CALL])["assistantOverrides"]["variableValues"]
        assert values["lastCallSentiment"] == "negative"

    def test_withheld_number_gets_default_assistant(self, respond):
        body = respond(_make_assistant_request(None), [{}], [{}])
        assert body["assistantOverrides"]["variableValues"]["callerKnown"] == "false"

    def test_unspeakable_first_name_falls_back_to_unknown(self, respond):
        bad = {**CUSTOMER, "first_name": "Robert'); DROP TABLE customers;--"}
        body = respond(_make_assistant_request(), [bad], [LAST_CALL])
        assert body["assistantOverrides"]["variableValues"]["callerKnown"] == "false"
        assert "firstMessage" not in body["assistantOverrides"]

    def test_long_summary_is_truncated(self, respond):
        long_call = {**LAST_CALL, "summary": "x" * 2000}
        values = respond(_make_assistant_request(), [CUSTOMER], [long_call])["assistantOverrides"]["variableValues"]
        assert len(values["lastCallSummary"]) == 300

    def test_values_are_all_strings(self, respond):
        values = respond(_make_assistant_request(), [CUSTOMER], [LAST_CALL])["assistantOverrides"]["variableValues"]
        assert all(isinstance(v, str) for v in values.values())

    def test_other_event_gets_empty_body(self, respond):
        assert respond({"body": {"message": {"type": "status-update"}}}, [{}], [{}]) == {}

    def test_date_of_birth_is_never_fetched_or_returned(self, respond):
        workflow = load_workflow(WORKFLOW)
        select = next(
            p["value"]
            for p in get_node(workflow, "Query Customer")["parameters"]["queryParameters"]["parameters"]
            if p["name"] == "select"
        )
        assert "date_of_birth" not in select
        assert "date_of_birth" not in json.dumps(workflow)


class TestWorkflowWiring:
    def test_webhook_path_and_auth(self):
        webhook = get_node(load_workflow(WORKFLOW), "Webhook")
        assert webhook["parameters"]["path"] == "pre-call-context"
        assert webhook["parameters"]["authentication"] == "headerAuth"
        assert webhook["parameters"]["responseMode"] == "responseNode"

    def test_lookups_are_time_boxed_and_cannot_fail_the_call(self):
        """Two lookups must fit inside VAPI's fixed 7.5 s budget, and errors must fall through."""
        workflow = load_workflow(WORKFLOW)
        total_ms = 0
        for name in ("Query Customer", "Query Last Interaction"):
            node = get_node(workflow, name)
            total_ms += node["parameters"]["options"]["timeout"]
            assert node["onError"] == "continueRegularOutput"
            assert node["alwaysOutputData"] is True
        assert total_ms <= 5000

    def test_customer_lookup_uses_phone_digits(self):
        params = get_node(load_workflow(WORKFLOW), "Query Customer")["parameters"]["queryParameters"]["parameters"]
        assert {"name": "phone_digits", "value": "=eq.{{ $json.phone_digits }}"} in params

    def test_linear_chain_ends_in_respond(self):
        connections = load_workflow(WORKFLOW)["connections"]
        chain, node = ["Webhook"], "Webhook"
        while node in connections:
            node = connections[node]["main"][0][0]["node"]
            chain.append(node)
        assert chain == [
            "Webhook", "Parse Assistant Request", "Query Customer", "Pick Customer",
            "Query Last Interaction", "Build Response", "Respond",
        ]

    def test_no_environment_specific_values_committed(self):
        text = (REPO_ROOT / "n8n" / "workflows" / f"{WORKFLOW}.json").read_text(encoding="utf-8")
        assert "__VAPI_ASSISTANT_ID__" in text
        assert "__SUPABASE_URL__" in text
        assert "supabase.co" not in text


class TestAssistantConfig:
    def _config(self):
        return json.loads((REPO_ROOT / "vapi" / "assistant_config.json").read_text(encoding="utf-8"))

    def test_server_messages_only_contains_valid_values(self):
        """`assistant-request` is not a serverMessages value: VAPI sends it to the phone
        number's server URL, and only when the number has no assistant assigned."""
        assert "assistant-request" not in self._config()["serverMessages"]
        assert {"end-of-call-report", "tool-calls"} <= set(self._config()["serverMessages"])

    def test_default_greeting_is_todays_greeting(self):
        config = self._config()
        assert config["firstMessageMode"] == "assistant-speaks-first"
        assert config["firstMessage"].endswith("How can I help you today?")

    @pytest.mark.parametrize("source", ["json", "markdown"])
    def test_prompt_uses_every_variable_and_guards_claim_details(self, source):
        if source == "json":
            prompt = self._config()["model"]["messages"][0]["content"]
        else:
            prompt = (REPO_ROOT / "vapi" / "system_prompt.md").read_text(encoding="utf-8")
        for name in VARIABLES:
            assert "{{" + name + "}}" in prompt, name
        assert "Caller ID is NOT authentication" in prompt
        assert "last call sentiment is negative" in prompt
        # the unknown-caller path still asks for the phone number, as before
        assert "Ask the caller for the phone number on their account." in prompt
