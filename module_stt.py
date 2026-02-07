#!/usr/bin/env python3
"""
module_stt.py - Versión Lite para Raspberry Pi 4 (Espejo)
Eliminadas todas las dependencias pesadas (Torch, FastRTC) para evitar 'Illegal Instruction'.
"""

import os
import threading
import time
import queue
import numpy as np
import sounddevice as sd
from openai import OpenAI
import soundfile as sf

# Importamos utilidades básicas
from modules.module_messageQue import queue_message
from modules.module_config import load_config

CONFIG = load_config()

class STTManager:
    def __init__(self, config, shutdown_event: threading.Event, ui_manager, amp_gain: float = 1.0):
        self.config = config
        self.shutdown_event = shutdown_event
        self.ui_manager = ui_manager
        self.running = False
        
        # Configuración de Audio (Estándar para Pi 4)
        self.SAMPLE_RATE = 16000
        self.CHANNELS = 1
        self.DTYPE = 'int16'
        
        # Callbacks
        self.wake_word_callback = None
        self.utterance_callback = None
        self.post_utterance_callback = None # Añadido para compatibilidad
        
        # Cliente OpenAI (Usaremos la nube para no quemar la CPU)
        api_key = self.config['STT'].get('openai_api_key', os.environ.get("OPENAI_API_KEY"))
        self.client = OpenAI(api_key=api_key) if api_key else None

    def _listen_loop(self):
        """Bucle simple: Mantiene el hilo vivo sin consumir CPU excesiva"""
        queue_message("INFO: STT (Modo Espejo Pi4) Iniciado.")
        
        # Aquí implementaremos la escucha real más adelante.
        # Por ahora, un bucle de espera para que no de error al arrancar.
        while self.running and not self.shutdown_event.is_set():
            time.sleep(1)

    # === Métodos de Control ===
    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if hasattr(self, 'thread'):
            self.thread.join(timeout=1)

    # === Setters (Para que app.py no se queje) ===
    def set_wake_word_callback(self, callback):
        self.wake_word_callback = callback

    def set_utterance_callback(self, callback):
        self.utterance_callback = callback
    
    def set_post_utterance_callback(self, callback):
        self.post_utterance_callback = callback
    
    # === Utilidades Dummy ===
    def play_wav(self, filename):
        """Reproduce sonido de forma segura"""
        try:
            data, fs = sf.read(filename)
            sd.play(data, fs)
            sd.wait()
        except Exception as e:
            print(f"Error audio: {e}")

    def stop_generation(self):
        pass
