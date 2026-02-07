#!/usr/bin/env python3
"""
module_vision.py - Versión Lite (Safe Mode) para Raspberry Pi 4
Eliminadas dependencias de Torch y Transformers para evitar 'Illegal Instruction'.
Mantiene la estructura para evitar errores de importación.
"""

from modules.module_messageQue import queue_message

# Variables globales dummy
PROCESSOR = None
MODEL = None
CAMERA = None

def initialize_camera():
    """Dummy initialization"""
    queue_message("INFO: Camera disabled in Lite Mode.")

def initialize_blip():
    """Dummy initialization"""
    pass

def capture_image() -> str:
    """Dummy capture"""
    return ""

def describe_camera_view() -> str:
    return "I cannot see. Vision module is disabled on Pi 4."

def describe_camera_view_openai(user_prompt) -> str:
    return "Vision is disabled. Please check configuration."

def send_image_to_server(image_path: str) -> str:
    return "Server vision disabled."

def get_image_caption_from_base64(base64_str):
    return "Captioning disabled."

def save_captured_image(image_path: str) -> str:
    return ""

# Evitamos que module_main falle si intenta importar algo más
class VisionManager:
    def __init__(self, *args, **kwargs): pass
