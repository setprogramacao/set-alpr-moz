"""
Services - Sistema ALPR UNIPIAGET
Camada de lógica de negócio
"""

from .auth_service import (
    verificar_senha,
    hash_senha,
    criar_token_acesso,
    verificar_token,
    autenticar_usuario,
)

from .deteccao_service import (
    processar_deteccao,
    verificar_duplicata,
    buscar_veiculo_por_placa,
    registrar_acesso,
    obter_ultimo_registro_veiculo,
)

__all__ = [
    # Auth
    "verificar_senha",
    "hash_senha",
    "criar_token_acesso",
    "verificar_token",
    "autenticar_usuario",
    # Detecção
    "processar_deteccao",
    "verificar_duplicata",
    "buscar_veiculo_por_placa",
    "registrar_acesso",
    "obter_ultimo_registro_veiculo",
]
