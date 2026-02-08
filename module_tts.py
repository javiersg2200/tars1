#!/usr/bin/env python3
import os
import io
import asyncio
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
        print(f"🔊 Generando voz para: {text[:30]}...")
        response = client.audio.speech.create(
            model="tts-1",
            voice="onyx", 
            input=text
        )
        
        # 1. Guardar MP3
        with open("temp.mp3", "wb") as f:
            f.write(response.content)

        # 2. Convertir a WAV 44100Hz (estándar del HAT)
        # Usamos -loglevel panic para que ffmpeg no ensucie la pantalla
        os.system("ffmpeg -y -i temp.mp3 -ar 44100 -ac 2 -loglevel panic temp.wav")

        # 3. Reproducir forzando la tarjeta 3 (hw:3,0)
        print("🔈 Reproduciendo en HAT (Card 3)...")
        os.system("aplay -D hw:3,0 temp.wav > /dev/null 2>&1")
        
    except Exception as e:
        print(f"TTS ERROR: {e}")

def update_tts_settings(url):
    pass
