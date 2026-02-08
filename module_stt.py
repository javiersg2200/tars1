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
import modules.tars_status as status 

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
        
        self.fs = 44100 
        self.channels = 2 
        
        # --- CAMBIO 1: UMBRAL MÁS ALTO ---
        # Tu voz es 0.39, el eco es 0.14. Ponemos el corte en 0.2
        self.threshold = 0.2 
        
        self.silence_limit = 1.2
        self.amp_gain = amp_gain
        self.current_recording = []

    def start(self):
        self.running = True
        queue_message("EAR: Sistema Anti-Eco (Umbral 0.2 + Delay)")
        threading.Thread(target=self._listen_loop, daemon=True).start()

    def _listen_loop(self):
        audio_buffer = []
        is_recording = False
        silence_start = None
        device_id = None 
        
        # Variable para controlar el tiempo de espera después de hablar
        last_speech_time = 0
        
        tts_conf = self.config['TTS']
        api_key = getattr(tts_conf, 'openai_api_key', None) or os.environ.get("OPENAI_API_KEY")
        client = OpenAI(api_key=api_key) if (OpenAI and api_key) else None

        def callback(indata, frames, time, status):
            if status: pass
            audio_buffer.append(indata.copy())

        try:
            with sd.InputStream(samplerate=self.fs, channels=self.channels, 
                              device=device_id, callback=callback):
                
                print(f"EAR: 👂 Escuchando (Umbral de corte: {self.threshold})")
                
                while self.running and not self.shutdown_event.is_set():
                    
                    # --- LÓGICA ANTI-ECO MEJORADA ---
                    if status.is_speaking:
                        # Si está hablando, limpiamos todo y actualizamos el reloj
                        audio_buffer = [] 
                        is_recording = False 
                        last_speech_time = time.time()
                        time.sleep(0.1)
                        continue
                    
                    # --- CAMBIO 2: TIEMPO DE ENFRIAMIENTO (COOLDOWN) ---
                    # Si hace menos de 2 segundos que terminó de hablar, seguimos sordos
                    # Esto evita que escuche el "final" de su propia frase
                    if time.time() - last_speech_time < 2.0:
                        audio_buffer = []
                        time.sleep(0.1)
                        continue
                    # ----------------------------------

                    if not audio_buffer:
                        time.sleep(0.1)
                        continue
                    
                    while audio_buffer:
                        chunk = audio_buffer.pop(0)
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
            print(f"EAR ERROR: {e}")

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
            
            # Filtro extra: Si lo que ha entendido es muy corto, lo ignoramos
            if not text or len(text.strip()) < 2:
                return

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
