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
        
        # Configuración del HAT
        self.rate = 44100
        self.chunk_size = 2048
        self.threshold = 500  # Umbral para enteros de 16-bit (ajustar si necesario)
        self.silence_limit = 1.5
        self.current_recording = []

    def start(self):
        self.running = True
        queue_message("EAR: Arrancando motor 'arecord' (Linux nativo)...")
        threading.Thread(target=self._listen_loop, daemon=True).start()

    def _get_card_number(self):
        """Busca el número de tarjeta de wm8960 en el sistema"""
        try:
            # Ejecutamos 'arecord -l' para ver la lista real
            result = subprocess.check_output("arecord -l", shell=True).decode()
            for line in result.split('\n'):
                if "wm8960" in line:
                    # Ejemplo: card 3: wm8960soundcard...
                    parts = line.split(":")
                    card_num = parts[0].replace("card ", "").strip()
                    print(f"✅ Tarjeta detectada en el sistema: {card_num}")
                    return card_num
        except:
            pass
        return "3" # Fallback al que te funcionó antes

    def _listen_loop(self):
        card_num = self._get_card_number()
        device_str = f"hw:{card_num},0"
        
        # COMANDO MÁGICO: Usamos arecord directamente
        # -t raw: datos crudos
        # -f S16_LE: formato estándar
        # -r 44100: frecuencia HAT
        # -c 2: estéreo
        cmd = [
            "arecord", 
            "-D", device_str, 
            "-f", "S16_LE", 
            "-r", str(self.rate), 
            "-c", "2", 
            "-t", "raw"
        ]
        
        print(f"EAR: Ejecutando -> {' '.join(cmd)}")
        
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=self.chunk_size*4)
        
        is_recording = False
        silence_start = None
        
        # Setup OpenAI
        tts_conf = self.config['TTS']
        api_key = getattr(tts_conf, 'openai_api_key', None) or os.environ.get("OPENAI_API_KEY")
        client = OpenAI(api_key=api_key) if (OpenAI and api_key) else None

        if not client:
            print("EAR ERROR: Falta API Key")
            return

        print("EAR: 👂 Escuchando flujo de datos RAW...")

        try:
            while self.running and not self.shutdown_event.is_set():
                # Leer bytes crudos del proceso
                raw_bytes = process.stdout.read(self.chunk_size * 2 * 2) # 2 canales * 2 bytes por sample
                
                if not raw_bytes:
                    time.sleep(0.01)
                    continue
                
                # Convertir bytes a números (Int16)
                audio_data = np.frombuffer(raw_bytes, dtype=np.int16)
                
                # Calcular volumen (RMS simple)
                volume = np.sqrt(np.mean(audio_data**2))
                
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
                        print("🛑 Procesando audio...")
                        is_recording = False
                        self._transcribe(self.current_recording, client)
                        self.current_recording = []
                
        except Exception as e:
            print(f"EAR ERROR: {e}")
        finally:
            process.terminate()

    def _transcribe(self, audio_data_list, client):
        if not audio_data_list: return
        
        # Concatenar todos los fragmentos
        full_audio = np.concatenate(audio_data_list)
        
        # Convertir a BytesIO para Whisper
        buffer = io.BytesIO()
        buffer.name = 'audio.wav'
        sf.write(buffer, full_audio, self.rate)
        buffer.seek(0)
        
        try:
            transcript = client.audio.transcriptions.create(
                model="whisper-1", 
                file=buffer, 
                language="es"
            )
            text = transcript.text
            print(f"🗣️ TARS OYÓ: '{text}'")
            if self.utterance_callback:
                self.utterance_callback(text)
        except Exception as e:
            print(f"Error Whisper: {e}")

    def stop(self): 
        self.running = False

    # Métodos dummy
    def set_wake_word_callback(self, cb): pass
    def set_utterance_callback(self, cb): self.utterance_callback = cb
    def set_post_utterance_callback(self, cb): pass
    def play_wav(self, f): pass
    def pause(self): pass
    def resume(self): pass
