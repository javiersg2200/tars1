#!/usr/bin/env python3
"""
app.py - TARS-AI Mirror Edition (4GB RAM Optimized)
Soporte para Memoria Inteligente. Sin Servos/Visión.
"""

import os
import sys
import threading
import time
import warnings
warnings.filterwarnings("ignore")

# === Configuración de Rutas ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)
sys.path.insert(0, BASE_DIR)

# === Módulos Core ===
from modules.module_config import load_config
from modules.module_messageQue import queue_message

CONFIG = load_config()
VERSION = "5.0 (Mirror 4GB)"

# === Imports Esenciales ===
from modules.module_character import CharacterManager
from modules.module_tts import update_tts_settings
from modules.module_llm import initialize_manager_llm
from modules.module_stt import STTManager
from modules.module_cputemp import CPUTempModule

# Traemos funciones de lógica principal
from modules.module_main import (
    initialize_managers,
    wake_word_callback,
    utterance_callback,
    post_utterance_callback
)

# === Memoria (Inteligente vs Lite) ===
# Intentamos cargar la memoria avanzada para aprovechar tus 4GB de RAM
try:
    from modules.module_memory import MemoryManager
    queue_message("LOAD: Smart Memory (Embeddings) ENABLED for 4GB RAM")
except ImportError as e:
    # Si faltan librerías pesadas, usamos la Lite por seguridad
    from modules.module_memory_lite import MemoryManagerLite as MemoryManager
    queue_message(f"WARNING: Smart Memory libs not found ({e}). Using Lite Mode.")

# === UI (Pantalla) ===
try:
    from modules.module_ui import UIManager
    UI_AVAILABLE = True
except ImportError:
    UI_AVAILABLE = False
    queue_message("WARNING: UI module not found")

# === Clases Dummy (Batería Falsa) ===
class BatteryStub:
    """Simula una batería siempre al 100%"""
    def start(self): pass
    def stop(self): pass
    def get_level(self): return 100
    def get_status(self): return "AC Power (Mirror)"

# === Main ===
if __name__ == "__main__":
    queue_message(f"LOAD: TARS-AI {VERSION} starting...")
    
    shutdown_event = threading.Event()
    
    # Sensores Básicos
    cpu_temp = CPUTempModule()
    battery = BatteryStub()

    # === Inicializar UI ===
    if UI_AVAILABLE and CONFIG["UI"]["UI_enabled"]:
        ui_manager = UIManager(
            shutdown_event=shutdown_event,
            battery_module=battery,
            cpu_temp_module=cpu_temp
        )
        ui_manager.start()
    else:
        class UIManagerStub:
            def update_data(self, *args): pass
            def start(self): pass
            def stop(self): pass
        ui_manager = UIManagerStub()

    ui_manager.update_data("System", "TARS System Online", "SYSTEM")

    # === Gestores de IA ===
    char_manager = CharacterManager(config=CONFIG)
    
    # Inicializamos la memoria (puede tardar un poco más en arrancar la primera vez)
    memory_manager = MemoryManager(
        config=CONFIG,
        char_name=char_manager.char_name,
        char_greeting=char_manager.char_greeting,
        ui_manager=ui_manager
    )

    # === Gestor de Oído ===
    stt_manager = STTManager(
        config=CONFIG,
        shutdown_event=shutdown_event,
        ui_manager=ui_manager
    )
    
    stt_manager.set_wake_word_callback(wake_word_callback)
    stt_manager.set_utterance_callback(utterance_callback)
    stt_manager.set_post_utterance_callback(post_utterance_callback)

    # === Inicializar Lógica Principal ===
    initialize_managers(
        memory_manager,
        char_manager,
        stt_manager,
        ui_manager,
        shutdown_event,
        battery
    )
    
    initialize_manager_llm(memory_manager, char_manager)

    # === Bucle Principal ===
    try:
        stt_manager.start()
        queue_message("SYSTEM: TARS Listening.")
        
        while not shutdown_event.is_set():
            time.sleep(0.5)

    except KeyboardInterrupt:
        shutdown_event.set()
    finally:
        stt_manager.stop()
        ui_manager.stop()
        queue_message("SYSTEM: TARS Shutdown.")
