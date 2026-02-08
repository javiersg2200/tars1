#!/usr/bin/env python3
import threading
import time
import numpy as np
import sounddevice as sd
import soundfile as sf
import io
import os
from modules.module_config import load_config
from modules.module_messageQue import queue_message

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
        
        # Configuración inicial (se ajustará automáticamente)
        self.fs = 44100
        self.channels = 2
        
        self.threshold = 0.04 # Ajustar sensibilidad
        self.silence_limit = 1.5
        self.amp_gain = amp_gain
        self.current_recording = []

    def start(self):
        self.running = True
        threading.Thread(target=self._listen_loop, daemon=True).start()

    def _find_wm8960(self):
        """Busca el HAT por nombre y devuelve su ID real y canales"""
        print("\n--- BUSCANDO HAT WM8960 ---")
        try:
            devices = sd.query_devices()
            for i, dev in enumerate(devices):
                # Imprimimos lo que encuentra para depurar
                # print(f"ID {i}: {dev['name']} (In: {dev['max_input_channels']})")
                
                # Buscamos la palabra clave en el nombre
                if ('wm8960' in dev['name'].lower() or 'seeed' in dev['name'].lower()) and dev['max_input_channels'] > 0:
                    print(f"✅ ¡ENCONTRADO! ID Python: {i} | Nombre: {dev['name']}")
                    return i, dev['max_input_channels']
        except Exception as e:
            print(f"Error buscando dispositivos: {e}")
        
        print("❌ No se encontró por nombre. Intentando fallback a default.")
        return None, 2

    def _listen_loop(self):
        audio_buffer = []
        is_recording = False
        silence_start = None
        
        # 1. BUSCAR EL DISPOSITIVO AUTOMÁTICAMENTE
        device_id, dev_channels = self._find_wm8960()
        
        # Actualizamos canales según lo que diga el hardware
        self.channels = dev_channels
        
        tts_conf = self.config['TTS']
        api_key = getattr(tts_conf, 'openai_api_key', None) or os.environ.get("OPENAI_API_KEY")

        client = None
        if OpenAI and api_key:
            client = OpenAI(api_key=api_key)
        else:
            print("EAR ERROR: No API Key")
            return

        def callback(indata, frames, time, status):
            if status: print(f"EAR STATUS: {status}")
            audio_buffer.append(indata.copy())

        try:
            # Usamos el ID encontrado dinámicamente
            with sd.InputStream(samplerate=self.fs, channels=self.channels, 
                              device=device_id, callback=callback):
                
                print(f"EAR: Escuchando en ID {device_id} ({self.channels} canales, {self.fs}Hz)")
                queue_message("EAR: Oído activo y conectado.")
                
                while self.running and not self.shutdown_event.is_set():
                    if not audio_buffer:
                        time.sleep(0.1)
                        continue
                    
                    while audio_buffer:
                        chunk = audio_buffer.pop(0)
                        
                        # Calcular volumen (promedio)
                        volume = np.linalg.norm(chunk) * self.amp_gain / len(chunk)
                        
                        if volume > self.threshold:
                            if not is_recording:
                                print(f"🎤 ESCUCHANDO... (Vol: {volume:.4f})")
                                is_recording = True
                                self.current_recording = [chunk]
                            else:
                                self.current_recording.append(chunk)
                            silence_start = None
                        
                        elif is_recording:
                            self.current_recording.append(chunk)
                            if silence_start is None:
                                silence_start = time.time()
                            elif time.time() - silence_start > self.silence_limit:
                                print("🛑 PROCESANDO...")
                                is_recording = False
                                self._transcribe(self.current_recording, client)
                                self.current_recording = []
                        
                    time.sleep(0.01)
                    
        except Exception as e:
            print(f"EAR ERROR CRÍTICO: {e}")
            print("Posible solución: Ejecuta 'python list_audio.py' para ver los IDs reales.")

    def _transcribe(self, audio_data, client):
        if not audio_data: return
        recording = np.concatenate(audio_data, axis=0)
        buffer = io.BytesIO()
        buffer.name = 'audio.wav'
        sf.write(buffer, recording, self.fs)
        buffer.seek(0)
        try:
            transcript = client.audio.transcriptions.create(
                model="whisper-1", 
                file=buffer, 
                language="es"
            )
            text = transcript.text
            print(f"🗣️ TARS: '{text}'")
            if self.utterance_callback:
                self.utterance_callback(text)
        except Exception as e:
            print(f"Error Whisper: {e}")

    def stop(self): self.running = False
    def set_wake_word_callback(self, cb): pass
    def set_utterance_callback(self, cb): self.utterance_callback = cb
    def set_post_utterance_callback(self, cb): pass
    def play_wav(self, f): pass
    def pause(self): pass
    def resume(self): pass
