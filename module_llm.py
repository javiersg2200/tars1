#!/usr/bin/env python3
"""
module_llm.py - Versión Lite (Cloud Only) para Raspberry Pi 4
Eliminadas dependencias de 'transformers' y 'vision' para evitar 'Illegal Instruction'.
"""

import os
import json
import requests
from modules.module_messageQue import queue_message
from modules.module_config import load_config

# Intentamos importar OpenAI
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

CONFIG = load_config()
memory_manager = None
character_manager = None
client = None

def initialize_manager_llm(mem_mgr, char_mgr):
    """Inicializa el gestor LLM solo con OpenAI."""
    global memory_manager, character_manager, client
    memory_manager = mem_mgr
    character_manager = char_mgr
    
    api_key = CONFIG['LLM'].get('api_key', os.environ.get("OPENAI_API_KEY"))
    
    # Configuración simplificada para OpenAI
    if OpenAI and api_key and "sk-" in api_key:
        try:
            client = OpenAI(api_key=api_key)
            queue_message("LOAD: Cerebro Cloud (OpenAI) conectado.")
        except Exception as e:
            queue_message(f"WARNING: Error conectando OpenAI: {e}")
    else:
        queue_message("WARNING: No se encontró API Key válida. TARS usará modo dummy.")

def process_completion(user_input):
    """Procesa la respuesta usando SOLO la nube."""
    global client
    
    if not user_input:
        return ""

    # 1. Recuperar contexto básico
    context = ""
    system_prompt = "You are TARS. Helpful, sarcastic, and efficient."
    
    if character_manager:
        # Intentamos obtener el prompt del personaje si existe el método
        try:
            system_prompt = character_manager.get_system_prompt()
        except:
            pass

    if memory_manager:
        try:
            # Intentamos obtener memoria si existe el método
            # En modo Lite a veces es por keywords
            context = memory_manager.get_context(user_input)
        except:
            context = ""

    # 2. Construir mensajes
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Contexto previo: {context}\n\nUsuario dice: {user_input}"}
    ]

    # 3. Generar respuesta
    if client:
        try:
            completion = client.chat.completions.create(
                model=CONFIG['LLM'].get('openai_model', 'gpt-4o-mini'),
                messages=messages,
                max_tokens=150,
                temperature=0.7
            )
            reply = completion.choices[0].message.content
            return reply
        except Exception as e:
            queue_message(f"ERROR LLM: {e}")
            return "Mis sistemas de lógica están fallando. Revisa mi conexión."
    
    # Fallback si no hay cliente (para que no crashee)
    return "Modo offline. No puedo procesar tu solicitud sin una API Key válida."

# Funciones dummy para compatibilidad
def detect_emotion(text): pass
