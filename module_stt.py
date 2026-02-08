#!/usr/bin/env python3
import threading
import time
import numpy as np
import subprocess
import io
import os
import soundfile as sf
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
        
        self.rate = 44100
        self.chunk_size = 4096 
        self.threshold = 500  # Umbral para enteros (arecord usa int16, valores de 0 a 32000)
        self.silence_limit = 1.2
        self.current_recording = []

    def start(self):
        self.running = True
        queue_message("EAR: Modo Nativo (arecord pipe)")
        threading.Thread(target=self._listen_loop, daemon=True).start()

    def _listen_loop(self):
        tts_conf = self.config['TTS']
        api_key = getattr(tts_conf, 'openai_api_key', None) or os.environ.get("OPENAI_API_KEY")
        client = OpenAI(api_key=api_key) if (OpenAI and api_key) else None

        process = None
        is_recording = False
        silence_start = None

        print("EAR: 👂 Iniciando motor de escucha nativo...")

        while self.running and not self.shutdown_event.is_set():
            
            # --- FASE 1: GESTIÓN DEL PROCESO ---
            
            # Si TARS habla, matamos el oído
            if status.is_speaking:
                if process:
                    # print("EAR: 🔇 TARS habla -> Apagando arecord")
                    process.terminate()
                    process.wait() # Asegurar que murió
                    process = None
                    is_recording = False
                    self.current_recording = []
                time.sleep(0.1)
                continue

            # Si TARS calla y no hay oído, lo encendemos
            if not process and not status.is_speaking:
                try:
                    # Lanzamos arecord en segundo plano y leemos su salida
                    # -D default: Usa el micro seleccionado en pantalla
                    cmd = ["arecord", "-D", "default", "-f", "S16_LE", "-r", str(self.rate), "-c", "2", "-t", "raw", "-q"]
                    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
                    print("EAR: 👂 Oído REINICIADO y listo.")
                    # Limpiamos buffer antiguo
                    self.current_recording = []
                except Exception as e:
                    print(f"EAR START ERROR: {e}")
                    time.sleep(1)
                    continue

            # --- FASE 2: LECTURA DE AUDIO ---
            if process:
                try:
                    # Leemos 4kb de audio crudo
                    raw_bytes = process.stdout.read(self.chunk_size * 4) 
                    
                    if not raw_bytes: 
                        time.sleep(0.01)
                        continue

                    # Convertimos bytes a números
                    audio_data = np.frombuffer(raw_bytes, dtype=np.int16)
                    
                    # Calcular volumen (RMS)
                    volume = np.sqrt(np.mean(audio_data**2))

                    # Lógica de detección de voz
                    if volume > self.threshold:
                        if not is_recording:
                            print(f"🎤 VOZ DETECTADA (Nivel: {int(volume)})")
                            is_recording = True
                            self.current_recording = [audio_data]
                        else:
                            self.current_recording.append(audio_data)
                        silence_start = None
                    
                    elif is_recording:
                        self.current_recording.append(audio_data)
                        if silence_start is None:
                            silence_start = time.time()
                        elif time.time() - silence_start > self.silence_limit:
                            print("🛑 PROCESANDO...")
                            is_recording = False
                            # Enviamos a transcribir
                            threading.Thread(target=self._transcribe, args=(self.current_recording, client)).start()
                            self.current_recording = []
                            
                except Exception as e:
                    # Si arecord muere, reseteamos variable para que se reinicie en la siguiente vuelta
                    process = None

        # Limpieza al salir
        if process: process.terminate()

    def _transcribe(self, audio_data_list, client):
        if not audio_data_list: return
        try:
            # Concatenar y convertir para Whisper
            full_audio = np.concatenate(audio_data_list)
            # Normalizar de int16 a float para guardar wav
            full_audio_float = full_audio.astype(np.float32) / 32768.0
            
            buffer = io.BytesIO()
            buffer.name = 'audio.wav'
            sf.write(buffer, full_audio_float, self.rate)
            buffer.seek(0)
            
            transcript = client.audio.transcriptions.create(
                model="whisper-1", 
                file=buffer, 
                language="es"
            )
            text = transcript.text
            
            if not text or len(text.strip()) < 2: return
            if "Subtítulos" in text or "Amara" in text: return

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
