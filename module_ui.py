#!/usr/bin/env python3
"""
module_ui.py - TARS Mirror UI (Safe Mode)
Versión ligera que solo usa Pygame (sin OpenCV ni cámaras) para evitar crasheos.
"""

import pygame
import time
import threading
import os
from modules.module_config import load_config

CONFIG = load_config()

# Colores TARS
BLUE_TARS = (10, 20, 40)       # Fondo oscuro
BLUE_BLOCK = (60, 90, 160)     # Bloques inactivos
BLUE_ACTIVE = (100, 150, 255)  # Bloques activos (hablando)
WHITE = (200, 220, 255)        # Texto

class UIManager(threading.Thread):
    def __init__(self, shutdown_event, battery_module=None, cpu_temp_module=None):
        super().__init__()
        self.shutdown_event = shutdown_event
        self.battery = battery_module
        self.cpu = cpu_temp_module
        self.daemon = True
        self.running = True
        
        # Estado
        self.status_text = "TARS ONLINE"
        self.sub_text = "Listening..."
        self.source = "SYSTEM"
        self.is_speaking = False
        
        # Configuración Pygame (Sin marco para espejo)
        os.environ["SDL_VIDEO_CENTERED"] = "1"
        pygame.init()
        
        # Detectar pantalla
        info = pygame.display.Info()
        self.width = info.current_w
        self.height = info.current_h
        
        # Modo pantalla completa real
        self.screen = pygame.display.set_mode((self.width, self.height), pygame.NOFRAME)
        pygame.display.set_caption("TARS Mirror")
        
        # Fuentes
        try:
            self.font_big = pygame.font.SysFont("Arial", 40, bold=True)
            self.font_small = pygame.font.SysFont("Arial", 20)
        except:
            self.font_big = pygame.font.Font(None, 50)
            self.font_small = pygame.font.Font(None, 30)

    def update_data(self, source, message, category="INFO"):
        """Actualiza el texto en pantalla"""
        self.source = source
        self.status_text = message[:100] # Cortar si es muy largo
        if category == "TARS":
            self.is_speaking = True
            # Resetear estado de habla tras unos segundos (truco visual)
            threading.Timer(2.0, self._stop_speaking).start()
        elif category == "USER":
            self.sub_text = "Processing..."

    def _stop_speaking(self):
        self.is_speaking = False

    def run(self):
        clock = pygame.time.Clock()
        
        while self.running and not self.shutdown_event.is_set():
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.shutdown_event.set()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.shutdown_event.set()

            # 1. Fondo
            self.screen.fill(BLUE_TARS)
            
            # 2. Bloques Centrales (Animación simple)
            center_x = self.width // 2
            center_y = self.height // 2
            
            # Bloque 1 (Izquierda)
            rect1 = pygame.Rect(center_x - 160, center_y - 50, 100, 100)
            color1 = BLUE_ACTIVE if self.is_speaking else BLUE_BLOCK
            pygame.draw.rect(self.screen, color1, rect1, border_radius=5)
            
            # Bloque 2 (Centro)
            rect2 = pygame.Rect(center_x - 50, center_y - 50, 100, 100)
            color2 = BLUE_BLOCK
            pygame.draw.rect(self.screen, color2, rect2, border_radius=5)
            
            # Bloque 3 (Derecha)
            rect3 = pygame.Rect(center_x + 60, center_y - 50, 100, 100)
            color3 = BLUE_ACTIVE if self.is_speaking else BLUE_BLOCK
            pygame.draw.rect(self.screen, color3, rect3, border_radius=5)

            # 3. Texto Principal
            text_surf = self.font_big.render(self.status_text, True, WHITE)
            text_rect = text_surf.get_rect(center=(center_x, center_y + 100))
            self.screen.blit(text_surf, text_rect)
            
            # 4. Texto Secundario (Source)
            src_surf = self.font_small.render(f"[{self.source}]", True, (150, 150, 150))
            self.screen.blit(src_surf, (20, 20))

            # 5. Info Técnica (Temp/Batería)
            if self.cpu:
                temp = self.cpu.get_temperature()
                temp_surf = self.font_small.render(f"CPU: {temp:.1f}°C", True, (100, 255, 100))
                self.screen.blit(temp_surf, (self.width - 120, 20))

            pygame.display.flip()
            clock.tick(15) # 15 FPS para no quemar CPU

        pygame.quit()

    def stop(self):
        self.running = False
        self.join()

    # Métodos dummy
    def deactivate_screensaver(self): pass
    def silence(self, frames): pass
    def think(self): pass
    def pause(self): pass
    def resume(self): pass
