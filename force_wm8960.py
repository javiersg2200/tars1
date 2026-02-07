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
        self.fs = 16000
        self.channels = 1
        self.threshold = 0.015 # Un poco más sensible para el HAT
        self.silence_limit = 1.8
        self.amp_gain = amp_gain
        self.current_recording = []

    def start(self):
        self.running = True
        queue_message("EAR: Inicializando HAT WM8960...")
        threading.Thread(target=self._listen_loop, daemon=True).start()

    def _get_wm8960_device(self):
        \"\"\"Busca el ID del HAT WM8960\"\"\"
        try:
            devices = sd.query_devices()
            for i, dev in enumerate(devices):
                # Buscamos wm8960 en el nombre
                if "wm8960" in dev['name'].lower() and dev['max_input_channels'] > 0:
                    print(f"EAR: ¡HAT detectado! {dev['name']} (ID: {i})")
                    return i
        except Exception as e:
            print(f"EAR WARNING: {e}")
        return None

    def _listen_loop(self):
        audio_buffer = []
        is_recording = False
        silence_start = None
        
        device_id = self._get_wm8960_device()
        
        # API Key Setup
        tts_conf = self.config['TTS']
        api_key = None
        if hasattr(tts_conf, 'openai_api_key'): api_key = tts_conf.openai_api_key
        elif isinstance(tts_conf, dict): api_key = tts_conf.get('openai_api_key')
        if not api_key: api_key = os.environ.get("OPENAI_API_KEY")

        client = None
        if OpenAI and api_key:
            client = OpenAI(api_key=api_key)
        else:
            print("EAR ERROR: No API Key")
            return

        def callback(indata, frames, time, status):
            if status: print(status)
            audio_buffer.append(indata.copy())

        try:
            # Abrimos el stream con el ID del HAT
            with sd.InputStream(samplerate=self.fs, channels=self.channels, 
                              device=device_id, callback=callback):
                
                print(f"EAR: Micrófono del HAT WM8960 abierto (ID: {device_id})")
                
                while self.running and not self.shutdown_event.is_set():
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
                                print("🛑 PROCESANDO VOZ...")
                                is_recording = False
                                self._transcribe(self.current_recording, client)
                                self.current_recording = []
                        
                    time.sleep(0.01)
                    
        except Exception as e:
            print(f"EAR ERROR CRÍTICO: {e}")

    def _transcribe(self, audio_data, client):
        if not audio_data: return
        recording = np.concatenate(audio_data, axis=0)
        buffer = io.BytesIO()
        buffer.name = 'audio.wav'
        sf.write(buffer, recording, self.fs)
        buffer.seek(0)
        try:
            transcript = client.audio.transcriptions.create(
                model="whisper-1", file=buffer, language="es"
            )
            text = transcript.text
            print(f"🗣️ TARS ENTENDIÓ: '{text}'")
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
"""

print("🎚️ Configurando TARS para el HAT WM8960...")
with open("modules/module_stt.py", "w") as f:
    f.write(stt_code)
print("✅ ¡HECHO! Ahora buscará el hardware de Waveshare.")
