#!/usr/bin/env python3
import threading
import time
import numpy as np
import sounddevice as sd
import soundfile as sf
import io
import os
from modules.module_config import load_config
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
        
        self.fs = 44100 
        self.channels = 2 
        
        # --- AJUSTES DE TERApeuta ---
        # Umbral muy bajo para captar las bajadas de voz entre palabras
        self.threshold = 0.03 
        # 2.5 segundos de pura paciencia
        self.silence_limit = 2.5 
        
        self.amp_gain = amp_gain
        self.current_recording = []

    def start(self):
        self.running = True
        print("EAR: Sistema Síncrono (Modo Paciente Activado)")
        threading.Thread(target=self._listen_loop, daemon=True).start()

    def _listen_loop(self):
        tts_conf = self.config['TTS']
        api_key = getattr(tts_conf, 'openai_api_key', None) or os.environ.get("OPENAI_API_KEY")
        client = OpenAI(api_key=api_key) if (OpenAI and api_key) else None

        while self.running and not self.shutdown_event.is_set():
            if status.is_speaking:
                time.sleep(0.1)
                continue

            try:
                with sd.InputStream(samplerate=self.fs, channels=self.channels, 
                                  blocksize=2048, device=None) as stream:
                    
                    print("EAR: 👂 Oído ABIERTO y escuchando...")
                    
                    is_recording = False
                    silence_start = None
                    self.current_recording = []
                    
                    while self.running:
                        if status.is_speaking:
                            print("EAR: 🔇 TARS va a hablar -> Apagando oído...")
                            break 

                        chunk, overflowed = stream.read(2048)
                        volume = np.sqrt(np.mean(chunk**2)) * self.amp_gain
                        
                        if volume > self.threshold:
                            if not is_recording:
                                print(f"🎤 VOZ DETECTADA (Vol: {volume:.4f})")
                                is_recording = True
                                self.current_recording = [chunk]
                            else:
                                self.current_recording.append(chunk)
                                # Si estábamos contando silencio, lo cancelamos al volver a oírte
                                if silence_start is not None:
                                    print("🗣️ (Sigues hablando, reseteando reloj...)")
                            silence_start = None
                            
                        elif is_recording:
                            self.current_recording.append(chunk)
                            if silence_start is None:
                                silence_start = time.time()
                                print("⏳ (Pausa detectada, esperando 2.5s...)")
                            elif time.time() - silence_start > self.silence_limit:
                                print("🛑 PROCESANDO LA FRASE COMPLETA...")
                                is_recording = False
                                
                                audio_to_send = self.current_recording.copy()
                                self.current_recording = []
                                
                                threading.Thread(target=self._transcribe, 
                                               args=(audio_to_send, client)).start()
                                
            except Exception as e:
                print(f"EAR ERROR DE HARDWARE: {e}")
                time.sleep(1) 

            if status.is_speaking:
                while status.is_speaking:
                    time.sleep(0.1)
                time.sleep(0.5) 

    def _transcribe(self, audio_data, client):
        if not audio_data: return
        
        try:
            recording = np.concatenate(audio_data, axis=0)
            buffer = io.BytesIO()
            buffer.name = 'audio.wav'
            sf.write(buffer, recording, self.fs)
            buffer.seek(0)
            
            if not client: return

            transcript = client.audio.transcriptions.create(
                model="whisper-1", 
                file=buffer, 
                language="es",
                timeout=10.0
            )
            
            text = transcript.text
            
            if not text or len(text.strip()) < 2: return
            if "Subtítulos" in text or "Amara" in text: return

            print(f"🗣️ TARS: '{text}'")
            if self.utterance_callback:
                self.utterance_callback(text)
                
        except Exception as e:
            print(f"❌ Error Whisper: {e}")

    def stop(self): self.running = False
    def set_wake_word_callback(self, cb): pass
    def set_utterance_callback(self, cb): self.utterance_callback = cb
    def set_post_utterance_callback(self, cb): pass
    def play_wav(self, f): pass
    def pause(self): pass
    def resume(self): pass
