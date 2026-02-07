#!/usr/bin/env python3
"""
module_tts.py - Versión Lite (Safe Mode) para Raspberry Pi 4
Eliminadas todas las dependencias locales pesadas (AllTalk, Piper, Silero)
para evitar el error 'Illegal Instruction'. Solo usa OpenAI.
"""

import os
import sys
import asyncio
import sounddevice as sd
import soundfile as sf
import io
import requests
from modules.module_messageQue import queue_message
from modules.module_config import load_config

# Intentamos importar OpenAI, si falla no pasa nada
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

CONFIG = load_config()

# === Funciones Helper ===

def update_tts_settings(ttsurl):
    """
    Función dummy para que app.py no falle al llamar aquí.
    En el modo Lite no configuramos servidores locales.
    """
    queue_message(f"INFO: TTS Settings update ignorado en modo Lite.")

async def generate_tts_audio(text, ttsoption, is_wakeword=False):
    """
    Generador dummy para mantener compatibilidad, pero no se usa en la lógica principal simplificada.
    """
    yield None

async def play_audio_chunks(text, config_or_option, is_wakeword=False):
    """
    Función principal de habla.
    Simplificada para usar SOLO OpenAI API o fallar silenciosamente.
    """
    if not text:
        return

    text = text.strip()
    # queue_message(f"TTS: Procesando '{text[:15]}...'")

    # Recuperar API Key
    api_key = CONFIG['TTS'].get('openai_api_key', os.environ.get("OPENAI_API_KEY"))
    
    # Si tenemos OpenAI y Key, lo usamos (Calidad Alta)
    if OpenAI and api_key and "sk-" in api_key:
        try:
            client = OpenAI(api_key=api_key)
            response = client.audio.speech.create(
                model="tts-1",
                voice="alloy", # Puedes cambiar a: alloy, echo, fable, onyx, nova, shimmer
                input=text
            )
            
            # Convertir bytes a audio
            data, fs = sf.read(io.BytesIO(response.content))
            
            # Reproducir
            sd.play(data, fs)
            sd.wait()
            return

        except Exception as e:
            queue_message(f"ERROR OpenAI TTS: {e}")
    
    # Fallback si no hay internet o clave (Opcional: usar espeak del sistema)
    # queue_message(f"TTS: No se pudo generar audio (Falta OpenAI Key o Error). Texto: {text}")
    # Descomenta la siguiente linea si tienes 'espeak' instalado en linux para voz de robot:
    # os.system(f"espeak '{text}' 2>/dev/null")

# Funciones extra para evitar errores de importación
def stop(): pass
