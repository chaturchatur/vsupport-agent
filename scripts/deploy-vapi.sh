#!/usr/bin/env bash
# Deploy VAPI assistant with actual webhook URLs from .env
# Usage: ./scripts/deploy-vapi.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Load .env
if [ -f "$PROJECT_DIR/.env" ]; then
    set -a
    source "$PROJECT_DIR/.env"
    set +a
else
    echo "ERROR: .env file not found at $PROJECT_DIR/.env"
    exit 1
fi

# Validate required vars
for var in N8N_WEBHOOK_BASE_URL VAPI_SECRET VAPI_API_KEY VAPI_KB_ID; do
    if [ -z "${!var:-}" ]; then
        echo "ERROR: $var is not set in .env"
        exit 1
    fi
done

# Substitute placeholders in assistant config
CONFIG_TEMPLATE="$PROJECT_DIR/vapi/assistant_config.json"
CONFIG_RESOLVED="$PROJECT_DIR/vapi/assistant_config.resolved.json"

sed -e "s|{{N8N_WEBHOOK_BASE_URL}}|$N8N_WEBHOOK_BASE_URL|g" \
    -e "s|{{VAPI_SECRET}}|$VAPI_SECRET|g" \
    -e "s|{{VAPI_KB_ID}}|$VAPI_KB_ID|g" \
    "$CONFIG_TEMPLATE" > "$CONFIG_RESOLVED"

echo "Resolved config written to $CONFIG_RESOLVED"
echo ""

# Deploy via VAPI REST API (CLI create is interactive-only)
if [ -n "${VAPI_ASSISTANT_ID:-}" ]; then
    echo "Updating existing assistant: $VAPI_ASSISTANT_ID"
    RESULT=$(curl -s -X PATCH "https://api.vapi.ai/assistant/$VAPI_ASSISTANT_ID" \
        -H "Authorization: Bearer $VAPI_API_KEY" \
        -H "Content-Type: application/json" \
        -d @"$CONFIG_RESOLVED")
    echo "$RESULT" | python3 -m json.tool 2>/dev/null || echo "$RESULT"
else
    echo "Creating new assistant..."
    RESULT=$(curl -s -X POST "https://api.vapi.ai/assistant" \
        -H "Authorization: Bearer $VAPI_API_KEY" \
        -H "Content-Type: application/json" \
        -d @"$CONFIG_RESOLVED")
    echo "$RESULT" | python3 -m json.tool 2>/dev/null || echo "$RESULT"
    echo ""
    echo "NOTE: Copy the assistant 'id' from above and set VAPI_ASSISTANT_ID in .env"
fi

echo ""
echo "Next steps:"
echo "  1. Set VAPI_ASSISTANT_ID in .env (if new)"
echo "  2. Provision a phone number via VAPI dashboard or API"
echo "  3. Set VAPI_PHONE_NUMBER_ID in .env"
echo "  4. Test with a real call!"
