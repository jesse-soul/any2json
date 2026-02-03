# any2json Examples

Real-world examples of any2json output for different media types.

## Image → JSON

### Input
Product photo (e-commerce)

### Output (max_tokens: 500)
```json
{
  "type": "image",
  "summary": "E-commerce product photo of white wireless earbuds in charging case",
  "elements": [
    {
      "id": "product",
      "type": "object",
      "label": "wireless earbuds",
      "attributes": {
        "color": "white",
        "brand_visible": false,
        "condition": "new"
      }
    },
    {
      "id": "case",
      "type": "object", 
      "label": "charging case",
      "attributes": {
        "color": "white",
        "state": "open"
      }
    },
    {
      "id": "bg",
      "type": "background",
      "style": "gradient",
      "colors": ["#f5f5f5", "#e0e0e0"]
    }
  ],
  "composition": {
    "style": "product_shot",
    "angle": "45_degree",
    "lighting": "soft_studio"
  },
  "_expandable": ["product", "case"],
  "_tokens_used": 156
}
```

---

## Video → JSON

### Input
YouTube tutorial (5 min)

### Output (max_tokens: 1000)
```json
{
  "type": "video",
  "duration_sec": 312,
  "summary": "Python tutorial explaining list comprehensions with 3 practical examples",
  "scenes": [
    {
      "id": "s1",
      "time": "0:00-0:45",
      "type": "intro",
      "summary": "Host introduces topic, shows code editor"
    },
    {
      "id": "s2", 
      "time": "0:45-2:30",
      "type": "tutorial",
      "summary": "Basic list comprehension syntax explained",
      "code_shown": true
    },
    {
      "id": "s3",
      "time": "2:30-4:15",
      "type": "examples",
      "summary": "Three practical examples demonstrated"
    },
    {
      "id": "s4",
      "time": "4:15-5:12",
      "type": "outro",
      "summary": "Recap and call to subscribe"
    }
  ],
  "transcript_summary": "Covers basic syntax [x for x in list], filtering with conditions, and nested comprehensions",
  "key_topics": ["list comprehension", "python", "iteration", "filtering"],
  "_expandable": ["s1", "s2", "s3", "s4"],
  "_tokens_used": 287
}
```

---

## Document → JSON

### Input
PDF invoice

### Output (max_tokens: 500)
```json
{
  "type": "document",
  "doc_type": "invoice",
  "pages": 1,
  "summary": "Invoice #INV-2024-0142 from Acme Corp for $1,250.00",
  "extracted": {
    "invoice_number": "INV-2024-0142",
    "date": "2024-01-15",
    "due_date": "2024-02-15",
    "vendor": {
      "name": "Acme Corp",
      "address": "123 Business St, NY 10001"
    },
    "customer": {
      "name": "John Smith",
      "email": "john@example.com"
    },
    "line_items": [
      {"description": "Consulting services", "qty": 10, "unit": "hours", "amount": 1000.00},
      {"description": "Software license", "qty": 1, "unit": "item", "amount": 250.00}
    ],
    "subtotal": 1250.00,
    "tax": 0,
    "total": 1250.00,
    "currency": "USD"
  },
  "_tokens_used": 198
}
```

---

## Audio → JSON

### Input
Podcast episode (30 min)

### Output (max_tokens: 800)
```json
{
  "type": "audio",
  "duration_sec": 1847,
  "summary": "Interview podcast discussing AI trends in 2024 with tech investor",
  "speakers": [
    {"id": "host", "name": "Unknown", "role": "host"},
    {"id": "guest", "name": "Unknown", "role": "guest"}
  ],
  "segments": [
    {
      "id": "seg1",
      "time": "0:00-3:20",
      "speaker": "host",
      "summary": "Introduction and guest background"
    },
    {
      "id": "seg2",
      "time": "3:20-15:40",
      "speakers": ["host", "guest"],
      "summary": "Discussion of LLM market and OpenAI vs open source"
    },
    {
      "id": "seg3",
      "time": "15:40-25:30",
      "speakers": ["host", "guest"],
      "summary": "Predictions for AI regulation and startup opportunities"
    },
    {
      "id": "seg4",
      "time": "25:30-30:47",
      "speaker": "host",
      "summary": "Closing thoughts and sponsor message"
    }
  ],
  "key_topics": ["AI", "LLM", "investing", "regulation", "startups"],
  "sentiment": "optimistic",
  "_expandable": ["seg1", "seg2", "seg3", "seg4"],
  "_tokens_used": 312
}
```

---

## Social Media → JSON

### Input
Twitter/X thread URL

### Output (max_tokens: 500)
```json
{
  "type": "social",
  "platform": "twitter",
  "content_type": "thread",
  "summary": "Thread explaining how to build a SaaS in 30 days (12 tweets)",
  "author": {
    "handle": "@example",
    "followers": "45.2K"
  },
  "thread": [
    {"position": 1, "summary": "Announcing 30-day SaaS challenge"},
    {"position": 2, "summary": "Day 1-7: Idea validation and landing page"},
    {"position": 3, "summary": "Day 8-14: MVP development"},
    {"position": 4, "summary": "Day 15-21: Beta users and feedback"},
    {"position": 5, "summary": "Day 22-30: Launch and marketing"}
  ],
  "engagement": {
    "likes": 2341,
    "retweets": 567,
    "replies": 89
  },
  "key_takeaways": [
    "Start with problem validation",
    "Ship fast, iterate faster",
    "Build in public for accountability"
  ],
  "_tokens_used": 203
}
```

---

## Using Expansion

### First call (overview)
```bash
curl -X POST https://api.any2json.ai/convert \
  -d '{"input": "video.mp4", "max_tokens": 200}'
```

### Second call (expand specific scene)
```bash
curl -X POST https://api.any2json.ai/convert \
  -d '{"input": "video.mp4", "max_tokens": 1000, "expand": ["s2"]}'
```

Returns detailed frame-by-frame for scene s2 only.
