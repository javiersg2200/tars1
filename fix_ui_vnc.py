import os

ui_code = """#!/usr/bin/env python3
import os
import sys

# INTENTO DE ARREGLO PARA VNC
# Forzamos X11 puro y duro
os.environ["SDL_VIDEODRIVER"] = "x11"
# Desactivamos aceleración por hardware explícitamente
os.environ["SDL_ACCELERATION"] = "0"

import pygame
import threading
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
        self.headless_mode = False # Se activa si falla la pantalla
        self.status_text = "TARS ONLINE"
        
        try:
            pygame.init()
            info = pygame.display.Info()
            self.width = 600 # Tamaño fijo seguro para VNC
            self.height = 400
            
            # SIN FLAGS (flags=0) es lo más seguro para VNC
            self.screen = pygame.display.set_mode((self.width, self.height), 0)
            pygame.display.set_caption("TARS VNC Mode")
            self.font = pygame.font.Font(None, 40)
            print("UI: Pantalla iniciada en modo ventana (Safe VNC)")
            
        except Exception as e:
            print(f"UI ERROR AL INICIAR: {e}")
            print("UI: Cambiando a MODO TEXTO (Headless)")
            self.headless_mode = True

    def update_data(self, source, message, category="INFO"):
        self.status_text = message[:50]
        # Si no hay pantalla, lo imprimimos en la terminal
        if self.headless_mode:
            print(f"DISPLAY [{source}]: {message}")

    def run(self):
        if self.headless_mode:
            self._run_headless()
            return

        clock = pygame.time.Clock()
        
        while self.running and not self.shutdown_event.is_set():
            try:
                # EVENTOS
                for event in pygame.event.get():
                    if event.type == pygame.QUIT: self.shutdown_event.set()

                # DIBUJAR (Muy simple)
                self.screen.fill(BLUE_BG)
                
                # Bloques
                cx, cy = self.width // 2, self.height // 2
                pygame.draw.rect(self.screen, BLUE_BLOCK, (cx - 100, cy - 30, 60, 60))
                pygame.draw.rect(self.screen, BLUE_BLOCK, (cx - 30, cy - 30, 60, 60))
                pygame.draw.rect(self.screen, BLUE_BLOCK, (cx + 40, cy - 30, 60, 60))
                
                # Texto
                text = self.font.render(self.status_text, True, WHITE)
                self.screen.blit(text, (20, cy + 50))

                # ACTUALIZAR PANTALLA
                # Usamos update() en lugar de flip(), a veces es más compatible
                pygame.display.update()
                
                clock.tick(5) # Muy lento para no saturar VNC
                
            except Exception as e:
                print(f"CRASH GRÁFICO DETECTADO: {e}")
                print("UI: Desactivando gráficos, TARS sigue vivo en la terminal.")
                self.headless_mode = True
                pygame.quit()
                self._run_headless()
                break
        
        if not self.headless_mode:
            pygame.quit()

    def _run_headless(self):
        # Bucle tonto para mantener el hilo vivo si falla la pantalla
        while self.running and not self.shutdown_event.is_set():
            time.sleep(1)

    # Dummies
    def stop(self): self.running = False
    def deactivate_screensaver(self): pass
    def silence(self, x): pass
    def think(self): pass
    def pause(self): pass
    def resume(self): pass
"""

print("Escribiendo modules/module_ui.py a prueba de balas...")
with open("modules/module_ui.py", "w") as f:
    f.write(ui_code)
print("¡HECHO! Ahora TARS no morirá si falla la pantalla.")
