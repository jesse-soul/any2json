#!/usr/bin/env python3
"""
Quick test for audio processing functionality.
"""

import sys
import tempfile
import subprocess

# Test 1: Check if Whisper is available
print("Test 1: Checking Whisper availability...")
try:
    result = subprocess.run(["whisper", "--help"], capture_output=True, timeout=5)
    if result.returncode == 0:
        print("✅ Whisper is installed and accessible")
    else:
        print("❌ Whisper command failed")
        sys.exit(1)
except FileNotFoundError:
    print("❌ Whisper not found in PATH")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error checking Whisper: {e}")
    sys.exit(1)

# Test 2: Import audio backend
print("\nTest 2: Importing audio backend...")
try:
    from backend.audio import transcribe_audio, process_audio_url, process_audio_base64
    print("✅ Audio backend imports successfully")
except ImportError as e:
    print(f"❌ Failed to import audio backend: {e}")
    sys.exit(1)

# Test 3: Check app.py imports
print("\nTest 3: Checking app.py imports...")
try:
    import app
    print("✅ app.py imports successfully")
except ImportError as e:
    print(f"❌ Failed to import app.py: {e}")
    sys.exit(1)

print("\n✅ All basic checks passed!")
print("\nAudio support is ready. To test with real audio:")
print("1. Start the server: uvicorn app:app --reload")
print("2. POST to /convert with:")
print('   {"input": "https://example.com/audio.mp3", "type": "audio", "max_tokens": 500}')
