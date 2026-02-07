import sys
print("--- INICIO DEL TEST DE DIAGNÓSTICO ---")

print("1. Probando numpy...")
import numpy
print(f"   > OK (Versión: {numpy.__version__})")

print("2. Probando sounddevice...")
import sounddevice
print("   > OK")

print("3. Probando soundfile...")
import soundfile
print("   > OK")

print("4. Probando openai...")
from openai import OpenAI
print("   > OK")

print("5. Probando onnxruntime (Culpable habitual)...")
try:
    import onnxruntime
    print("   > OK")
except ImportError:
    print("   > No instalado (Bien)")
except Exception as e:
    print(f"   > Error al importar: {e}")

print("6. Probando tokenizers/transformers (Culpable habitual)...")
try:
    import tokenizers
    print("   > OK")
except ImportError:
    print("   > No instalado")

print("7. Probando modules.module_config...")
try:
    from modules.module_config import load_config
    print("   > OK")
except Exception as e:
    print(f"   > FALLO en module_config: {e}")

print("8. Probando modules.module_tts...")
try:
    from modules.module_tts import update_tts_settings
    print("   > OK")
except Exception as e:
    print(f"   > FALLO en module_tts: {e}")

print("9. Probando modules.module_llm...")
try:
    from modules.module_llm import initialize_manager_llm
    print("   > OK")
except Exception as e:
    print(f"   > FALLO en module_llm: {e}")

print("--- FIN DEL TEST: SI LEES ESTO, EL ENTORNO ESTÁ SANO ---")
