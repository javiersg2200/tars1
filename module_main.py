#!/usr/bin/env python3
"""
module_main.py - TARS Mirror Edition (Safe Mode)
Lógica central limpia y formateada correctamente.
"""
import os
import threading
import json
import re
import time
import asyncio
from modules.module_config import load_config
from modules.module_messageQue import queue_message

# Importamos versiones seguras (si existen)
try:
    from modules.module_llm import process_completion
except ImportError:
    process_completion = lambda x: "Error: LLM no encontrado"

try:
    from modules.module_tts import play_audio_chunks
except ImportError:
    async def play_audio_chunks(*args, **kwargs): pass

CONFIG = load_config()

# Variables Globales
ui_manager = None
character_manager = None
memory_manager = None
stt_manager = None
shutdown_event = None
battery_module = None

def initialize_managers(mem_mgr, char_mgr, stt_mgr, ui_mgr, shutdown_evt, batt_mod):
    global memory_manager, character_manager, stt_manager, ui_manager, shutdown_event, battery_module
    memory_manager = mem_mgr
    character_manager = char_mgr
    stt_manager = stt_mgr
    ui_manager = ui_mgr
    shutdown_event = shutdown_evt
    battery_module = batt_mod
    queue_message("SYSTEM: Managers initialized (Safe Mode).")

def wake_word_callback(wake_response="Yes?"):
    """Respuesta inicial al detectar la palabra clave"""
    if ui_manager:
        ui_manager.deactivate_screensaver()
        ui_manager.update_data("TARS", wake_response, "TARS")
    
    # Intento seguro de reproducir audio
    try:
        asyncio.run(play_audio_chunks(wake_response, "openai", True))
    except Exception as e:
        print(f"Audio Error: {e}")

def utterance_callback(message):
    """Procesa el mensaje del usuario."""
    if not message:
        return

    # 1. Extraer texto limpio
    user_text = ""
    try:
        if isinstance(message, str):
            if message.strip().startswith('{'):
                data = json.loads(message)
                user_text = data.get('text', '')
            else:
                user_text = message
    except:
        user_text = str(message)

    if not user_text: return

    # 2. Actualizar UI
    if ui_manager:
        ui_manager.deactivate_screensaver()
        ui_manager.update_data("USER", user_text, "USER")
    
    queue_message(f"USER: {user_text}")

    # 3. Comandos de Sistema
    cmd = user_text.lower()
    if "apágate" in cmd or "shutdown" in cmd:
        if ui_manager: ui_manager.update_data("SYSTEM", "Shutting down...", "SYSTEM")
        os.system("sudo shutdown -h now")
        return

    # 4. Generar Respuesta (LLM)
    reply = "Processing..."
    if ui_manager: ui_manager.update_data("TARS", reply, "TARS")
    
    try:
        # Llamada al cerebro
        reply = process_completion(user_text)
        # Limpieza básica
        reply = re.sub(r"<think>.*?</think>", "", reply, flags=re.DOTALL).strip()
        
        # Mostrar y Hablar
        if ui_manager: ui_manager.update_data("TARS", reply, "TARS")
        asyncio.run(play_audio_chunks(reply, "openai"))
        
    except Exception as e:
        queue_message(f"Error procesando respuesta: {e}")

def post_utterance_callback():
    pass
