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
    # Buscamos la clave en cualquier parte de la configuración
    api_key = CONFIG['TTS'].get('openai_api_key') or \
              CONFIG['LLM'].get('api_key') or \
              os.environ.get('OPENAI_API_KEY')
    if api_key:
        return OpenAI(api_key=api_key)
    return None

async def play_audio_chunks(text, tts_option=None, is_wakeword=False):
    if not text:
        return

    client = get_openai_client()
    if not client:
        print("TTS ERROR: No se encontró API Key para la voz.")
        return

    try:
        # 1. Generar el audio en la nube
        # Usamos la voz 'onyx' o 'echo' que son las más parecidas a TARS (masculinas y serias)
        response = client.audio.speech.create(
            model="tts-1",
            voice="onyx", 
            input=text
        )

        # 2. Leer los datos de audio
        data, fs = sf.read(io.BytesIO(response.content))

        # 3. Reproducir por el HAT WM8960 (ID: 1)
        # Forzamos el dispositivo 1 que es tu tarjeta Waveshare
        sd.play(data, fs, device=1)
        sd.wait() # Esperar a que termine de hablar

    except Exception as e:
        print(f"TTS ERROR: {e}")

def update_tts_settings(url):
    pass
