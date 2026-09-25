# Webhook integrations

openwahi talks to external systems through two independent webhook mechanisms:

| Mechanism | Direction | Triggered by | Configured in |
|---|---|---|---|
| **Agent webhook tools** | openwahi → your endpoint | The LangGraph agent decides to call a tool during a conversation | AI assistant settings in the web app, or the `/webhook-tools` API |
| **Developer event webhooks** | openwahi → your endpoint | An incoming WhatsApp message (`message.received`) | Developer portal → Webhook tab, or the `/developer` API |

Any HTTP endpoint works as a receiver: your own service, or an automation platform such as Make, n8n, Zapier or Pipedream.

---

## 1. Agent webhook tools

A webhook tool gives the agent an action it can take: create a ticket, look up an order, book a meeting, and so on. openwahi turns each enabled tool into a LangChain tool. The model sees the tool `name` and `description` and fills in arguments that match `input_schema`.

### Tool definition

| Field | Required | Notes |
|---|---|---|
| `name` | yes | Tool name shown to the model. Use `snake_case`, e.g. `create_support_ticket`. |
| `description` | yes | Tell the model **when** to call the tool and what it does. This is the most important field for reliable tool use. |
| `webhook_url` | yes | Endpoint that is called. |
| `method` | no | `GET`, `POST` (default), `PUT`, `PATCH` or `DELETE`. |
| `input_schema` | yes | JSON Schema (`properties` + `required`) describing the arguments. |
| `headers` | no | Static headers sent on every call. |
| `auth_type` / `auth_value` | no | `bearer` sends `Authorization: Bearer <auth_value>`; `api_key` sends `X-API-Key: <auth_value>`. |
| `timeout_seconds` | no | 1–300, default 30. |
| `is_enabled` | no | Disabled tools are not offered to the agent. |

Create a tool through the API (authenticated with a Firebase ID token):

```bash
curl -X POST http://localhost:8000/webhook-tools \
  -H "Authorization: Bearer $FIREBASE_ID_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "create_support_ticket",
    "description": "Create a support ticket when the customer reports a problem that cannot be solved from the knowledge base. Ask for their name, email and a short summary first.",
    "webhook_url": "https://hooks.example.com/support-ticket",
    "method": "POST",
    "input_schema": {
      "type": "object",
      "properties": {
        "name":    {"type": "string", "description": "Customer full name"},
        "email":   {"type": "string", "description": "Customer email"},
        "phone":   {"type": "string", "description": "Customer WhatsApp number"},
        "summary": {"type": "string", "description": "One-paragraph description of the problem"}
      },
      "required": ["name", "email", "summary"]
    },
    "auth_type": "bearer",
    "auth_value": "sk_example_replace_me"
  }'
```

### What your endpoint receives

The request body is the JSON object of validated tool arguments, with `Content-Type: application/json` plus any configured headers:

```http
POST /support-ticket HTTP/1.1
Host: hooks.example.com
Authorization: Bearer sk_example_replace_me
Content-Type: application/json

{"name": "Ada Lovelace", "email": "ada@example.com", "phone": "15551234567", "summary": "The invoice PDF does not download."}
```

### What your endpoint should return

Return a `2xx` status with a JSON object. If it contains a `message` field, that text is passed back to the agent as the tool result; otherwise the agent receives the other fields as `key: value` details. Keep `message` short and factual so the agent can relay it to the customer.

```json
{
  "message": "Ticket #4821 created. Our team will reply by email within one business day.",
  "ticket_id": 4821
}
```

Any non-`2xx` status or network error is reported to the agent as a failed action.

### Minimal receiver (Python)

```python
from fastapi import FastAPI, Header, HTTPException

app = FastAPI()
EXPECTED_TOKEN = "sk_example_replace_me"


@app.post("/support-ticket")
async def create_ticket(payload: dict, authorization: str = Header(default="")):
    if authorization != f"Bearer {EXPECTED_TOKEN}":
        raise HTTPException(status_code=401, detail="invalid token")
    ticket_id = save_ticket(payload)  # your logic
    return {"message": f"Ticket #{ticket_id} created.", "ticket_id": ticket_id}
```

