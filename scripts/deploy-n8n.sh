#!/usr/bin/env bash
# Deploy n8n workflow JSONs to n8n Cloud via REST API
# Usage: ./scripts/deploy-n8n.sh [workflow-name]
#   ./scripts/deploy-n8n.sh                  # deploy all
#   ./scripts/deploy-n8n.sh log-interaction   # deploy one
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
    workflow_id=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['id'])" "$json_file")

    echo "Deploying: $name (ID: $workflow_id)"

    # Strip read-only fields before sending (API rejects them)
    local payload
    payload=$(python3 -c "
import json,sys
d=json.load(open(sys.argv[1]))
for k in ['id','active','createdAt','updatedAt','versionId']:
    d.pop(k,None)
print(json.dumps(d))
" "$json_file")

    # PUT the workflow JSON
    local http_code
    http_code=$(curl -s -o /tmp/n8n_deploy_response.json -w "%{http_code}" \
        -X PUT "$N8N_API_BASE/workflows/$workflow_id" \
        -H "X-N8N-API-KEY: $N8N_API_KEY" \
        -H "Content-Type: application/json" \
        -d "$payload")

    if [ "$http_code" -ge 200 ] && [ "$http_code" -lt 300 ]; then
        echo "  Updated successfully (HTTP $http_code)"
    else
        echo "  FAILED (HTTP $http_code)"
        cat /tmp/n8n_deploy_response.json
        echo ""
        return 1
    fi

    # Activate the workflow
    http_code=$(curl -s -o /tmp/n8n_deploy_response.json -w "%{http_code}" \
        -X POST "$N8N_API_BASE/workflows/$workflow_id/activate" \
        -H "X-N8N-API-KEY: $N8N_API_KEY")

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
