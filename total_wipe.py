import os

# DEFINICIONES DE CÓDIGO SEGURO (LITE)
# ---------------------------------------------------------

CODE_MEMORY = """#!/usr/bin/env python3
# module_memory.py - LITE VERSION
from modules.module_messageQue import queue_message
class MemoryManager:
    def __init__(self, config, char_name, char_greeting, ui_manager=None):
        self.config = config
        self.char_name = char_name
        self.ui_manager = ui_manager
    def get_context(self, user_input): return ""
    def write_longterm_memory(self, user_input, bot_response): pass
    def update_topic_index_with_ai_response(self, text): pass
    def load_memory(self): pass
    def save_memory(self): pass
"""

CODE_BROWSER = """#!/usr/bin/env python3
# module_browser.py - LITE VERSION
def search_google(query): return f"Busqueda simulada: {query}"
def get_browser_player(): return None
def search_and_play(q, **k): return {'success': False, 'message': 'Browser disabled in Lite Mode'}
"""

CODE_SERVO = """#!/usr/bin/env python3
# module_servoctl.py - LITE VERSION
def set_servo_angle(pin, angle): pass
def cleanup(): pass
class ServoManager:
    def __init__(self): pass
    def move(self, x): pass
"""

CODE_IMOTIONS = """#!/usr/bin/env python3
# module_imotions.py - LITE VERSION
# Evita cargar OpenCV/DeepFace
def detect_emotion(img): return "neutral"
def analyze_face(img): return {}
"""

CODE_VISION = """#!/usr/bin/env python3
# module_vision.py - LITE VERSION
def describe_camera_view(): return "Vision disabled."
def describe_camera_view_openai(p): return "Vision disabled."
def capture_image(): return None
def initialize_camera(): pass
def initialize_blip(): pass
"""

CODE_STT = """#!/usr/bin/env python3
# module_stt.py - LITE VERSION
import threading, time
class STTManager:
    def __init__(self, c, s, u, g=1.0): self.running=False; self.s=s; self.u=u
    def start(self): 
        self.running=True
        threading.Thread(target=self._l, daemon=True).start()
    def _l(self):
        while self.running and not self.s.is_set(): time.sleep(1)
    def stop(self): self.running=False
    def set_wake_word_callback(self, c): pass
    def set_utterance_callback(self, c): pass
    def set_post_utterance_callback(self, c): pass
    def play_wav(self, f): pass
    def pause(self): pass
    def resume(self): pass
"""

CODE_TTS = """#!/usr/bin/env python3
# module_tts.py - LITE VERSION
import asyncio, os
from modules.module_messageQue import queue_message
try:
    from openai import OpenAI
except:
    OpenAI = None

async def play_audio_chunks(text, opt, wake=False):
    # Dummy o OpenAI simple
    if not text: return
    # print(f"TTS: {text}") # Descomentar para debug
    
def update_tts_settings(url): pass
"""

CODE_LLM = """#!/usr/bin/env python3
# module_llm.py - LITE VERSION
import os
try: from openai import OpenAI
except: OpenAI = None
from modules.module_config import load_config
CONFIG = load_config()
client = None
if OpenAI: 
    k = CONFIG['LLM'].get('api_key', os.environ.get('OPENAI_API_KEY'))
    if k: client = OpenAI(api_key=k)

def initialize_manager_llm(m, c): pass
def process_completion(text):
    if not client: return "Modo Lite. Configura OpenAI API Key."
    try:
        r = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"user","content":text}],
            max_tokens=100
        )
        return r.choices[0].message.content
    except Exception as e: return f"Error: {e}"
"""

# LISTA DE OBJETIVOS
targets = {
    "modules/module_memory.py": CODE_MEMORY,
    "modules/module_browser.py": CODE_BROWSER,
    "modules/module_servoctl.py": CODE_SERVO,
    "modules/module_imotions.py": CODE_IMOTIONS,
    "modules/module_vision.py": CODE_VISION,
    "modules/module_stt.py": CODE_STT,
    "modules/module_tts.py": CODE_TTS,
    "modules/module_llm.py": CODE_LLM
}

print("☢️  INICIANDO LIMPIEZA TOTAL DE MÓDULOS ☢️")
print("------------------------------------------")

for path, content in targets.items():
    print(f" -> Sanitizando {path}...", end="")
    try:
        with open(path, "w") as f:
            f.write(content)
        print(" [OK]")
    except Exception as e:
        print(f" [ERROR: {e}]")

print("------------------------------------------")
print("✅ LIMPIEZA COMPLETADA.")
print("Ahora ejecuta: python app.py")
