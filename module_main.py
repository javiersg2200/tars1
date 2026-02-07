"""
module_main.py - TARS Mirror Edition (Pi 4 Optimized)
Lógica central limpia. Sin servos, sin Bluetooth, con apagado real para Raspberry.
"""
# === Standard Libraries ===
import os
import threading
import json
import re
import concurrent.futures
import sys
import time
import asyncio

# === Custom Modules ===
from modules.module_config import load_config
from modules.module_llm import process_completion
from modules.module_tts import play_audio_chunks
from modules.module_messageQue import queue_message

# NOTA: Hemos eliminado module_servoctl para evitar errores en el espejo

CONFIG = load_config()

# === UI Import (Solo si está disponible) ===
UIManager = None
try:
    from modules.module_ui import UIManager as _UIManager
    UIManager = _UIManager
except ImportError:
    pass

# === Constants and Globals ===
ui_manager = None
character_manager = None
memory_manager = None
stt_manager = None
shutdown_event = None
battery_module = None

stop_event = threading.Event()

# === Callback Functions ===

def wake_word_callback(wake_response):
    """Respuesta inicial al detectar la palabra clave"""
    if ui_manager:
        ui_manager.deactivate_screensaver()

    char_name = CONFIG['CHAR']['character_name']
    ui_manager.update_data(char_name, wake_response, char_name)
    
    # Reproducimos el audio de respuesta
    asyncio.run(play_audio_chunks(wake_response, CONFIG['TTS']['ttsoption'], True))

def utterance_callback(message):
    """
    Procesa el mensaje del usuario y genera respuesta.
    Adaptado para aceptar tanto JSON (versión antigua) como Texto Plano (versión nueva).
    """
    try:
        if ui_manager:
            ui_manager.deactivate_screensaver()
        
        # 1. Intentamos extraer el texto, venga como venga
        user_text = ""
        try:
            # Si es JSON
            message_dict = json.loads(message)
            user_text = message_dict.get('text', '').strip()
        except (json.JSONDecodeError, TypeError):
            # Si es texto plano
            user_text = str(message).strip()

        if not user_text:
            return

        # 2. Mostramos lo que has dicho
        ui_manager.update_data("USER", user_text, "USER")
        queue_message(f"USER: {user_text}", stream=False) 

        # 3. COMANDO SECRETO: APAGADO
        # Añadido "apágate" para tu comodidad
        cmd = user_text.lower()
        if "shutdown pc" in cmd or "apágate" in cmd or "apagar sistema" in cmd:
            queue_message(f"SYSTEM: Iniciando secuencia de apagado...")
            if ui_manager:
                ui_manager.update_data("SYSTEM", "Goodbye.", "SYSTEM")
            
            # Reproduce despedida rápida antes de morir
            asyncio.run(play_audio_chunks("Apagando sistemas.", CONFIG['TTS']['ttsoption']))
            time.sleep(2)
            
            # Comando real de Linux para apagar la Raspberry
            os.system('sudo shutdown -h now')
            return 
        
        # 4. Generamos respuesta con el LLM (OpenAI/Local)
        reply = process_completion(user_text)

        # Limpieza de etiquetas <think> (pensamientos internos)
        reply = re.sub(r"<think>.*?</think>", "", reply, flags=re.DOTALL).strip()

        # 5. Enviamos la respuesta a la pantalla y altavoces
        char_name = CONFIG['CHAR']['character_name']
        ui_manager.update_data(char_name, reply, "TARS")
        queue_message(f"{char_name}: {reply}", stream=False) 

        # Limpiamos caracteres raros para el TTS
        reply_clean = re.sub(r'[^a-zA-Z0-9\s.,?!;:"\'-<>]', '', reply)
        
        asyncio.run(play_audio_chunks(reply_clean, CONFIG['TTS']['ttsoption']))

    except Exception as e:
        queue_message(f"ERROR en utterance_callback: {e}")

def post_utterance_callback():
    """Reinicia la escucha. En modo Lite esto se gestiona automáticamente."""
    pass

# === Initialization ===
def initialize_managers(mem_manager, char_manager_inst, stt_mgr, ui_mgr, shutdown_evt=None, battery_mod=None):
    """Conecta todos los módulos entre sí."""
    global memory_manager, character_manager, stt_manager, ui_manager, shutdown_event, battery_module
    memory_manager = mem_manager
    character_manager = char_manager_inst
    stt_manager = stt_mgr
    ui_manager = ui_mgr
    shutdown_event = shutdown_evt
    battery_module = battery_mod

def startup_initialization():
    """
    Inicialización de hardware.
    LIMPIADO: Eliminados servos y ventiladores para evitar errores en el Espejo.
    """
    queue_message("SYSTEM: TARS Mirror Mode Initialized.")
    # Aquí iría el código de servos, pero lo hemos quitado para proteger tu Pi 4.
