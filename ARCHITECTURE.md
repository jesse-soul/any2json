# any2json — Architecture

## Concept
Universal multimodal-to-JSON converter with token-budget control.
**Key insight:** `max_tokens` parameter controls detail level like a "zoom" dial.

## API Design

### POST /convert
```json
{
  "input": "https://example.com/video.mp4",  // URL, base64, or upload
  "type": "auto",                             // auto|image|video|audio|document
  "max_tokens": 500,                          // target output size
  "format": "flat",                           // flat|nested|progressive
  "expand": ["section_id"]                    // optional: get more detail on specific parts
}
```

### Response (flat, 500 tokens)
```json
{
  "type": "video",
  "duration_sec": 127,
  "summary": "Product demo showing new dashboard features",
  "scenes": [
    {"id": "s1", "time": "0:00-0:32", "label": "intro", "summary": "Host introduces topic"},
    {"id": "s2", "time": "0:32-1:45", "label": "demo", "summary": "Screen recording of dashboard"},
    {"id": "s3", "time": "1:45-2:07", "label": "outro", "summary": "Call to action"}
  ],
  "_expandable": ["s1", "s2", "s3"],
  "_tokens_used": 487
}
```

### Progressive Expansion
Request with `"expand": ["s2"]` returns detailed breakdown of scene 2:
- Frame-by-frame descriptions
- Transcribed dialogue
- UI elements detected
- Actions performed

## Token Budget Strategy

| max_tokens | Detail Level | Use Case |
|------------|--------------|----------|
| 100-200    | TL;DR        | Quick triage, search indexing |
| 500-1000   | Summary      | Context for chat, RAG |
| 2000-5000  | Detailed     | Analysis, documentation |
| 10000+     | Full         | Complete extraction |

## Modality Handlers

### Image
- Scene description
- Text extraction (OCR)
- Object/face detection
- Color palette, composition

### Video
- Scene segmentation
- Key frame extraction
- Audio transcription
- Speaker diarization

### Audio
- Transcription
- Speaker identification
- Sentiment/tone
- Music/sound detection

### Document (PDF/DOCX)
- Structure extraction
- Table parsing
- Image extraction
- Metadata

## Tech Stack
- **Backend:** Python FastAPI
- **Vision:** Claude/GPT-4V for descriptions
- **Video:** ffmpeg + scene detection
- **Audio:** Whisper
- **OCR:** Tesseract / Vision API
- **Deployment:** jesse.intelligency.pro (nginx + uvicorn)

## MVP Scope
1. Image support only
2. Single endpoint
3. max_tokens parameter
4. Basic landing page

---
*Draft by Jesse, 2026-02-02*
