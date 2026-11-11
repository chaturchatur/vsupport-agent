#!/usr/bin/env bash
# Switch the VAPI phone number between "dynamic" and "static" assistant selection.
#
#   ./scripts/configure-vapi-phone.sh enable    # pre-call recognition ON
#   ./scripts/configure-vapi-phone.sh disable   # rollback: number -> assistant directly
#
# Why this exists: VAPI only sends `assistant-request` when the phone number has NO
# assistant assigned, and it sends it to the PHONE NUMBER's server URL (there is no
# assistant yet whose server URL could be used). So enabling pre-call recognition
# means un-assigning the assistant from the number and pointing the number at the
# pre-call-context webhook. If that webhook is down or slower than 7.5 s, inbound
# calls FAIL: `disable` is the rollback.
#
# NOT run by any other script. Changes live call routing.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

if [ -f "$PROJECT_DIR/.env" ]; then
    set -a
    source "$PROJECT_DIR/.env"
    set +a
else
    echo "ERROR: .env file not found at $PROJECT_DIR/.env"
    exit 1
fi

for var in VAPI_API_KEY VAPI_PHONE_NUMBER_ID VAPI_ASSISTANT_ID N8N_WEBHOOK_BASE_URL VAPI_SECRET; do
    if [ -z "${!var:-}" ]; then
        echo "ERROR: $var is not set in .env"
        exit 1
    fi
done

case "${1:-}" in
    enable)
        # server.headers is how the assistant config authenticates to n8n. VAPI's docs
        # show `server.url` for phone numbers but do not document `server.headers` there:
        # after running this, confirm in the VAPI dashboard (Phone Numbers -> Server URL
        # -> HTTP Headers) that x-vapi-secret is present. Without it n8n answers 403
        # and calls fail.
        BODY=$(cat <<EOF
{
  "assistantId": null,
  "squadId": null,
  "server": {
    "url": "$N8N_WEBHOOK_BASE_URL/webhook/pre-call-context",
    "headers": { "x-vapi-secret": "$VAPI_SECRET" }
  }
}
EOF
)
        echo "Enabling pre-call recognition on phone number $VAPI_PHONE_NUMBER_ID"
        ;;
    disable)
        BODY=$(cat <<EOF
{
  "assistantId": "$VAPI_ASSISTANT_ID",
  "server": null
}
EOF
)
        echo "Rolling back: assigning assistant $VAPI_ASSISTANT_ID directly to phone number $VAPI_PHONE_NUMBER_ID"
        ;;
    *)
        echo "Usage: $0 enable|disable"
        exit 2
        ;;
esac

RESULT=$(curl -s -X PATCH "https://api.vapi.ai/phone-number/$VAPI_PHONE_NUMBER_ID" \
    -H "Authorization: Bearer $VAPI_API_KEY" \
    -H "Content-Type: application/json" \
    -d "$BODY")
echo "$RESULT" | python3 -m json.tool 2>/dev/null || echo "$RESULT"
