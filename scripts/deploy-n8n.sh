#!/usr/bin/env bash
# Deploy n8n workflow JSONs to n8n Cloud via REST API
# Usage: ./scripts/deploy-n8n.sh [workflow-name]
#   ./scripts/deploy-n8n.sh                  # deploy all
#   ./scripts/deploy-n8n.sh log-interaction   # deploy one
#
# Workflow exports may contain __PLACEHOLDER__ values (alert recipient, Twilio
# sender, assistant id, ...). They are filled in from .env at deploy time by
# scripts/resolve_n8n_placeholders.py, so nothing environment-specific is committed.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
WORKFLOWS_DIR="$PROJECT_DIR/n8n/workflows"

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
for var in N8N_API_KEY N8N_WEBHOOK_BASE_URL; do
    if [ -z "${!var:-}" ]; then
        echo "ERROR: $var is not set in .env"
        exit 1
    fi
done

N8N_API_BASE="${N8N_WEBHOOK_BASE_URL}/api/v1"

deploy_workflow() {
    local json_file="$1"
    local name
    name=$(basename "$json_file" .json)
    local workflow_id
    workflow_id=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1])).get('id') or '')" "$json_file")

    # Resolve __PLACEHOLDER__ values from .env and strip read-only fields
    # (the API rejects them). Fails if a required value is missing.
    local payload
    if ! payload=$(python3 "$SCRIPT_DIR/resolve_n8n_placeholders.py" "$json_file"); then
        echo "  FAILED: could not resolve placeholders for $name"
        return 1
    fi

    local http_code
    if [ -z "$workflow_id" ]; then
        # No id in the export yet: first deploy of a new workflow -> create it.
        echo "Creating: $name (no workflow id in $json_file yet)"
        http_code=$(curl -s -o /tmp/n8n_deploy_response.json -w "%{http_code}"             -X POST "$N8N_API_BASE/workflows"             -H "X-N8N-API-KEY: $N8N_API_KEY"             -H "Content-Type: application/json"             -d "$payload")
        if [ "$http_code" -ge 200 ] && [ "$http_code" -lt 300 ]; then
            workflow_id=$(python3 -c "import json; print(json.load(open('/tmp/n8n_deploy_response.json'))['id'])")
            echo "  Created (HTTP $http_code) with ID: $workflow_id"
            echo "  ACTION: set \"id\": \"$workflow_id\" at the top of $json_file and commit it,"
            echo "          otherwise the next deploy creates a second copy."
        else
            echo "  FAILED (HTTP $http_code)"
            cat /tmp/n8n_deploy_response.json
            echo ""
            return 1
        fi
    else
        echo "Deploying: $name (ID: $workflow_id)"
        http_code=$(curl -s -o /tmp/n8n_deploy_response.json -w "%{http_code}"             -X PUT "$N8N_API_BASE/workflows/$workflow_id"             -H "X-N8N-API-KEY: $N8N_API_KEY"             -H "Content-Type: application/json"             -d "$payload")

        if [ "$http_code" -ge 200 ] && [ "$http_code" -lt 300 ]; then
            echo "  Updated successfully (HTTP $http_code)"
        else
            echo "  FAILED (HTTP $http_code)"
            cat /tmp/n8n_deploy_response.json
            echo ""
            return 1
        fi
    fi

    # Activate the workflow
    http_code=$(curl -s -o /tmp/n8n_deploy_response.json -w "%{http_code}"         -X POST "$N8N_API_BASE/workflows/$workflow_id/activate"         -H "X-N8N-API-KEY: $N8N_API_KEY")

    if [ "$http_code" -ge 200 ] && [ "$http_code" -lt 300 ]; then
        echo "  Activated"
    else
        echo "  Activation failed (HTTP $http_code)"
        cat /tmp/n8n_deploy_response.json
        echo ""
        return 1
    fi

    echo ""
}

# Deploy specific workflow or all
if [ -n "${1:-}" ]; then
    json_file="$WORKFLOWS_DIR/$1.json"
    if [ ! -f "$json_file" ]; then
        echo "ERROR: $json_file not found"
        echo "Available workflows:"
        ls "$WORKFLOWS_DIR"/*.json 2>/dev/null | xargs -I{} basename {} .json | sed 's/^/  /'
        exit 1
    fi
    deploy_workflow "$json_file"
else
    echo "Deploying all workflows to n8n Cloud..."
    echo "Host: $N8N_WEBHOOK_BASE_URL"
    echo ""
    failed=0
    for json_file in "$WORKFLOWS_DIR"/*.json; do
        deploy_workflow "$json_file" || ((failed++))
    done
    if [ "$failed" -gt 0 ]; then
        echo "WARNING: $failed workflow(s) failed to deploy"
        exit 1
    fi
    echo "All workflows deployed successfully!"
fi
