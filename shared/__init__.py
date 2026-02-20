"""
Módulo Shared - Sistema ALPR UNIPIAGET
Contém código compartilhado entre os módulos Desktop e Web
"""

from .schemas import (
    # Schemas de Proprietário
    ProprietarioBase,
    ProprietarioCreate,
    ProprietarioUpdate,
    ProprietarioResponse,

    # Schemas de Veículo
    VeiculoBase,
    VeiculoCreate,
    VeiculoUpdate,
    VeiculoResponse,
    VeiculoComProprietario,

    # Schemas de Registro de Acesso
    RegistroAcessoBase,
    RegistroAcessoCreate,
    RegistroAcessoResponse,
    RegistroAcessoDetalhado,

    # Schemas de Usuário
    UsuarioBase,
    UsuarioCreate,
    UsuarioUpdate,
    UsuarioResponse,

    # Schemas de Autenticação
    Token,
    TokenData,
    LoginRequest,

    # Schemas de Detecção
    DeteccaoRequest,
    DeteccaoResponse,
    ResultadoOCR,

    # Schemas de Relatórios
    FiltroRelatorio,
    RelatorioProprietario,
    RelatorioVeiculo,
    EstatisticasDashboard,
    VeiculoNoCampus,
    AlertaProprietario,

    # Schemas de Configuração
    ConfiguracaoBase,
    ConfiguracaoCreate,
    ConfiguracaoResponse,
)

from .utils import (
    validar_placa_mocambique,
    limpar_texto_ocr,
    corrigir_placa_ocr,
    preprocessar_imagem_placa,
    preprocessar_imagem_placa_cinza,
    adicionar_margem_placa,
    mesclar_resultados_ocr,
    salvar_imagem_deteccao,
    calcular_tempo_permanencia,
    formatar_tempo_permanencia,
    validar_email,
    validar_telefone_mocambique,
    gerar_nome_arquivo_imagem,
)

__version__ = "1.0.0"
__all__ = [
    # Schemas
    "ProprietarioBase",
    "ProprietarioCreate",
    "ProprietarioUpdate",
    "ProprietarioResponse",
    "VeiculoBase",
    "VeiculoCreate",
    "VeiculoUpdate",
    "VeiculoResponse",
    "VeiculoComProprietario",
    "RegistroAcessoBase",
    "RegistroAcessoCreate",
    "RegistroAcessoResponse",
    "RegistroAcessoDetalhado",
    "UsuarioBase",
    "UsuarioCreate",
    "UsuarioUpdate",
    "UsuarioResponse",
    "Token",
    "TokenData",
    "LoginRequest",
    "DeteccaoRequest",
    "DeteccaoResponse",
    "ResultadoOCR",
    "FiltroRelatorio",
    "RelatorioProprietario",
    "RelatorioVeiculo",
    "EstatisticasDashboard",
    "VeiculoNoCampus",
    "AlertaProprietario",
    "ConfiguracaoBase",
    "ConfiguracaoCreate",
    "ConfiguracaoResponse",
    # Utils
    "validar_placa_mocambique",
    "limpar_texto_ocr",
    "corrigir_placa_ocr",
    "preprocessar_imagem_placa",
    "preprocessar_imagem_placa_cinza",
    "adicionar_margem_placa",
    "mesclar_resultados_ocr",
    "salvar_imagem_deteccao",
    "calcular_tempo_permanencia",
    "formatar_tempo_permanencia",
    "validar_email",
    "validar_telefone_mocambique",
    "gerar_nome_arquivo_imagem",
]