### Recipe: Make

1. Create a scenario and add **Webhooks → Custom webhook**. Copy its URL into `webhook_url`.
2. Add a filter right after the trigger that checks the `Authorization` header equals `Bearer <your token>`.
3. Add the actions you need (help desk, spreadsheet row, email, chat notification, …), mapping `{{name}}`, `{{email}}`, `{{summary}}` from the trigger.
4. Finish with **Webhooks → Webhook response**, status `200`, body:
   ```json
   {"message": "Ticket created. We will contact you by email shortly."}
   ```

### Recipe: n8n

Minimal workflow: **Webhook** (method `POST`, path `support-ticket`, response mode *Using "Respond to Webhook" node*, header auth credential) → your action nodes → **Respond to Webhook**:

```json
{
  "name": "openwahi - support ticket",
  "nodes": [
    {
      "name": "Webhook",
      "type": "n8n-nodes-base.webhook",
      "parameters": {
        "httpMethod": "POST",
        "path": "support-ticket",
        "authentication": "headerAuth",
        "responseMode": "responseNode"
      },
      "position": [250, 300]
    },
    {
      "name": "Respond to Webhook",
      "type": "n8n-nodes-base.respondToWebhook",
      "parameters": {
        "respondWith": "json",
        "responseBody": "={\"message\": \"Ticket created for {{$json.body.email}}.\"}"
      },
      "position": [650, 300]
    }
  ],
  "connections": {
    "Webhook": { "main": [[{ "node": "Respond to Webhook", "type": "main", "index": 0 }]] }
  }
}
```

Insert your own nodes (database insert, help desk API, chat notification, …) between the two.

### Recipe: Zapier

1. Trigger: **Webhooks by Zapier → Catch Hook**; use its URL as `webhook_url`.
2. Add the actions you need, mapping the caught fields.

Zapier's Catch Hook always answers with its own acknowledgement body, so the agent only learns that the call succeeded. Use Make, n8n or your own endpoint when the reply must carry information back to the conversation.

---

## 2. Developer event webhooks

When a WhatsApp message arrives on one of your devices, openwahi POSTs an event to the webhook URL configured in the developer portal:

```json
{
  "event": "message.received",
  "timestamp": "2026-01-15T10:30:00+00:00",
  "data": {
    "message_id": "uuid",
    "whatsapp_message_id": "3EB0C767D26A1D5B5A1F",
    "device_id": "uuid",
    "from_phone": "15551234567",
    "to_phone": "15557654321",
    "body": "Hello!",
    "message_type": "text",
    "timestamp": "2026-01-15T10:30:00+00:00"
  }
}
```

The portal's **Test** button sends a sample event to the same URL.

### Signature verification

If you configure a secret, each request carries:

```
X-Webhook-Signature: sha256=<hex HMAC-SHA256>
```

The HMAC is computed over the exact raw request body. Verify it against the bytes you received, before parsing JSON:

```python
import hashlib
import hmac


def verify(raw_body: bytes, signature_header: str, secret: str) -> bool:
    expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature_header)
```

Always use a constant-time comparison and reject requests with a missing or invalid signature.

---

## Testing

- [webhook.site](https://webhook.site) or [RequestBin](https://requestbin.com) show exactly what openwahi sends.
- Expose a local receiver with a tunnel (e.g. `ngrok http 9000`) and use the public URL as `webhook_url`.
- Call your receiver directly to check the response format:

```bash
curl -X POST https://hooks.example.com/support-ticket \
  -H "Authorization: Bearer $HOOK_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Test User", "email": "test@example.com", "summary": "This is a test"}'
```

Expected response:

```json
{"message": "Ticket #1 created.", "ticket_id": 1}
```

## References

- [Make webhooks](https://www.make.com/en/help/tools/webhooks)
- [n8n Webhook node](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.webhook/)
- [Zapier webhooks](https://zapier.com/apps/webhook/integrations)
