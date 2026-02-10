"""
Audio processing module for any2json.
Uses OpenAI Whisper for transcription.
"""

import os
import tempfile
import subprocess
import json
from typing import Dict, Optional


def transcribe_audio(audio_path: str, max_tokens: int, language: Optional[str] = None) -> Dict:
    """
    Transcribe audio file using Whisper.
    
    Args:
        audio_path: Path to audio file
        max_tokens: Token budget for output (affects model choice)
        language: Optional language hint (e.g., "Russian", "English")
    
    Returns:
        Dict with transcription and metadata
    """
    
    # Choose Whisper model based on token budget
    # tiny: fast but less accurate (~1GB RAM)
    # small: good balance (~2GB RAM)
    # medium: better quality (~5GB RAM)
    if max_tokens <= 200:
        model = "tiny"
    elif max_tokens <= 1000:
        model = "small"
    else:
        model = "medium"
    
    # Create temp directory for output
    with tempfile.TemporaryDirectory() as tmpdir:
        output_format = "json"
        
        # Build whisper command
        cmd = [
            "whisper",
            audio_path,
            "--model", model,
            "--output_format", output_format,
            "--output_dir", tmpdir
        ]
        
        if language:
            cmd.extend(["--language", language])
        
        # Run Whisper
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode != 0:
                raise Exception(f"Whisper failed: {result.stderr}")
            
            # Read JSON output
            base_name = os.path.splitext(os.path.basename(audio_path))[0]
            json_file = os.path.join(tmpdir, f"{base_name}.json")
            
            with open(json_file, 'r') as f:
                whisper_output = json.load(f)
            
            # Extract transcript
            text = whisper_output.get("text", "").strip()
            segments = whisper_output.get("segments", [])
            
            # Build response based on token budget
            if max_tokens <= 200:
                # Minimal: just the text
                return {
                    "type": "audio",
                    "summary": text[:200] + "..." if len(text) > 200 else text,
                    "text": text,
                    "metadata": {
                        "model": model,
                        "language": whisper_output.get("language"),
                        "duration": segments[-1]["end"] if segments else None
                    },
                    "_expandable": ["segments"] if segments else [],
                    "_tokens_used": len(text.split()) * 1.3  # Rough estimate
                }
            
            elif max_tokens <= 1000:
                # Include basic segmentation
                simple_segments = [
                    {
                        "start": seg["start"],
                        "end": seg["end"],
                        "text": seg["text"].strip()
                    }
                    for seg in segments[:10]  # Limit to first 10 segments
                ]
                
                return {
                    "type": "audio",
                    "summary": f"Audio transcription ({len(segments)} segments, {whisper_output.get('language', 'unknown')} language)",
                    "text": text,
                    "segments": simple_segments,
                    "metadata": {
                        "model": model,
                        "language": whisper_output.get("language"),
                        "duration": segments[-1]["end"] if segments else None,
                        "total_segments": len(segments)
                    },
                    "_expandable": ["full_segments"] if len(segments) > 10 else [],
                    "_tokens_used": len(text.split()) * 1.5
                }
            
            else:
                # Full detail with all segments
                detailed_segments = [
                    {
                        "id": f"seg_{i}",
                        "start": seg["start"],
                        "end": seg["end"],
                        "text": seg["text"].strip(),
                        "confidence": seg.get("avg_logprob", 0)
                    }
                    for i, seg in enumerate(segments)
                ]
                
                return {
                    "type": "audio",
                    "summary": f"Full transcription with {len(segments)} time-aligned segments",
                    "text": text,
                    "segments": detailed_segments,
                    "metadata": {
                        "model": model,
                        "language": whisper_output.get("language"),
                        "duration": segments[-1]["end"] if segments else None,
                        "word_count": len(text.split())
                    },
                    "_expandable": [],
                    "_tokens_used": len(text.split()) * 2
                }
        
        except subprocess.TimeoutExpired:
            raise Exception("Audio transcription timed out (>5 minutes)")
        except Exception as e:
            raise Exception(f"Transcription error: {str(e)}")


def process_audio_url(url: str, max_tokens: int, language: Optional[str] = None) -> Dict:
    """Download and process audio from URL."""
    import httpx
    
    with tempfile.NamedTemporaryFile(suffix=".audio", delete=False) as tmp:
        try:
            # Download audio
            with httpx.Client(timeout=30.0) as client:
                response = client.get(url)
                response.raise_for_status()
                tmp.write(response.content)
                tmp.flush()
            
            # Transcribe
            result = transcribe_audio(tmp.name, max_tokens, language)
            return result
        
        finally:
            # Cleanup
            if os.path.exists(tmp.name):
                os.unlink(tmp.name)


def process_audio_base64(data: str, max_tokens: int, language: Optional[str] = None) -> Dict:
    """Process base64-encoded audio."""
    import base64
    
    # Handle data URL format
    if data.startswith("data:"):
        data = data.split(",", 1)[1]
    
    audio_bytes = base64.b64decode(data)
    
    with tempfile.NamedTemporaryFile(suffix=".audio", delete=False) as tmp:
        try:
            tmp.write(audio_bytes)
            tmp.flush()
            
            result = transcribe_audio(tmp.name, max_tokens, language)
            return result
        
        finally:
            if os.path.exists(tmp.name):
                os.unlink(tmp.name)
