# Audio Support

## Overview

any2json now supports audio transcription using OpenAI Whisper. The system automatically chooses the appropriate Whisper model based on your `max_tokens` budget.

## Features

- **Automatic model selection**: tiny/small/medium based on token budget
- **Time-aligned segments**: Get timestamped transcription segments
- **Language detection**: Automatic language detection or specify manually
- **Progressive detail**: Control output verbosity with `max_tokens`

## Token Budget → Model Mapping

| max_tokens | Whisper Model | Detail Level |
|------------|---------------|--------------|
| ≤ 200 | tiny | Text only, minimal summary |
| ≤ 1000 | small | Text + first 10 segments |
| > 1000 | medium | Full transcript with all segments |

## API Usage

### Basic Request

```json
POST /convert
{
  "input": "https://example.com/audio.mp3",
  "type": "audio",
  "max_tokens": 500
}
```

### With Language Hint

```json
{
  "input": "https://example.com/audio.mp3",
  "type": "audio",
  "max_tokens": 1000,
  "language": "Russian"
}
```

### Response Format

#### Minimal (≤ 200 tokens)

```json
{
  "type": "audio",
  "summary": "Brief text preview...",
  "text": "Full transcription text",
  "metadata": {
    "model": "tiny",
    "language": "en",
    "duration": 120.5
  },
  "_expandable": ["segments"],
  "_tokens_used": 85
}
```

#### Medium (≤ 1000 tokens)

```json
{
  "type": "audio",
  "summary": "Audio transcription (45 segments, Russian language)",
  "text": "Full transcription text",
  "segments": [
    {
      "start": 0.0,
      "end": 3.5,
      "text": "Hello, this is a test"
    },
    ...
  ],
  "metadata": {
    "model": "small",
    "language": "ru",
    "duration": 180.0,
    "total_segments": 45
  },
  "_expandable": ["full_segments"],
  "_tokens_used": 450
}
```

#### Full Detail (> 1000 tokens)

```json
{
  "type": "audio",
  "summary": "Full transcription with 45 time-aligned segments",
  "text": "Complete transcription...",
  "segments": [
    {
      "id": "seg_0",
      "start": 0.0,
      "end": 3.5,
      "text": "Hello, this is a test",
      "confidence": -0.15
    },
    ...
  ],
  "metadata": {
    "model": "medium",
    "language": "en",
    "duration": 180.0,
    "word_count": 350
  },
  "_expandable": [],
  "_tokens_used": 1200
}
```

## Supported Formats

- MP3
- WAV
- M4A
- OGG
- FLAC
- AAC

## Input Methods

1. **URL**: `"input": "https://example.com/audio.mp3"`
2. **Base64**: `"input": "data:audio/mp3;base64,//uQx..."`

## Performance Notes

- **Tiny model**: ~instant load, ~30s processing for 1min audio
- **Small model**: ~80s load on CPU, better accuracy
- **Medium model**: ~2min load on CPU, highest quality
- **Timeout**: 5 minutes max per request

## Backend Implementation

See `backend/audio.py` for implementation details:
- `transcribe_audio()`: Core Whisper transcription
- `process_audio_url()`: Download from URL and process
- `process_audio_base64()`: Decode base64 and process

## Testing

Run `python3 test_audio.py` to verify the audio backend is working.

## Future Improvements

- [ ] Speaker diarization (identify different speakers)
- [ ] Emotion/sentiment detection
- [ ] Audio quality metrics
- [ ] Support for video audio extraction
