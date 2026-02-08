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
        
        # CONFIGURACIÓN
        self.rate = 44100
        self.chunk_size = 4096 # Buffer un poco más grande
        
        # --- UMBRAL MUY BAJO PARA PRUEBAS ---
        self.threshold = 150  
        self.silence_limit = 2.0
        self.current_recording = []

    def start(self):
        self.running = True
        queue_message("EAR: Arrancando en MODO DEBUG...")
        threading.Thread(target=self._listen_loop, daemon=True).start()

    def _get_card_number(self):
        try:
            result = subprocess.check_output("arecord -l", shell=True).decode()
            for line in result.split('\n'):
                if "wm8960" in line:
                    parts = line.split(":")
                    card_num = parts[0].replace("card ", "").strip()
                    return card_num
        except:
            pass
        return "3"

    def _listen_loop(self):
        card_num = self._get_card_number()
        print(f"EAR: Usando tarjeta {card_num}")
        
        # Usamos arecord forzando parámetros
        cmd = [
            "arecord", 
            "-D", f"hw:{card_num},0", 
            "-f", "S16_LE", 
            "-r", str(self.rate), 
            "-c", "2", 
            "-t", "raw"
        ]
        
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        
        is_recording = False
        silence_start = None
        
        # API Key
        tts_conf = self.config['TTS']
        api_key = getattr(tts_conf, 'openai_api_key', None) or os.environ.get("OPENAI_API_KEY")
        client = OpenAI(api_key=api_key) if (OpenAI and api_key) else None

        print("EAR: 👂 Escuchando... (Mira los números de volumen)")

        try:
            while self.running and not self.shutdown_event.is_set():
                # Leemos un trozo de audio
                raw_bytes = process.stdout.read(self.chunk_size * 4) 
                
                if not raw_bytes or len(raw_bytes) == 0:
                    continue
                
                # Convertir a números
                audio_data = np.frombuffer(raw_bytes, dtype=np.int16)
                
                # Calcular volumen real
                volume = int(np.sqrt(np.mean(audio_data**2)))
                
                # --- DEBUG: IMPRIMIR VOLUMEN ---
                # Si el volumen es mayor que 10 (para no ensuciar con silencio absoluto) lo imprimimos
                if volume > 10:
                    print(f"🔊 VOL: {volume}", end="\r") 
                
                if volume > self.threshold:
                    if not is_recording:
                        print(f"\n🎤 [DETECTADO] Iniciando grabación (Nivel: {volume})")
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
                        print("\n🛑 Fin de frase. Enviando a OpenAI...")
                        is_recording = False
                        self._transcribe(self.current_recording, client)
                        self.current_recording = []
                
        except Exception as e:
            print(f"EAR ERROR: {e}")
        finally:
            process.terminate()

    def _transcribe(self, audio_data_list, client):
        if not audio_data_list: return
        full_audio = np.concatenate(audio_data_list)
        buffer = io.BytesIO()
        buffer.name = 'audio.wav'
        sf.write(buffer, full_audio, self.rate)
        buffer.seek(0)
        
        try:
            transcript = client.audio.transcriptions.create(
                model="whisper-1", file=buffer, language="es"
            )
            text = transcript.text
            print(f"🗣️ TARS OYÓ: '{text}'")
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
