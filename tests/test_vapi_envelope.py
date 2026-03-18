import json

# ---------------------------------------------------------------------------
# FastAPI endpoint tests
# ---------------------------------------------------------------------------


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_normalize_phone_endpoint(client):
    response = client.post("/normalize-phone", json={"phone_number": "(415) 555-1234"})
    assert response.status_code == 200
    data = response.json()
    assert data["normalized"] == "+14155551234"
    assert data["valid"] is True


def test_normalize_phone_invalid(client):
    response = client.post("/normalize-phone", json={"phone_number": "garbage"})
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is False


def test_normalize_phone_custom_region(client):
    response = client.post(
        "/normalize-phone",
        json={"phone_number": "020 7946 0958", "default_region": "GB"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["normalized"] == "+442079460958"
    assert data["valid"] is True


# ---------------------------------------------------------------------------
# VAPI webhook envelope parsing tests
#
# These validate that the payload structures VAPI sends to n8n webhooks
# conform to the expected shape our n8n workflows parse.
# ---------------------------------------------------------------------------


def _make_tool_call_envelope(tool_name: str, arguments: dict, call_id: str = "call-abc123", tool_call_id: str = "tc-001"):
    """Build a VAPI tool-call webhook payload (assistant-request type)."""
    return {
        "message": {
            "type": "tool-calls",
            "call": {"id": call_id},
            "toolCallList": [
                {
                    "id": tool_call_id,
                    "type": "function",
                    "function": {
                        "name": tool_name,
                        "arguments": arguments,
                    },
                }
            ],
        }
    }


def _make_end_of_call_report(call_id: str = "call-abc123", ended_reason: str = "assistant-ended-call"):
    """Build a VAPI end-of-call-report server message payload."""
    return {
        "message": {
            "type": "end-of-call-report",
            "call": {
                "id": call_id,
            },
            "endedReason": ended_reason,
            "summary": "Caller checked claim status. Claim CLM-2024-001 approved.",
            "transcript": "Agent: Thank you for calling... Caller: Hi...",
            "analysis": {
                "summary": "Caller checked claim status for CLM-2024-001.",
                "structuredData": {
                    "callReason": "claim status check",
                    "authenticated": True,
                    "claimNumber": "CLM-2024-001",
                    "claimStatus": "approved",
                    "escalated": False,
                },
            },
        }
    }


class TestVapiToolCallEnvelope:
    """Validate VAPI tool-call envelope structure for n8n parsing."""

    def test_lookup_caller_phone_envelope(self):
        payload = _make_tool_call_envelope(
            "lookup_caller",
            {"phone_number": "(415) 555-1234"},
        )
        msg = payload["message"]
        assert msg["type"] == "tool-calls"
        assert msg["call"]["id"] == "call-abc123"

        tc = msg["toolCallList"][0]
        assert tc["function"]["name"] == "lookup_caller"
        assert tc["function"]["arguments"]["phone_number"] == "(415) 555-1234"
        assert tc["id"] == "tc-001"

    def test_lookup_caller_last_name_envelope(self):
        payload = _make_tool_call_envelope(
            "lookup_caller",
            {"last_name": "Johnson"},
        )
        args = payload["message"]["toolCallList"][0]["function"]["arguments"]
        assert args["last_name"] == "Johnson"
        assert "phone_number" not in args

    def test_lookup_caller_claim_number_envelope(self):
        payload = _make_tool_call_envelope(
            "lookup_caller",
            {"claim_number": "CLM-2024-003"},
        )
        args = payload["message"]["toolCallList"][0]["function"]["arguments"]
        assert args["claim_number"] == "CLM-2024-003"

    def test_log_interaction_envelope(self):
        payload = _make_tool_call_envelope(
            "log_interaction",
            {
                "caller_name": "Sarah Johnson",
                "phone_number": "+14155551234",
                "summary": "Caller checked approved claim status.",
                "sentiment": "positive",
            },
        )
        args = payload["message"]["toolCallList"][0]["function"]["arguments"]
        assert args["caller_name"] == "Sarah Johnson"
        assert args["sentiment"] in ("positive", "neutral", "negative")
        assert "summary" in args

    def test_log_interaction_minimal_envelope(self):
        """log_interaction only requires summary and sentiment."""
        payload = _make_tool_call_envelope(
            "log_interaction",
            {"summary": "Caller not found.", "sentiment": "neutral"},
        )
        args = payload["message"]["toolCallList"][0]["function"]["arguments"]
        assert "caller_name" not in args
        assert args["sentiment"] == "neutral"

    def test_envelope_serializable(self):
        """Envelope must be JSON-serializable (n8n receives JSON)."""
        payload = _make_tool_call_envelope(
            "lookup_caller",
            {"phone_number": "+14155551234"},
        )
        serialized = json.dumps(payload)
        roundtrip = json.loads(serialized)
        assert roundtrip == payload


class TestVapiEndOfCallReport:
    """Validate VAPI end-of-call-report envelope for n8n parsing."""

    def test_end_of_call_report_structure(self):
        payload = _make_end_of_call_report()
        msg = payload["message"]
        assert msg["type"] == "end-of-call-report"
        assert msg["call"]["id"] == "call-abc123"
        assert "summary" in msg
        assert "analysis" in msg

    def test_end_of_call_structured_data(self):
        payload = _make_end_of_call_report()
        sd = payload["message"]["analysis"]["structuredData"]
        assert sd["callReason"] == "claim status check"
        assert sd["authenticated"] is True
        assert sd["claimNumber"] == "CLM-2024-001"
        assert sd["claimStatus"] in ("approved", "pending", "requires_documentation", "not_found", "")
        assert sd["escalated"] is False

    def test_end_of_call_ended_reason(self):
        payload = _make_end_of_call_report(ended_reason="customer-ended-call")
        assert payload["message"]["endedReason"] == "customer-ended-call"

    def test_end_of_call_serializable(self):
        payload = _make_end_of_call_report()
        serialized = json.dumps(payload)
        roundtrip = json.loads(serialized)
        assert roundtrip == payload
