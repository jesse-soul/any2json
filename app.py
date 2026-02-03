"""
any2json — Multimodal to JSON converter
MVP: Image support with token budget control
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, List
import base64
import httpx
import os

app = FastAPI(
    title="any2json",
    description="Convert any media to context-efficient JSON",
    version="0.1.0"
)

# --- Models ---

class ConvertRequest(BaseModel):
    input: str  # URL or base64
    type: str = "auto"  # auto|image|video|audio|document
    max_tokens: int = 500
    format: str = "flat"  # flat|nested|progressive
    expand: Optional[List[str]] = None


class ConvertResponse(BaseModel):
    type: str
    summary: str
    details: dict
    _expandable: List[str] = []
    _tokens_used: int


# --- Token Budget Prompts ---

def get_prompt_for_budget(max_tokens: int, media_type: str) -> str:
    """Generate prompt based on token budget."""
    
    if max_tokens <= 200:
        detail = "极简：1-2 sentences, key facts only"
    elif max_tokens <= 500:
        detail = "summary: main elements, structure, key text"
    elif max_tokens <= 2000:
        detail = "detailed: all visible elements, full text, relationships"
    else:
        detail = "exhaustive: every detail, spatial relationships, colors, fonts"
    
    return f"""Analyze this {media_type} and return JSON.
Detail level: {detail}
Target: ~{max_tokens} tokens output.

Return valid JSON with:
- "summary": brief description
- "elements": array of detected items (id, type, content)
- "text": any text found (if applicable)
- "metadata": dimensions, colors, etc.

Be concise but complete within the token budget."""


# --- Handlers ---

async def process_image(image_data: str, max_tokens: int) -> dict:
    """Process image with vision model."""
    
    # For MVP, return mock structure
    # TODO: Integrate Claude/GPT-4V
    
    return {
        "type": "image",
        "summary": "Image analysis placeholder - integrate vision API",
        "elements": [
            {"id": "e1", "type": "placeholder", "content": "Vision API integration needed"}
        ],
        "text": None,
        "metadata": {
            "max_tokens_requested": max_tokens
        },
        "_expandable": ["e1"],
        "_tokens_used": 45
    }


# --- Routes ---

@app.get("/", response_class=HTMLResponse)
async def landing():
    """Landing page."""
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>any2json — Media to JSON</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0d1117;
            color: #c9d1d9;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 4rem 2rem;
        }
        .container { max-width: 800px; width: 100%; }
        h1 {
            font-size: 3rem;
            background: linear-gradient(135deg, #58a6ff, #f78166);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 1rem;
        }
        .tagline {
            font-size: 1.25rem;
            color: #8b949e;
            margin-bottom: 3rem;
        }
        .feature {
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 8px;
            padding: 1.5rem;
            margin-bottom: 1rem;
        }
        .feature h3 { color: #58a6ff; margin-bottom: 0.5rem; }
        code {
            background: #0d1117;
            padding: 0.2rem 0.5rem;
            border-radius: 4px;
            font-size: 0.9rem;
        }
        pre {
            background: #0d1117;
            padding: 1rem;
            border-radius: 8px;
            overflow-x: auto;
            margin-top: 1rem;
        }
        .endpoint {
            background: #238636;
            color: white;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-weight: bold;
            font-size: 0.8rem;
        }
        .coming-soon {
            opacity: 0.5;
            border-style: dashed;
        }
        footer {
            margin-top: 3rem;
            color: #8b949e;
            font-size: 0.9rem;
        }
        a { color: #58a6ff; }
    </style>
</head>
<body>
    <div class="container">
        <h1>any2json</h1>
        <p class="tagline">Convert any media to context-efficient JSON.<br>Control detail with <code>max_tokens</code>.</p>
        
        <div class="feature">
            <h3>🎯 Token Budget Control</h3>
            <p>Set <code>max_tokens: 100</code> for TL;DR, or <code>max_tokens: 5000</code> for full extraction.</p>
        </div>
        
        <div class="feature">
            <h3>🔍 Progressive Expansion</h3>
            <p>Get summary first, then <code>expand: ["section_id"]</code> for details on specific parts.</p>
        </div>
        
        <div class="feature">
            <h3><span class="endpoint">POST</span> /convert</h3>
            <pre>{
  "input": "https://example.com/image.jpg",
  "max_tokens": 500,
  "expand": null
}</pre>
        </div>
        
        <div class="feature">
            <h3>📷 Supported Formats</h3>
            <p>Images (JPG, PNG, WebP) • <span style="opacity:0.5">Video, Audio, Documents — coming soon</span></p>
        </div>
        
        <div class="feature coming-soon">
            <h3>🚧 API Docs</h3>
            <p>Interactive docs at <a href="/docs">/docs</a></p>
        </div>
        
        <footer>
            Built by <a href="https://jesse.intelligency.pro">Jesse</a> @ <a href="https://intelligency.space">Intelligency</a>
        </footer>
    </div>
</body>
</html>
"""


@app.post("/convert")
async def convert(request: ConvertRequest):
    """Convert media to JSON."""
    
    if request.type == "auto":
        # TODO: Auto-detect type from input
        request.type = "image"
    
    if request.type == "image":
        result = await process_image(request.input, request.max_tokens)
        return JSONResponse(result)
    
    raise HTTPException(
        status_code=400,
        detail=f"Type '{request.type}' not yet supported. MVP supports: image"
    )


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
