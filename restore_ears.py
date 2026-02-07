import os

stt_code = """#!/usr/bin/env python3
import threading
import time
import numpy as np
import sounddevice as sd
import soundfile as sf
import io
import os
from modules.module_config import load_config
from modules.module_messageQue import queue_message

# Intentamos importar OpenAI
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

class STTManager:
    def __init__(self, config, shutdown_event, ui_manager, amp_gain=1.0):
        self.config = config
        self.shutdown_event = shutdown_event
        self.ui_manager = ui_manager
        self.running = False
        self.utterance_callback = None
        
        # Configuración de Audio
        self.fs = 16000  # Frecuencia de muestreo (16kHz es estándar para STT)
        self.channels = 1
        self.threshold = 0.02  # UMBRAL DE SILENCIO (Ajustar si hay ruido)
        self.silence_limit = 2.0  # Segundos de silencio para cortar
        self.amp_gain = amp_gain

    def start(self):
        self.running = True
        queue_message("EAR: Escuchando micrófono... (Habla fuerte)")
        threading.Thread(target=self._listen_loop, daemon=True).start()

    def _listen_loop(self):
        # Buffer para guardar audio
        audio_buffer = []
        is_recording = False
        silence_start = None
        
        # Inicializar cliente OpenAI
        client = None
        api_key = self.config['TTS'].get('openai_api_key', os.environ.get("OPENAI_API_KEY"))
        if OpenAI and api_key:
            client = OpenAI(api_key=api_key)
        else:
            queue_message("EAR ERROR: No OpenAI API Key found!")
            return

        def callback(indata, frames, time, status):
            if status:
                print(status)
            # Copia segura del audio
            audio_buffer.append(indata.copy())

        # Abrimos el micrófono
        try:
            with sd.InputStream(samplerate=self.fs, channels=self.channels, callback=callback):
                while self.running and not self.shutdown_event.is_set():
                    if not audio_buffer:
                        time.sleep(0.1)
                        continue
                    
                    # Procesar chunks nuevos
                    while audio_buffer:
                        chunk = audio_buffer.pop(0)
                        volume = np.linalg.norm(chunk) * self.amp_gain / len(chunk)
                        
                        # Detección de Voz (VAD Simple)
                        if volume > self.threshold:
                            if not is_recording:
                                print("🎤 [Detectando Voz...]")
                                is_recording = True
                                self.current_recording = [chunk]
                                if self.ui_manager:
                                    self.ui_manager.update_data("USER", "Listening...", "USER")
                            else:
                                self.current_recording.append(chunk)
                            silence_start = None # Reiniciar contador de silencio
                        
                        elif is_recording:
                            # Estamos grabando pero hay silencio
                            self.current_recording.append(chunk)
                            if silence_start is None:
                                silence_start = time.time()
                            
                            # Si el silencio dura mucho, cortamos
                            elif time.time() - silence_start > self.silence_limit:
                                print("🛑 [Fin de frase detected]")
                                is_recording = False
                                self._transcribe(self.current_recording, client)
                                self.current_recording = []
                        
                    time.sleep(0.01)
                    
        except Exception as e:
            queue_message(f"EAR ERROR: Fallo en micrófono: {e}")

    def _transcribe(self, audio_data, client):
        if not audio_data: return
        
        # Convertir lista de arrays a un solo array
        recording = np.concatenate(audio_data, axis=0)
        
        # Guardar en memoria como WAV
        buffer = io.BytesIO()
        buffer.name = 'audio.wav'
        sf.write(buffer, recording, self.fs)
        buffer.seek(0)
        
        try:
            print("☁️ Enviando a OpenAI Whisper...")
            transcript = client.audio.transcriptions.create(
                model="whisper-1", 
                file=buffer,
                language="es" # Forzamos español, quítalo si quieres auto
            )
            text = transcript.text
            print(f"🗣️ Entendido: '{text}'")
            
            if text and len(text.strip()) > 1:
                if self.utterance_callback:
                    self.utterance_callback(text)
                    
        except Exception as e:
            print(f"Error transcribiendo: {e}")

    def stop(self):
        self.running = False

    def set_wake_word_callback(self, cb): pass
    
    def set_utterance_callback(self, cb):
        self.utterance_callback = cb
        
    def set_post_utterance_callback(self, cb): pass
    def play_wav(self, f): pass
    def pause(self): pass
    def resume(self): pass
"""

print("🦻 Instalando Oído Cloud (Whisper)...")
with open("modules/module_stt.py", "w") as f:
    f.write(stt_code)
print("¡HECHO! TARS ahora escucha por el micrófono.")
