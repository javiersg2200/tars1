#!/usr/bin/env python3
import os
import sys

# --- PARCHES DE VIDEO PARA RASPBERRY PI 4 / VNC ---
# Forzamos el uso de X11 (el sistema de ventanas clásico) en lugar de Wayland
os.environ["SDL_VIDEODRIVER"] = "x11"
# Forzamos el renderizado por software (CPU) para evitar errores de GPU/OpenGL
os.environ["SDL_RENDER_DRIVER"] = "software"
# Centramos la ventana
os.environ["SDL_VIDEO_CENTERED"] = "1"

import pygame
import threading
import time

# Colores TARS
BLUE_BG = (10, 20, 40)
BLUE_BLOCK = (60, 90, 160)
BLUE_ACTIVE = (100, 150, 255)
WHITE = (200, 200, 200)

class UIManager(threading.Thread):
    def __init__(self, shutdown_event, battery_module=None, cpu_temp_module=None):
        super().__init__()
        self.shutdown_event = shutdown_event
        self.daemon = True
        self.running = True
        self.status_text = "TARS ONLINE"
        self.sub_text = "System Ready"
        self.is_speaking = False
        
        # Inicializar Pygame sin modos acelerados
        try:
            pygame.init()
            
            # Detectar tamaño de pantalla
            info = pygame.display.Info()
            self.width = info.current_w
            self.height = info.current_h
            
            # Crear ventana SIN MARCO (NOFRAME)
            # No usamos FULLSCREEN para evitar bloqueos en VNC
            self.screen = pygame.display.set_mode((self.width, self.height), pygame.NOFRAME)
            pygame.display.set_caption("TARS Mirror")
            
            # Fuente
            self.font = pygame.font.Font(None, 50)
            self.font_small = pygame.font.Font(None, 30)
            
        except Exception as e:
            print(f"CRITICAL UI ERROR: {e}")
            self.running = False

    def update_data(self, source, message, category="INFO"):
        self.status_text = message[:60]
        self.sub_text = f"[{source}]"
        
        if category == "TARS":
            self.is_speaking = True
            # Dejar de "hablar" visualmente tras 2 segundos
            threading.Timer(2.0, self._stop_speaking).start()

    def _stop_speaking(self):
        self.is_speaking = False

    def run(self):
        if not self.running: return
        
        clock = pygame.time.Clock()
        
        while self.running and not self.shutdown_event.is_set():
            # Procesar eventos (clics, teclas)
            for event in pygame.event.get():
                if event.type == pygame.QUIT: self.shutdown_event.set()
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE: self.shutdown_event.set()

            # 1. Limpiar pantalla
            self.screen.fill(BLUE_BG)
            
            # 2. Dibujar Bloques (Interfaz TARS)
            cx, cy = self.width // 2, self.height // 2
            
            # Color de los bloques (Brillan si habla)
            block_color = BLUE_ACTIVE if self.is_speaking else BLUE_BLOCK
            
            # Bloque Izq
            pygame.draw.rect(self.screen, block_color, (cx - 160, cy - 50, 100, 150), border_radius=5)
            # Bloque Centro
            pygame.draw.rect(self.screen, BLUE_BLOCK, (cx - 50, cy - 50, 100, 150), border_radius=5)
            # Bloque Der
            pygame.draw.rect(self.screen, block_color, (cx + 60, cy - 50, 100, 150), border_radius=5)
            
            # 3. Textos
            # Texto Principal (Centro)
            text_surf = self.font.render(self.status_text, True, WHITE)
            self.screen.blit(text_surf, (cx - text_surf.get_width()//2, cy - 100))
            
            # Texto Secundario (Esquina)
            sub_surf = self.font_small.render(self.sub_text, True, (100, 200, 100))
            self.screen.blit(sub_surf, (20, 20))

            # 4. Actualizar pantalla
            pygame.display.flip()
            
            # 5. Limitar FPS para no calentar la CPU
            clock.tick(10)

        pygame.quit()

    # Métodos dummy para compatibilidad
    def stop(self): self.running = False
    def deactivate_screensaver(self): pass
    def silence(self, x): pass
    def think(self): pass
    def pause(self): pass
    def resume(self): pass
