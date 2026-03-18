#!/usr/bin/env python3
"""Create all three n8n workflows via the n8n REST API.

Workflows:
  1. lookup-caller   — VAPI tool call → Airtable Customers search
  2. log-interaction — VAPI tool call → Airtable Interactions create
  3. end-of-call-report — VAPI serverUrl webhook → dedup check → Airtable Interactions create

Prerequisites:
  - N8N_API_KEY and N8N_WEBHOOK_BASE_URL set in .env
  - Airtable PAT credential created (id: 72gACBmxGU7HuQB9)
  - Header Auth credential created (id: PQXagW16N8ErYDM7)
"""

import json
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv()

N8N_API_KEY = os.environ["N8N_API_KEY"]
N8N_BASE_URL = os.environ["N8N_WEBHOOK_BASE_URL"]
API_URL = f"{N8N_BASE_URL}/api/v1"

AIRTABLE_CRED_ID = "72gACBmxGU7HuQB9"
HEADER_AUTH_CRED_ID = "PQXagW16N8ErYDM7"
AIRTABLE_BASE_ID = os.environ["AIRTABLE_BASE_ID"]
CUSTOMERS_TABLE_ID = "tbl8aUdxcp0Vt2MXc"
INTERACTIONS_TABLE_ID = "tblKsTpur4w8kqcW1"

HEADERS = {
    "X-N8N-API-KEY": N8N_API_KEY,
    "Content-Type": "application/json",
}

EXPORT_DIR = Path(__file__).resolve().parent.parent / "n8n" / "workflows"


def create_workflow(workflow_json: dict) -> dict:
    """Create a workflow via n8n API and return the response."""
    resp = httpx.post(f"{API_URL}/workflows", headers=HEADERS, json=workflow_json, timeout=30)
    resp.raise_for_status()
    return resp.json()


