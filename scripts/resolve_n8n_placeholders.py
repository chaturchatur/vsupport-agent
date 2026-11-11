#!/usr/bin/env python3
"""Turn a workflow export from n8n/workflows/ into the payload sent to the n8n API.

The repo copies of the workflows never contain deployment-specific values.
Anything that differs per environment is a ``__NAME__`` placeholder that is
filled in from the environment (``.env``, loaded by ``deploy-n8n.sh``) here:

    required (deploy fails if the workflow uses one and it is unset)
        __VAPI_ASSISTANT_ID__        assistant returned by pre-call-context
        __SUPABASE_URL__             base URL for pre-call-context's REST reads

    optional (unset -> empty string -> the workflow skips that action)
        __ALERT_EMAIL_TO__           who gets the escalation alert
        __ALERT_EMAIL_FROM__         sender address for the alert
        __N8N_SMTP_CREDENTIAL_ID__   n8n SMTP credential id
        __TWILIO_FROM_NUMBER__       Twilio sender number (E.164)
        __N8N_TWILIO_CREDENTIAL_ID__ n8n Twilio credential id

Usage: python3 scripts/resolve_n8n_placeholders.py n8n/workflows/<name>.json
"""

import json
import os
import re
import sys

REQUIRED = ("VAPI_ASSISTANT_ID", "SUPABASE_URL")
OPTIONAL = (
    "ALERT_EMAIL_TO",
    "ALERT_EMAIL_FROM",
    "N8N_SMTP_CREDENTIAL_ID",
    "TWILIO_FROM_NUMBER",
    "N8N_TWILIO_CREDENTIAL_ID",
)
READ_ONLY_KEYS = ("id", "active", "createdAt", "updatedAt", "versionId")

# Values are pasted into JSON strings *and* into single-quoted JS literals inside
# Code nodes, so anything that could close a string or start an expression is refused.
_UNSAFE = re.compile(r"""['"\\`\r\n{}$]""")


class PlaceholderError(ValueError):
    """A placeholder could not be resolved safely."""


def resolve_placeholders(text: str, env: dict) -> str:
    """Replace every ``__NAME__`` placeholder in ``text`` using ``env``."""
    for name in REQUIRED + OPTIONAL:
        token = f"__{name}__"
        if token not in text:
            continue
        value = (env.get(name) or "").strip()
        if not value and name in REQUIRED:
            raise PlaceholderError(f"{name} is not set in .env but this workflow needs it")
        if _UNSAFE.search(value):
            raise PlaceholderError(f"{name} contains a character that is not allowed in a workflow value")
        if name == "SUPABASE_URL":
            value = value.rstrip("/")
        text = text.replace(token, value)
    return text


def build_payload(workflow_text: str, env: dict) -> dict:
    """Resolve placeholders and return the body for POST/PUT /workflows."""
    workflow = json.loads(resolve_placeholders(workflow_text, env))
    for key in READ_ONLY_KEYS:
        workflow.pop(key, None)
    # A node whose credential id resolved to "" has no credential to point at.
    # Drop the reference so n8n does not store a dangling one; the workflow's own
    # "configured?" checks keep that node from ever running.
    for node in workflow.get("nodes", []):
        creds = node.get("credentials")
        if not creds:
            continue
        kept = {kind: ref for kind, ref in creds.items() if ref.get("id")}
        if kept:
            node["credentials"] = kept
        else:
            del node["credentials"]
    return workflow


def main(argv: list) -> int:
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    with open(argv[1], encoding="utf-8") as fh:
        text = fh.read()
    try:
        payload = build_payload(text, dict(os.environ))
    except PlaceholderError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(payload))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
