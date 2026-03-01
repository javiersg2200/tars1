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
        # 1. SEMÁFORO ROJO (Apagamos el oído)
        status.is_speaking = True 
        
        print(f"🔊 Generando voz...")
        
        # 2. Pedimos el WAV a OpenAI
        response = client.audio.speech.create(
            model="tts-1",
            voice="onyx",
            input=text,
            response_format="wav" 
        )
        
        raw_file = "speech_raw.wav"
        ready_file = "speech_ready.wav"
        
        with open(raw_file, "wb") as f:
            f.write(response.content)

        # 3. CONVERSIÓN CRÍTICA: Forzamos 44100Hz y 2 Canales
        subprocess.run(
            f"ffmpeg -y -i {raw_file} -ar 44100 -ac 2 {ready_file} -loglevel quiet", 
            shell=True
        )

        print(f"🔊 TARS HABLANDO...")
        
        # 4. Reproducimos
        subprocess.run(
            f"aplay -D default {ready_file} -q", 
            shell=True
        )

    except Exception as e:
        print(f"TTS ERROR: {e}")
        
    finally:
        # 5. SEMÁFORO VERDE (Oído, despierta)
        print("✅ Fin de frase.")
        status.is_speaking = False

# --- ESTA ES LA FUNCIÓN QUE FALTABA ---
def update_tts_settings(*args, **kwargs): 
    pass
