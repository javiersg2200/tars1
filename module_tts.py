#!/usr/bin/env python3
import os
import io
import asyncio
import sounddevice as sd
import soundfile as sf
from openai import OpenAI
from modules.module_config import load_config

CONFIG = load_config()

def get_openai_client():
    tts_conf = CONFIG['TTS']
    api_key = getattr(tts_conf, 'openai_api_key', None) or os.environ.get("OPENAI_API_KEY")
    if api_key:
        return OpenAI(api_key=api_key)
    return None

async def play_audio_chunks(text, tts_option=None, is_wakeword=False):
    if not text: return
    client = get_openai_client()
    if not client: return

    try:
        response = client.audio.speech.create(
            model="tts-1",
            voice="onyx", 
            input=text
        )
        data, fs = sf.read(io.BytesIO(response.content))
        # Forzamos salida por el dispositivo 1 (HAT WM8960)
        sd.play(data, fs, device=1)
        sd.wait()
    except Exception as e:
        print(f"TTS ERROR: {e}")

def update_tts_settings(url): pass
