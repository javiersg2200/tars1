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
        
        self.fs = 44100 
        self.channels = 2 
        
        # --- AJUSTES DE CONVERSACIÃ“N ---
        # Umbral de ruido: 0.08 ignora soplidos leves pero capta tu voz
        self.threshold = 0.08 
        # LÃ­mite de silencio: 2.0 segundos de paciencia para que puedas respirar entre palabras
        self.silence_limit = 2.0 
        
        self.amp_gain = amp_gain
        self.current_recording = []

    def start(self):
        self.running = True
        queue_message("EAR: Sistema SÃ­ncrono (ConversaciÃ³n Fluida)")
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
                    
                    print("EAR: ðŸ‘‚ OÃ­do ABIERTO y escuchando...")
                    
                    is_recording = False
                    silence_start = None
                    self.current_recording = []
                    
                    while self.running:
                        if status.is_speaking:
                            print("EAR: ðŸ”‡ TARS va a hablar -> Apagando oÃ­do...")
                            break 

                        chunk, overflowed = stream.read(2048)
                        volume = np.sqrt(np.mean(chunk**2)) * self.amp_gain
                        
                        if volume > self.threshold:
                            if not is_recording:
                                print(f"ðŸŽ¤ VOZ DETECTADA (Vol: {volume:.4f})")
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
                                print("ðŸ›‘ PROCESANDO...")
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
            if "SubtÃ­tulos" in text or "Amara" in text: return

            print(f"ðŸ—£ï¸ TARS: '{text}'")
            if self.utterance_callback:
                self.utterance_callback(text)
                
        except Exception as e:
            print(f"âŒ Error Whisper: {e}")

    def stop(self): self.running = False
    def set_wake_word_callback(self, cb): pass
    def set_utterance_callback(self, cb): self.utterance_callback = cb
    def set_post_utterance_callback(self, cb): pass
    def play_wav(self, f): pass
    def pause(self): pass
    def resume(self): pass        queue_message("EAR: Sistema SÃ­ncrono (Alta Sensibilidad)")
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
                # 2. SOLUCIÃ“N AL CUELGUE: Leemos el audio directamente (stream.read) 
                # en lugar de usar procesos en segundo plano que se mueren en Linux.
                with sd.InputStream(samplerate=self.fs, channels=self.channels, 
                                  blocksize=2048, device=None) as stream:
                    
                    print("EAR: ðŸ‘‚ OÃ­do ABIERTO (Sensibilidad alta)...")
                    
                    is_recording = False
                    silence_start = None
                    self.current_recording = []
                    
                    while self.running:
                        # Si TARS tiene que hablar, salimos del bucle para apagar el micro
                        if status.is_speaking:
                            print("EAR: ðŸ”‡ TARS va a hablar -> Apagando oÃ­do...")
                            break 

                        # Leer el audio directamente de la tarjeta (se bloquea hasta tener datos)
                        chunk, overflowed = stream.read(2048)
                        
                        # CÃ¡lculo de volumen mÃ¡s preciso y estable
                        volume = np.sqrt(np.mean(chunk**2)) * self.amp_gain
                        
                        if volume > self.threshold:
                            if not is_recording:
                                print(f"ðŸŽ¤ VOZ DETECTADA (Vol: {volume:.4f})")
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
                                print("ðŸ›‘ PROCESANDO...")
                                is_recording = False
                                
                                # Guardamos lo grabado y limpiamos para la siguiente frase
                                audio_to_send = self.current_recording.copy()
                                self.current_recording = []
                                
                                # Lo enviamos a OpenAI en un hilo para seguir escuchando si hace falta
                                threading.Thread(target=self._transcribe, 
                                               args=(audio_to_send, client)).start()
                                
            except Exception as e:
                print(f"EAR ERROR DE HARDWARE: {e}")
                time.sleep(1) # Si el driver choca, le damos 1 segundo para respirar

            # Pausa obligatoria al terminar de hablar para soltar la tarjeta de sonido
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
            
            # Filtros anti-ruido fantasma
            if not text or len(text.strip()) < 2: return
            if "SubtÃ­tulos" in text or "Amara" in text: return

            print(f"ðŸ—£ï¸ TARS: '{text}'")
            if self.utterance_callback:
                self.utterance_callback(text)
                
        except Exception as e:
            print(f"âŒ Error Whisper: {e}")

    def stop(self): self.running = False
    def set_wake_word_callback(self, cb): pass
    def set_utterance_callback(self, cb): self.utterance_callback = cb
    def set_post_utterance_callback(self, cb): pass
    def play_wav(self, f): pass
    def pause(self): pass
    def resume(self): pass
