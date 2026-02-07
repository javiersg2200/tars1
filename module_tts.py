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
        
        # 1. Guardar temporalmente el MP3 de OpenAI
        with open("temp.mp3", "wb") as f:
            f.write(response.content)

        # 2. Convertirlo a WAV de 44100Hz (frecuencia que ama el HAT)
        # Usamos ffmpeg para asegurar que el formato sea perfecto
        os.system("ffmpeg -y -i temp.mp3 -ar 44100 -ac 2 temp.wav > /dev/null 2>&1")

        # 3. Reproducir usando aplay (el estándar más bajo nivel de Linux)
        # hw:1,0 es tu HAT WM8960
        print("🔈 Reproduciendo por el HAT...")
        os.system("aplay -D hw:1,0 temp.wav > /dev/null 2>&1")
        
    except Exception as e:
        print(f"TTS ERROR: {e}")

def update_tts_settings(url):
    pass
