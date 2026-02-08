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
        
        # Umbral para tu voz (ajústalo si es necesario)
        self.threshold = 0.2 
        
        self.silence_limit = 1.2
        self.amp_gain = amp_gain
        self.current_recording = []

    def start(self):
        self.running = True
        queue_message("EAR: Sistema Anti-Eco (Sincronizado)")
        threading.Thread(target=self._listen_loop, daemon=True).start()

    def _listen_loop(self):
        audio_buffer = []
        is_recording = False
        silence_start = None
        device_id = None 

        tts_conf = self.config['TTS']
        api_key = getattr(tts_conf, 'openai_api_key', None) or os.environ.get("OPENAI_API_KEY")
        client = OpenAI(api_key=api_key) if (OpenAI and api_key) else None

        def callback(indata, frames, time, status):
            if status: pass
            audio_buffer.append(indata.copy())

        try:
            with sd.InputStream(samplerate=self.fs, channels=self.channels, 
                              device=device_id, callback=callback):
                
                print(f"EAR: 👂 Escuchando...")
                
                while self.running and not self.shutdown_event.is_set():
                    
                    # --- LÓGICA CRÍTICA ---
                    # Si TARS está hablando, VACIAMOS el buffer y no hacemos nada más.
                    # Es como si se tapara los oídos físicamente.
                    if status.is_speaking:
                        if len(audio_buffer) > 0:
                            audio_buffer.clear() # ¡Borrar lo que entra!
                            is_recording = False # Cancelar cualquier grabación a medias
                        time.sleep(0.05) # Chequeo rápido
                        continue
                    # ----------------------

                    if not audio_buffer:
                        time.sleep(0.05)
                        continue
                    
                    while audio_buffer:
                        chunk = audio_buffer.pop(0)
                        
                        # Si justo empezó a hablar mientras procesábamos este trozo -> PARAR
                        if status.is_speaking:
                            audio_buffer.clear()
                            break

                        volume = np.linalg.norm(chunk) * self.amp_gain / len(chunk)
                        
                        if volume > self.threshold:
                            if not is_recording:
                                print(f"🎤 VOZ DETECTADA (Vol: {volume:.4f})")
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
            
            # Filtro básico de ruido
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
