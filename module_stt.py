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
        self.threshold = 0.2 # Mantenemos el umbral que te funcionó bien
        self.silence_limit = 1.2
        self.amp_gain = amp_gain
        self.current_recording = []

    def start(self):
        self.running = True
        queue_message("EAR: Sistema Walkie-Talkie (Reiniciar al hablar)")
        threading.Thread(target=self._listen_loop, daemon=True).start()

    def _listen_loop(self):
        # Configuración de OpenAI
        tts_conf = self.config['TTS']
        api_key = getattr(tts_conf, 'openai_api_key', None) or os.environ.get("OPENAI_API_KEY")
        client = OpenAI(api_key=api_key) if (OpenAI and api_key) else None

        # Bucle Principal: Gestiona el ciclo de vida del micrófono
        while self.running and not self.shutdown_event.is_set():
            
            # 1. SI TARS ESTÁ HABLANDO, ESPERAMOS
            if status.is_speaking:
                time.sleep(0.1)
                continue

            # 2. SI TARS ESTÁ CALLADO, ABRIMOS EL MICRO
            try:
                # Buffer local para este ciclo de escucha
                self.audio_buffer = [] 
                
                def callback(indata, frames, time_info, status_code):
                    if status_code: pass
                    self.audio_buffer.append(indata.copy())

                # ABRIMOS EL STREAM (Esto reinicia el driver)
                with sd.InputStream(samplerate=self.fs, channels=self.channels, 
                                  callback=callback):
                    
                    print("EAR: 👂 Oído ABIERTO y listo.")
                    
                    # Bucle Interno: Escuchar mientras nadie hable
                    is_recording = False
                    silence_start = None
                    
                    while self.running and not status.is_speaking:
                        # Si de repente TARS empieza a hablar, ROMPEMOS este bucle
                        # para que se cierre el 'with stream' y libere la tarjeta
                        if status.is_speaking:
                            print("EAR: 🔇 TARS va a hablar -> Apagando oído...")
                            break

                        if not self.audio_buffer:
                            time.sleep(0.05)
                            continue
                        
                        while self.audio_buffer:
                            chunk = self.audio_buffer.pop(0)
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
                                    # Procesamos en un hilo aparte para no bloquear el cierre del micro si hiciera falta
                                    threading.Thread(target=self._transcribe, 
                                                   args=(self.current_recording, client)).start()
                                    self.current_recording = []
                        
                        time.sleep(0.01)

            except Exception as e:
                print(f"EAR RESTART ERROR: {e}")
                time.sleep(1) # Esperar un poco antes de reintentar si falló el hardware

    def _transcribe(self, audio_data, client):
        if not audio_data: return
        try:
            recording = np.concatenate(audio_data, axis=0)
            buffer = io.BytesIO()
            buffer.name = 'audio.wav'
            sf.write(buffer, recording, self.fs)
            buffer.seek(0)
            
            transcript = client.audio.transcriptions.create(
                model="whisper-1", 
                file=buffer, 
                language="es"
            )
            text = transcript.text
            
            if not text or len(text.strip()) < 2: return

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