def activate_workflow(workflow_id: str) -> dict:
    """Activate a workflow via n8n API."""
    resp = httpx.post(
        f"{API_URL}/workflows/{workflow_id}/activate",
        headers=HEADERS,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def export_workflow(workflow_id: str, filename: str):
    """Fetch full workflow JSON and save to n8n/workflows/."""
    resp = httpx.get(f"{API_URL}/workflows/{workflow_id}", headers=HEADERS, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    filepath = EXPORT_DIR / filename
    filepath.write_text(json.dumps(data, indent=2))
    print(f"  Exported to {filepath}")


# ── Credential references ──────────────────────────────────────────

airtable_cred = {
    "airtableTokenApi": {
        "id": AIRTABLE_CRED_ID,
        "name": "Airtable PAT",
    }
}

header_auth_cred = {
    "httpHeaderAuth": {
        "id": HEADER_AUTH_CRED_ID,
        "name": "VAPI Webhook Secret",
    }
}


# ── Workflow 1: Lookup Caller ───────────────────────────────────────

LOOKUP_CALLER_CODE = r"""
// Extract VAPI tool call envelope
const body = $input.first().json.body;
const message = body.message;

// Extract call ID and tool call details
const vapiCallId = message.call?.id || '';
const toolCall = message.toolCallList?.[0] || {};
const toolCallId = toolCall.id || '';
const args = toolCall.function?.arguments || {};

// Parse search parameters
const phone_number = (args.phone_number || '').trim();
const last_name = (args.last_name || '').trim();
const claim_number = (args.claim_number || '').trim();

// Determine search mode
let searchMode = '';
let searchValue = '';
let filterFormula = '';

if (phone_number) {
  // Normalize phone: strip non-digit chars, prepend +1 if 10 digits
  let normalized = phone_number.replace(/[^\d+]/g, '');
  if (normalized.length === 10) normalized = '+1' + normalized;
  else if (normalized.length === 11 && normalized.startsWith('1')) normalized = '+' + normalized;
  else if (!normalized.startsWith('+')) normalized = '+' + normalized;
  searchMode = 'phone_number';
  searchValue = normalized;
  filterFormula = `{phone_number} = '${normalized}'`;
} else if (last_name) {
  searchMode = 'last_name';
  searchValue = last_name;
  filterFormula = `LOWER({last_name}) = LOWER('${last_name}')`;
} else if (claim_number) {
  searchMode = 'claim_number';
  searchValue = claim_number;
  filterFormula = `UPPER({claim_number}) = UPPER('${claim_number}')`;
} else {
  // No search params provided
  return [{
    json: {
      toolCallId,
      vapiCallId,
      error: true,
      filterFormula: '',
      searchMode: 'none',
      resultMessage: JSON.stringify({
        found: false,
        error: true,
        message: "No search parameters provided. Please provide a phone number, last name, or claim number."
      })
    }
  }];
}

return [{
  json: {
    toolCallId,
    vapiCallId,
    searchMode,
    searchValue,
    filterFormula,
    error: false,
    resultMessage: ''
  }
}];
"""

LOOKUP_FORMAT_CODE = r"""
// Format Airtable results for VAPI response
const inputData = $('Parse VAPI Envelope').first().json;
const toolCallId = inputData.toolCallId;
const searchMode = inputData.searchMode;

// Get Airtable results - may be empty array
const airtableItems = $input.all();
const records = airtableItems.filter(item => item.json.id); // filter out empty results

let result;

if (records.length === 0) {
  result = {
    found: false,
    message: "No matching record found in our system."
  };
} else if (records.length === 1) {
  const r = records[0].json;
  result = {
    found: true,
    multiple: false,
    first_name: r.first_name || '',
    last_name: r.last_name || '',
    claim_number: r.claim_number || '',
    claim_status: r.claim_status || '',
    claim_details: r.claim_details || '',
    phone_number: r.phone_number || ''
  };
} else {
  // Multiple matches
  result = {
    found: true,
    multiple: true,
    matches: records.map(item => ({
      first_name: item.json.first_name || '',
      last_name: item.json.last_name || '',
      claim_number: item.json.claim_number || '',
      claim_status: item.json.claim_status || ''
    }))
  };
}

return [{
  json: {
    results: [{
      toolCallId: toolCallId,
      result: JSON.stringify(result)
    }]
  }
}];
"""

LOOKUP_ERROR_CODE = r"""
// Format error response for VAPI
const inputData = $('Parse VAPI Envelope').first().json;
const toolCallId = inputData.toolCallId;

const result = {
  found: false,
  error: true,
  message: "System temporarily unavailable. Please try again later."
};

return [{
  json: {
    results: [{
      toolCallId: toolCallId,
      result: JSON.stringify(result)
    }]
  }
}];
"""

lookup_caller_workflow = {
    "name": "Lookup Caller",
    "nodes": [
        {
            "parameters": {
                "httpMethod": "POST",
                "path": "lookup-caller",
                "authentication": "headerAuth",
                "responseMode": "responseNode",
                "options": {},
            },
            "id": "webhook-lookup",
            "name": "Webhook",
            "type": "n8n-nodes-base.webhook",
            "typeVersion": 2,
            "position": [0, 0],
            "webhookId": "lookup-caller",
            "credentials": header_auth_cred,
        },
        {
            "parameters": {
                "jsCode": LOOKUP_CALLER_CODE,
            },
            "id": "parse-envelope",
            "name": "Parse VAPI Envelope",
            "type": "n8n-nodes-base.code",
            "typeVersion": 2,
            "position": [220, 0],
        },
        {
            "parameters": {
                "conditions": {
                    "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict"},
                    "conditions": [
                        {
                            "id": "cond-no-error",
                            "leftValue": "={{ $json.error }}",
                            "rightValue": False,
                            "operator": {"type": "boolean", "operation": "equals", "singleValue": True},
                        }
                    ],
                    "combinator": "and",
                },
                "options": {},
            },
            "id": "if-valid",
            "name": "Has Search Params?",
            "type": "n8n-nodes-base.if",
            "typeVersion": 2,
            "position": [440, 0],
        },
        {
            "parameters": {
                "operation": "search",
                "base": {
                    "__rl": True,
                    "value": AIRTABLE_BASE_ID,
                    "mode": "id",
                },
                "table": {
                    "__rl": True,
                    "value": CUSTOMERS_TABLE_ID,
                    "mode": "id",
                },
                "filterByFormula": "={{ $json.filterFormula }}",
                "options": {},
            },
            "id": "airtable-search",
            "name": "Search Customers",
            "type": "n8n-nodes-base.airtable",
            "typeVersion": 2.1,
            "position": [660, -60],
            "credentials": airtable_cred,
            "onError": "continueErrorOutput",
        },
        {
            "parameters": {
                "jsCode": LOOKUP_FORMAT_CODE,
            },
            "id": "format-result",
            "name": "Format Result",
            "type": "n8n-nodes-base.code",
            "typeVersion": 2,
            "position": [880, -120],
        },
        {
            "parameters": {
                "jsCode": LOOKUP_ERROR_CODE,
            },
            "id": "format-error",
            "name": "Format Error",
            "type": "n8n-nodes-base.code",
            "typeVersion": 2,
            "position": [880, 60],
        },
        {
            "parameters": {
                "respondWith": "json",
                "responseBody": "={{ JSON.stringify($json) }}",
                "options": {},
            },
            "id": "respond-success",
            "name": "Respond Success",
            "type": "n8n-nodes-base.respondToWebhook",
            "typeVersion": 1.1,
            "position": [1100, -120],
        },
        {
            "parameters": {
                "respondWith": "json",
                "responseBody": "={{ JSON.stringify($json) }}",
                "options": {},
            },
            "id": "respond-error",
            "name": "Respond Error",
            "type": "n8n-nodes-base.respondToWebhook",
            "typeVersion": 1.1,
            "position": [1100, 60],
        },
        {
            "parameters": {
                "respondWith": "json",
                "responseBody": '={{ JSON.stringify({ results: [{ toolCallId: $json.toolCallId, result: $json.resultMessage }] }) }}',
                "options": {},
            },
            "id": "respond-no-params",
            "name": "Respond No Params",
            "type": "n8n-nodes-base.respondToWebhook",
            "typeVersion": 1.1,
            "position": [660, 120],
        },
    ],
    "connections": {
        "Webhook": {
            "main": [[{"node": "Parse VAPI Envelope", "type": "main", "index": 0}]]
        },
        "Parse VAPI Envelope": {
            "main": [[{"node": "Has Search Params?", "type": "main", "index": 0}]]
        },
        "Has Search Params?": {
            "main": [
                # true branch - has valid search params
                [{"node": "Search Customers", "type": "main", "index": 0}],
                # false branch - no params / error
                [{"node": "Respond No Params", "type": "main", "index": 0}],
            ]
        },
        "Search Customers": {
            "main": [
                # success branch
                [{"node": "Format Result", "type": "main", "index": 0}],
                # error branch
                [{"node": "Format Error", "type": "main", "index": 0}],
            ]
        },
        "Format Result": {
            "main": [[{"node": "Respond Success", "type": "main", "index": 0}]]
        },
        "Format Error": {
            "main": [[{"node": "Respond Error", "type": "main", "index": 0}]]
        },
    },
    "settings": {
        "executionOrder": "v1",
    },
}


# ── Workflow 2: Log Interaction ─────────────────────────────────────

LOG_INTERACTION_PARSE_CODE = r"""
// Extract VAPI tool call envelope for log_interaction
const body = $input.first().json.body;
const message = body.message;

const vapiCallId = message.call?.id || '';
const toolCall = message.toolCallList?.[0] || {};
const toolCallId = toolCall.id || '';
const args = toolCall.function?.arguments || {};

const caller_name = (args.caller_name || 'Unknown').trim();
const phone_number = (args.phone_number || '').trim();
const summary = (args.summary || '').trim();
const sentiment = (args.sentiment || 'neutral').trim();
const timestamp = new Date().toISOString();

return [{
  json: {
    toolCallId,
    vapiCallId,
    caller_name,
    phone_number,
    summary,
    sentiment,
    timestamp
  }
}];
"""

LOG_INTERACTION_SUCCESS_CODE = r"""
// Format success response
const inputData = $('Parse Log Envelope').first().json;
const toolCallId = inputData.toolCallId;
const recordId = $input.first().json.id || 'unknown';

const result = {
  success: true,
  record_id: recordId
};

return [{
  json: {
    results: [{
      toolCallId: toolCallId,
      result: JSON.stringify(result)
    }]
  }
}];
"""

LOG_INTERACTION_ERROR_CODE = r"""
// Format error response
const inputData = $('Parse Log Envelope').first().json;
const toolCallId = inputData.toolCallId;

const result = {
  success: false,
  error: "Failed to save interaction record"
};

return [{
  json: {
    results: [{
      toolCallId: toolCallId,
      result: JSON.stringify(result)
    }]
  }
}];
"""

log_interaction_workflow = {
    "name": "Log Interaction",
    "nodes": [
        {
            "parameters": {
                "httpMethod": "POST",
                "path": "log-interaction",
                "authentication": "headerAuth",
                "responseMode": "responseNode",
                "options": {},
            },
            "id": "webhook-log",
            "name": "Webhook",
            "type": "n8n-nodes-base.webhook",
            "typeVersion": 2,
            "position": [0, 0],
            "webhookId": "log-interaction",
            "credentials": header_auth_cred,
        },
        {
            "parameters": {
                "jsCode": LOG_INTERACTION_PARSE_CODE,
            },
            "id": "parse-log",
            "name": "Parse Log Envelope",
            "type": "n8n-nodes-base.code",
            "typeVersion": 2,
            "position": [220, 0],
        },
        {
            "parameters": {
                "operation": "create",
                "base": {
                    "__rl": True,
                    "value": AIRTABLE_BASE_ID,
                    "mode": "id",
                },
                "table": {
                    "__rl": True,
                    "value": INTERACTIONS_TABLE_ID,
                    "mode": "id",
                },
                "columns": {
                    "mappingMode": "defineBelow",
                    "value": {
                        "caller_name": "={{ $json.caller_name }}",
                        "phone_number": "={{ $json.phone_number }}",
                        "summary": "={{ $json.summary }}",
                        "sentiment": "={{ $json.sentiment }}",
                        "timestamp": "={{ $json.timestamp }}",
                        "vapi_call_id": "={{ $json.vapiCallId }}",
                    },
                },
                "options": {},
            },
            "id": "airtable-create",
            "name": "Create Interaction",
            "type": "n8n-nodes-base.airtable",
            "typeVersion": 2.1,
            "position": [440, 0],
            "credentials": airtable_cred,
            "onError": "continueErrorOutput",
        },
        {
            "parameters": {
                "jsCode": LOG_INTERACTION_SUCCESS_CODE,
            },
            "id": "format-success",
            "name": "Format Success",
            "type": "n8n-nodes-base.code",
            "typeVersion": 2,
            "position": [660, -60],
        },
        {
            "parameters": {
                "jsCode": LOG_INTERACTION_ERROR_CODE,
            },
            "id": "format-log-error",
            "name": "Format Error",
            "type": "n8n-nodes-base.code",
            "typeVersion": 2,
            "position": [660, 60],
        },
        {
            "parameters": {
                "respondWith": "json",
                "responseBody": "={{ JSON.stringify($json) }}",
                "options": {},
            },
            "id": "respond-log-success",
            "name": "Respond Success",
            "type": "n8n-nodes-base.respondToWebhook",
            "typeVersion": 1.1,
            "position": [880, -60],
        },
        {
            "parameters": {
                "respondWith": "json",
                "responseBody": "={{ JSON.stringify($json) }}",
                "options": {},
            },
            "id": "respond-log-error",
            "name": "Respond Error",
            "type": "n8n-nodes-base.respondToWebhook",
            "typeVersion": 1.1,
            "position": [880, 60],
        },
    ],
    "connections": {
        "Webhook": {
            "main": [[{"node": "Parse Log Envelope", "type": "main", "index": 0}]]
        },
        "Parse Log Envelope": {
            "main": [[{"node": "Create Interaction", "type": "main", "index": 0}]]
        },
        "Create Interaction": {
            "main": [
                [{"node": "Format Success", "type": "main", "index": 0}],
                [{"node": "Format Error", "type": "main", "index": 0}],
            ]
        },
        "Format Success": {
            "main": [[{"node": "Respond Success", "type": "main", "index": 0}]]
        },
        "Format Error": {
            "main": [[{"node": "Respond Error", "type": "main", "index": 0}]]
        },
    },
    "settings": {
        "executionOrder": "v1",
    },
}


# ── Workflow 3: End-of-Call Report ──────────────────────────────────

EOC_PARSE_CODE = r"""
// Extract end-of-call-report data from VAPI serverUrl webhook
const body = $input.first().json.body;
const message = body.message;

// Filter: only process end-of-call-report messages
const messageType = message.type || '';
if (messageType !== 'end-of-call-report') {
  // Not an end-of-call-report, stop processing
  return [];
}

const vapiCallId = message.call?.id || '';
const summary = message.analysis?.summary || message.artifact?.messages?.map(m => m.content || '').join(' ').substring(0, 500) || 'No summary available';
const sentiment = message.analysis?.structuredData?.sentiment || 'neutral';

// Try to extract caller phone from call data
const callerPhone = message.call?.customer?.number || '';
const callerName = message.analysis?.structuredData?.callerName || 'Unknown';

return [{
  json: {
    vapiCallId,
    summary,
    sentiment: ['positive', 'neutral', 'negative'].includes(sentiment) ? sentiment : 'neutral',
    callerPhone,
    callerName,
    timestamp: new Date().toISOString()
  }
}];
"""

EOC_CREATE_CODE = r"""
// Check dedup results - if record already exists, skip
const searchResults = $input.all();
const hasExisting = searchResults.some(item => item.json.id);

if (hasExisting) {
  // Already logged by log_interaction tool call — skip
  return [];
}

// Pass through the parsed data for creation
const parsed = $('Parse EOC Envelope').first().json;
return [{
  json: {
    caller_name: parsed.callerName,
    phone_number: parsed.callerPhone,
    summary: parsed.summary,
    sentiment: parsed.sentiment,
    timestamp: parsed.timestamp,
    vapi_call_id: parsed.vapiCallId
  }
}];
"""

eoc_workflow = {
    "name": "End-of-Call Report",
    "nodes": [
        {
            "parameters": {
                "httpMethod": "POST",
                "path": "vapi-server",
                "authentication": "headerAuth",
                "responseMode": "lastNode",
                "options": {},
            },
            "id": "webhook-eoc",
            "name": "Webhook",
            "type": "n8n-nodes-base.webhook",
            "typeVersion": 2,
            "position": [0, 0],
            "webhookId": "vapi-server",
            "credentials": header_auth_cred,
        },
        {
            "parameters": {
                "jsCode": EOC_PARSE_CODE,
            },
            "id": "parse-eoc",
            "name": "Parse EOC Envelope",
            "type": "n8n-nodes-base.code",
            "typeVersion": 2,
            "position": [220, 0],
        },
        {
            "parameters": {
                "amount": 10,
                "unit": "seconds",
            },
            "id": "wait-node",
            "name": "Wait 10s",
            "type": "n8n-nodes-base.wait",
            "typeVersion": 1.1,
            "position": [440, 0],
        },
        {
            "parameters": {
                "operation": "search",
                "base": {
                    "__rl": True,
                    "value": AIRTABLE_BASE_ID,
                    "mode": "id",
                },
                "table": {
                    "__rl": True,
                    "value": INTERACTIONS_TABLE_ID,
                    "mode": "id",
                },
                "filterByFormula": "={{ '{vapi_call_id} = \\'' + $('Parse EOC Envelope').first().json.vapiCallId + '\\'' }}",
                "options": {},
            },
            "id": "airtable-dedup",
            "name": "Check Dedup",
            "type": "n8n-nodes-base.airtable",
            "typeVersion": 2.1,
            "position": [660, 0],
            "credentials": airtable_cred,
            "onError": "continueErrorOutput",
        },
        {
            "parameters": {
                "jsCode": EOC_CREATE_CODE,
            },
            "id": "check-dedup",
            "name": "Filter Existing",
            "type": "n8n-nodes-base.code",
            "typeVersion": 2,
            "position": [880, -60],
        },
        {
            "parameters": {
                "operation": "create",
                "base": {
                    "__rl": True,
                    "value": AIRTABLE_BASE_ID,
                    "mode": "id",
                },
                "table": {
                    "__rl": True,
                    "value": INTERACTIONS_TABLE_ID,
                    "mode": "id",
                },
                "columns": {
                    "mappingMode": "defineBelow",
                    "value": {
                        "caller_name": "={{ $json.caller_name }}",
                        "phone_number": "={{ $json.phone_number }}",
                        "summary": "={{ $json.summary }}",
                        "sentiment": "={{ $json.sentiment }}",
                        "timestamp": "={{ $json.timestamp }}",
                        "vapi_call_id": "={{ $json.vapi_call_id }}",
                    },
                },
                "options": {},
            },
            "id": "airtable-create-eoc",
            "name": "Create Interaction",
            "type": "n8n-nodes-base.airtable",
            "typeVersion": 2.1,
            "position": [1100, -60],
            "credentials": airtable_cred,
        },
        {
            "parameters": {},
            "id": "noop-end",
            "name": "No Operation",
            "type": "n8n-nodes-base.noOp",
            "typeVersion": 1,
            "position": [1100, 60],
        },
    ],
    "connections": {
        "Webhook": {
            "main": [[{"node": "Parse EOC Envelope", "type": "main", "index": 0}]]
        },
        "Parse EOC Envelope": {
            "main": [[{"node": "Wait 10s", "type": "main", "index": 0}]]
        },
        "Wait 10s": {
            "main": [[{"node": "Check Dedup", "type": "main", "index": 0}]]
        },
        "Check Dedup": {
            "main": [
                # success branch
                [{"node": "Filter Existing", "type": "main", "index": 0}],
                # error branch — silently end
                [{"node": "No Operation", "type": "main", "index": 0}],
            ]
        },
        "Filter Existing": {
            "main": [[{"node": "Create Interaction", "type": "main", "index": 0}]]
        },
    },
    "settings": {
        "executionOrder": "v1",
    },
}


# ── Main execution ──────────────────────────────────────────────────

def main():
    workflows = [
        ("Lookup Caller", lookup_caller_workflow, "lookup-caller.json"),
        ("Log Interaction", log_interaction_workflow, "log-interaction.json"),
        ("End-of-Call Report", eoc_workflow, "end-of-call-report.json"),
    ]

    created_ids = {}

    for name, wf_json, filename in workflows:
        print(f"\n{'='*50}")
        print(f"Creating workflow: {name}")
        result = create_workflow(wf_json)
        wf_id = result["id"]
        print(f"  Created with ID: {wf_id}")
        created_ids[name] = wf_id

        print(f"  Activating...")
        activate_workflow(wf_id)
        print(f"  Activated!")

        print(f"  Exporting...")
        export_workflow(wf_id, filename)

    print(f"\n{'='*50}")
    print("All workflows created and activated!")
    print("\nWorkflow IDs:")
    for name, wf_id in created_ids.items():
        print(f"  {name}: {wf_id}")

    print("\nWebhook URLs:")
    base = N8N_BASE_URL
    print(f"  Lookup Caller:      {base}/webhook/lookup-caller")
    print(f"  Log Interaction:    {base}/webhook/log-interaction")
    print(f"  End-of-Call Report: {base}/webhook/vapi-server")


if __name__ == "__main__":
    main()
