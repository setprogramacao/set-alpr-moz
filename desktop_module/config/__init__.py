"""
Config module - Desktop ALPR
"""

from .settings import *

__all__ = [
    "API_HOST",
    "API_BASE_URL",
    "API_DETECCAO_ENDPOINT",
    "YOLO_MODEL_PATH",
    "YOLO_CONFIDENCE_THRESHOLD",
    "OCR_METHOD",
    "OCR_MIN_CONFIDENCE",
    "VIDEO_SOURCE",
    "DETECTION_COOLDOWN",
    "SAVE_DETECTION_IMAGES",
    # PLC / Cancela
    "PLC_HABILITADO",
    "PLC_HOST",
    "PLC_PORT",
    "PLC_TIMEOUT",
    "PLC_COIL_CANCELA",
    "PLC_INPUT_LACO",
    "BARREIRA_TIMEOUT_SEGUNDOS",
    "BARREIRA_CONFIANCA_MINIMA",
    "validar_configuracoes",
    "obter_config_display",
]
