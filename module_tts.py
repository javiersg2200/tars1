#!/usr/bin/env python3
import os
import subprocess
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
        print(f"🔊 Generando voz para: '{text[:20]}...'")
        
        response = client.audio.speech.create(
            model="tts-1",
            voice="onyx",
            input=text
        )
        
        mp3_file = "speech_temp.mp3"
        wav_file = "speech_temp.wav"
        
        with open(mp3_file, "wb") as f:
            f.write(response.content)

        # Convertir a WAV estándar
        subprocess.run(
            f"ffmpeg -y -i {mp3_file} -ar 44100 -ac 2 -f wav {wav_file} -loglevel quiet", 
            shell=True
        )

        # --- CAMBIO CLAVE: Usar dispositivo 'default' ---
        print(f"🔊 Reproduciendo en DEFAULT...")
        subprocess.run(
            f"aplay -D default {wav_file} -q", 
            shell=True
        )

    except Exception as e:
        print(f"TTS ERROR: {e}")

def update_tts_settings(url): pass
