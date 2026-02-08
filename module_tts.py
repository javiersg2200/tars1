#!/usr/bin/env python3
import os
import subprocess
from openai import OpenAI
from modules.module_config import load_config
import modules.tars_status as status 

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
        # 1. SEMÁFORO ROJO (¡Cállate oído!)
        status.is_speaking = True 
        
        print(f"🔊 Generando voz...")
        
        # 2. SOLICITAMOS WAV DIRECTAMENTE (Más rápido)
        response = client.audio.speech.create(
            model="tts-1",
            voice="onyx",
            input=text,
            response_format="wav" # <--- ¡TRUCO DE VELOCIDAD!
        )
        
        wav_file = "speech_temp.wav"
        
        # Guardamos directo (sin conversión ffmpeg)
        with open(wav_file, "wb") as f:
            f.write(response.content)

        print(f"🔊 TARS HABLANDO...")
        
        # 3. REPRODUCIMOS
        subprocess.run(
            f"aplay -D default {wav_file} -q", 
            shell=True
        )

    except Exception as e:
        print(f"TTS ERROR: {e}")
        
    finally:
        # 4. SEMÁFORO VERDE (Oído, despierta)
        print("✅ Fin de frase. Reactivando oído...")
        status.is_speaking = False

def update_tts_settings(url): pass
