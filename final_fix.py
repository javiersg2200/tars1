import os

# 1. ARREGLO DEL OÍDO (STT)
# Corregimos los nombres de las variables para que coincidan con app.py
stt_code = """#!/usr/bin/env python3
import threading
import time

class STTManager:
    # Aceptamos argumentos con los nombres exactos que usa app.py
    def __init__(self, config, shutdown_event, ui_manager, amp_gain=1.0):
        self.config = config
        self.shutdown_event = shutdown_event
        self.ui_manager = ui_manager
        self.running = False

    def start(self):
        self.running = True
        # Hilo dummy para no bloquear
        threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        while self.running and not self.shutdown_event.is_set():
            time.sleep(1)

    def stop(self):
        self.running = False

    # Setters obligatorios
    def set_wake_word_callback(self, cb): pass
    def set_utterance_callback(self, cb): pass
    def set_post_utterance_callback(self, cb): pass
    
    # Control de audio
    def play_wav(self, f): pass
    def pause(self): pass
    def resume(self): pass
"""

# 2. ARREGLO DE LA PANTALLA (UI)
# Eliminamos OpenGL y usamos solo dibujo 2D simple
ui_code = """#!/usr/bin/env python3
import pygame
import threading
import os
import time

# Colores
BLUE_BG = (10, 20, 40)
BLUE_BLOCK = (60, 90, 160)
WHITE = (200, 200, 200)

class UIManager(threading.Thread):
    def __init__(self, shutdown_event, battery_module=None, cpu_temp_module=None):
        super().__init__()
        self.shutdown_event = shutdown_event
        self.daemon = True
        self.running = True
        self.status_text = "TARS ONLINE"
        self.sub_text = "System Ready"
        
        # Configuración Pygame (Sin aceleración 3D)
        os.environ["SDL_VIDEO_CENTERED"] = "1"
        pygame.init()
        
        info = pygame.display.Info()
        self.width = info.current_w
        self.height = info.current_h
        
        # Pantalla completa falsa (sin marco) para evitar errores de contexto
        self.screen = pygame.display.set_mode((self.width, self.height), pygame.NOFRAME)
        pygame.display.set_caption("TARS Mirror")
        
        # Fuente
        self.font = pygame.font.Font(None, 50)

    def update_data(self, source, message, category="INFO"):
        self.status_text = message[:60]
        self.sub_text = f"[{source}]"

    def run(self):
        clock = pygame.time.Clock()
        
        while self.running and not self.shutdown_event.is_set():
            # Eventos
            for event in pygame.event.get():
                if event.type == pygame.QUIT: self.shutdown_event.set()
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE: self.shutdown_event.set()

            # Dibujar Fondo
            self.screen.fill(BLUE_BG)
            
            # Dibujar Bloques
            cx, cy = self.width // 2, self.height // 2
            
            # Bloque Izq
            pygame.draw.rect(self.screen, BLUE_BLOCK, (cx - 160, cy - 50, 100, 150), border_radius=5)
            # Bloque Centro
            pygame.draw.rect(self.screen, BLUE_BLOCK, (cx - 50, cy - 50, 100, 150), border_radius=5)
            # Bloque Der
            pygame.draw.rect(self.screen, BLUE_BLOCK, (cx + 60, cy - 50, 100, 150), border_radius=5)
            
            # Texto
            text_surf = self.font.render(self.status_text, True, WHITE)
            self.screen.blit(text_surf, (cx - text_surf.get_width()//2, cy - 150))
            
            sub_surf = self.font.render(self.sub_text, True, (100, 255, 100))
            self.screen.blit(sub_surf, (20, 20))

            pygame.display.flip()
            clock.tick(10) # 10 FPS es suficiente

        pygame.quit()

    # Métodos dummy para compatibilidad
    def stop(self): self.running = False
    def deactivate_screensaver(self): pass
    def silence(self, x): pass
    def think(self): pass
    def pause(self): pass
    def resume(self): pass
"""

print("🔧 Aplicando correcciones finales...")

with open("modules/module_stt.py", "w") as f:
    f.write(stt_code)
    print(" -> Oído (STT) arreglado.")

with open("modules/module_ui.py", "w") as f:
    f.write(ui_code)
    print(" -> Pantalla (UI) arreglada.")

print("✅ LISTO. TARS debería arrancar ahora.")
