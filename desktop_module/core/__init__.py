"""
Core Module - Desktop ALPR
Detecção, OCR, câmera e comunicação com API
"""

from .detector import PlateDetector
from .camera import CameraManager
from .api_client import APIClient
from .plc_controller import PLCController

__all__ = [
    "PlateDetector",
    "CameraManager",
    "APIClient",
    "PLCController",
]
