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
        
        # Valores por defecto (se sobrescribirán al detectar el hardware)
        self.fs = 44100
        self.channels = 2
        
        self.threshold = 0.03
        self.silence_limit = 1.2
        self.amp_gain = amp_gain
        self.current_recording = []

    def start(self):
        self.running = True
        queue_message("EAR: Buscando hardware automáticamente...")
        threading.Thread(target=self._listen_loop, daemon=True).start()

    def _auto_detect_hardware(self):
        """Busca el dispositivo WM8960 por nombre y devuelve su ID real"""
        print("\n🔎 ESCANEANDO DISPOSITIVOS DE AUDIO...")
        try:
            devices = sd.query_devices()
            target_id = None
            
            # 1. Buscamos por nombre "wm8960" o "seeed"
            for i, dev in enumerate(devices):
                name = dev['name'].lower()
                # Si tiene canales de entrada y el nombre coincide
                if dev['max_input_channels'] > 0 and ('wm8960' in name or 'seeed' in name):
                    print(f"✅ ¡ENCONTRADO! ID: {i} | Nombre: {dev['name']}")
                    return i, int(dev['max_input_channels']), 44100 # Forzamos 44100Hz que sabemos que va bien
            
            # 2. Si no lo encuentra por nombre, buscamos cualquiera con 2 canales de entrada
            print("⚠️ No veo el nombre 'wm8960'. Buscando genérico estéreo...")
            for i, dev in enumerate(devices):
                if dev['max_input_channels'] == 2:
                    print(f"⚠️ Usando fallback: ID {i} ({dev['name']})")
                    return i, 2, 44100

        except Exception as e:
            print(f"❌ Error en autodetección: {e}")
        
        print("❌ FALLO TOTAL: Usando configuración por defecto (ID 1).")
        return 1, 1, 16000 # Fallback de emergencia

    def _listen_loop(self):
        audio_buffer = []
        is_recording = False
        silence_start = None
        
        # --- AUTO-CONFIGURACIÓN AL ARRANCAR ---
        device_id, channels, fs = self._auto_detect_hardware()
        
        # Aplicamos lo detectado
        self.channels = channels
        self.fs = fs
        
        tts_conf = self.config['TTS']
        api_key = getattr(tts_conf, 'openai_api_key', None) or os.environ.get("OPENAI_API_KEY")
        
        client = None
        if OpenAI and api_key:
            client = OpenAI(api_key=api_key)
        else:
            print("EAR ERROR: No API Key")
            return

        def callback(indata, frames, time, status):
            if status:
                # Ignoramos advertencias menores para no ensuciar el log
                pass
            audio_buffer.append(indata.copy())

        try:
            # Abrimos el stream con los datos DETECTADOS
            with sd.InputStream(samplerate=self.fs, channels=self.channels, 
                              device=device_id, callback=callback):
                
                print(f"EAR: 👂 Escuchando en ID {device_id} ({self.channels} canales, {self.fs}Hz)")
                
                while self.running and not self.shutdown_event.is_set():
                    if not audio_buffer:
                        time.sleep(0.1)
                        continue
                    
                    while audio_buffer:
                        chunk = audio_buffer.pop(0)
                        
                        # Calcular volumen
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
            print("Consejo: Reinicia la Raspberry si el HAT se ha quedado 'tonto'.")

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
