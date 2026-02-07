#!/usr/bin/env python3
import os
import io
import asyncio
import numpy as np
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
        print(f"🔊 Generando voz para: {text[:30]}...")
        response = client.audio.speech.create(
            model="tts-1",
            voice="onyx", 
            input=text
        )
        
        # Leemos el audio de OpenAI
        data, fs = sf.read(io.BytesIO(response.content))

        # EL TRUCO: El HAT WM8960 suele preferir 44100Hz o 48000Hz. 
        # OpenAI manda 24000Hz por defecto.
        # Si sounddevice falla con el ID: 1, probaremos sin especificar el ID 
        # pero forzando el mapeo a la tarjeta WM8960.
        
        print(f"🔈 Reproduciendo a {fs}Hz...")
        
        # Intentamos reproducir. Si falla el sample rate, el sistema operativo
        # debería re-muestrear si usamos el dispositivo por nombre o el ID correcto.
        sd.play(data, fs, device=1)
        sd.wait()
        
    except Exception as e:
        print(f"TTS ERROR: {e}")
        print("Intentando método de emergencia (aplay)...")
        # Si falla sounddevice, intentamos usar el comando del sistema
        try:
            with open("temp.mp3", "wb") as f:
                f.write(response.content)
            os.system("mpg123 -D hw:1,0 temp.mp3") 
        except:
            pass

def update_tts_settings(url):
    pass
