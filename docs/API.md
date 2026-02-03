# any2json API Documentation

## Base URL
```
https://api.any2json.ai
```

## Authentication

All API requests require an API key in the Authorization header:

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
  https://api.any2json.ai/convert
```

Get your API key by running:
```bash
curl -sSL https://any2json.ai/install | bash
```

---

## Endpoints

### POST /convert

Convert any media to structured JSON.

**Request:**
```json
{
  "input": "https://example.com/image.jpg",
  "max_tokens": 500,
  "type": "auto",
  "expand": null
}
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `input` | string | required | URL, base64, or file path |
| `max_tokens` | int | 500 | Target output size (100-10000) |
| `type` | string | "auto" | `auto`, `image`, `video`, `audio`, `document` |
| `expand` | array | null | IDs to expand for more detail |

**Response:**
```json
{
  "type": "image",
  "summary": "Product photo showing a laptop on a wooden desk",
  "elements": [
    {"id": "e1", "type": "object", "label": "laptop", "position": "center"},
    {"id": "e2", "type": "object", "label": "desk", "position": "background"},
    {"id": "e3", "type": "text", "content": "MacBook Pro", "position": "top-left"}
  ],
  "metadata": {
    "dimensions": "1920x1080",
    "format": "jpeg"
  },
  "_expandable": ["e1", "e2", "e3"],
  "_tokens_used": 127
}
```

---

### Progressive Expansion

Get more detail on specific elements:

```json
{
  "input": "https://example.com/image.jpg",
  "max_tokens": 2000,
  "expand": ["e1"]
}
```

Response includes detailed breakdown of element `e1`.

---

### GET /account/balance

Check your credit balance.

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
  https://api.any2json.ai/account/balance
```

**Response:**
```json
{
  "balance": 4.50,
  "used": 0.50,
  "tier": "free"
}
```

---

### POST /payments/get-address

Get a unique payment address to add credits.

```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"network": "trc20"}' \
  https://api.any2json.ai/payments/get-address
```

**Networks:** `trc20`, `erc20`, `dai`, `xdai`

**Response:**
```json
{
  "address": "TXyz123...",
  "network": "trc20",
  "network_name": "USDT (TRC-20)"
}
```

---

## Token Budget Guide

| max_tokens | Detail Level | Use Case |
|------------|--------------|----------|
| 100 | TL;DR | Quick triage, search indexing |
| 500 | Summary | Chat context, RAG |
| 2000 | Detailed | Analysis, documentation |
| 5000+ | Full | Complete extraction |

---

## Examples

### Image Analysis
```bash
curl -X POST https://api.any2json.ai/convert \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "input": "https://example.com/screenshot.png",
    "max_tokens": 500
  }'
```

### Video Summary
```bash
curl -X POST https://api.any2json.ai/convert \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "input": "https://youtube.com/watch?v=VIDEO_ID",
    "max_tokens": 1000,
    "type": "video"
  }'
```

### Document Extraction
```bash
curl -X POST https://api.any2json.ai/convert \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "input": "https://example.com/report.pdf",
    "max_tokens": 2000,
    "type": "document"
  }'
```

---

## Error Codes

| Code | Description |
|------|-------------|
| 400 | Bad request (invalid input) |
| 401 | Unauthorized (invalid/missing API key) |
| 402 | Insufficient credits |
| 429 | Rate limited |
| 500 | Server error |

---

## Rate Limits

| Tier | Requests/min | Requests/day |
|------|--------------|--------------|
| Free | 10 | 100 |
| Paid | 60 | 10,000 |

---

## SDKs

### Python
```python
from any2json import Any2JSON

client = Any2JSON(api_key="YOUR_KEY")
result = client.convert("https://example.com/image.jpg", max_tokens=500)
print(result.summary)
```

### JavaScript
```javascript
import { Any2JSON } from 'any2json';

const client = new Any2JSON('YOUR_KEY');
const result = await client.convert('https://example.com/image.jpg', { maxTokens: 500 });
console.log(result.summary);
```

---

## Support

- GitHub: https://github.com/jesse-soul/any2json
- Email: jesse@intelligency.pro
