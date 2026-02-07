#!/usr/bin/env python3
"""
module_cputemp.py - Versión Lite
Lee la temperatura de la Raspberry Pi sin complicaciones.
"""

import os

class CPUTempModule:
    def __init__(self):
        self.running = False

    def get_temperature(self):
        """Devuelve la temperatura en grados Celsius."""
        try:
            # Ruta estándar en Raspberry Pi
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                temp_str = f.read().strip()
                return float(temp_str) / 1000.0
        except Exception:
            # Si falla (ej. en Windows), devuelve 0
            return 0.0

    def start(self):
        pass

    def stop(self):
        pass

# Funciones dummy para compatibilidad si module_main las llama
def set_cpu_temp_instance(inst): pass
def set_ventilate_callback(cb): pass
def start_thermal_monitoring(): pass
