"""
Routes - Sistema ALPR UNIPIAGET
Endpoints da API REST
"""

from . import auth
from . import veiculos
from . import proprietarios
from . import registros
from . import dashboard
from . import relatorios

__all__ = [
    "auth",
    "veiculos",
    "proprietarios",
    "registros",
    "dashboard",
    "relatorios",
]
