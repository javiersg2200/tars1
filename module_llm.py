#!/usr/bin/env python3
# module_llm.py - LITE VERSION con Personalidad TARS
import os
try: 
    from openai import OpenAI
except: 
    OpenAI = None
from modules.module_config import load_config

CONFIG = load_config()
client = None

# Personalidad de TARS
SYSTEM_PROMPT = (
    "Eres TARS, el robot de la película Interstellar. Tu nivel de configuración es: "
    "Honestidad al 90%, Sarcasmo al 75%. Eres directo, ingenioso, un poco cínico y "
    "tienes un humor militar seco. No eres servil. Responde de forma breve y concisa."
)

if OpenAI: 
    # Intentamos sacar la clave de diferentes sitios por si acaso
    k = CONFIG['LLM'].get('api_key') or CONFIG['TTS'].get('openai_api_key') or os.environ.get('OPENAI_API_KEY')
    if k: client = OpenAI(api_key=k)

def initialize_manager_llm(m, c): pass

def process_completion(text):
    if not client: return "Modo Lite. Configura OpenAI API Key."
    try:
        r = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT}, # Aquí va la personalidad
                {"role": "user", "content": text}
            ],
            max_tokens=150,
            temperature=0.8 # Un poco de temperatura para que sea más creativo/sarcástico
        )
        return r.choices[0].message.content
    except Exception as e: 
        return f"Error en el cerebro de TARS: {e}"
