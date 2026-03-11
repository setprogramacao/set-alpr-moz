"""
Schemas Pydantic - Sistema ALPR UNIPIAGET
Define todos os modelos de dados para validação e serialização
"""

from datetime import datetime
from typing import Optional, List, Literal
from pydantic import BaseModel, EmailStr, Field, field_validator
import re


# ============================================================================
# SCHEMAS DE PROPRIETÁRIO
# ============================================================================

class ProprietarioBase(BaseModel):
    """Schema base para Proprietário"""
    nome: str = Field(..., min_length=3, max_length=150, description="Nome completo do proprietário")
    categoria: Literal["docente", "tecnico", "visitante", "aluno"] = Field(..., description="Categoria do proprietário")
    departamento: Optional[str] = Field(None, max_length=100, description="Departamento/Faculdade")
    telefone: Optional[str] = Field(None, max_length=20, description="Número de telefone")
    email: Optional[EmailStr] = Field(None, description="Email do proprietário")

    @field_validator("telefone")
    @classmethod
    def validar_telefone(cls, v: Optional[str]) -> Optional[str]:
        """Valida formato de telefone moçambicano"""
        if v is None:
            return v
        # Remove espaços e caracteres especiais
        telefone_limpo = re.sub(r'[^\d+]', '', v)
        # Aceita formatos: +258XXXXXXXXX, 258XXXXXXXXX, 8XXXXXXXX, 2XXXXXXXX
        if not re.match(r'^(\+?258)?[28]\d{8}$', telefone_limpo):
            raise ValueError("Telefone inválido. Use formato moçambicano: +258XXXXXXXXX ou 8XXXXXXXX")
        return telefone_limpo


class ProprietarioCreate(ProprietarioBase):
    """Schema para criar proprietário"""
    pass


class ProprietarioUpdate(BaseModel):
    """Schema para atualizar proprietário"""
    nome: Optional[str] = Field(None, min_length=3, max_length=150)
    categoria: Optional[Literal["docente", "tecnico", "visitante", "aluno"]] = None
    departamento: Optional[str] = Field(None, max_length=100)
    telefone: Optional[str] = Field(None, max_length=20)
    email: Optional[EmailStr] = None
    ativo: Optional[bool] = None


class ProprietarioResponse(ProprietarioBase):
    """Schema de resposta para Proprietário"""
    id: int
    ativo: bool
    data_cadastro: datetime

    class Config:
        from_attributes = True


# ============================================================================
# SCHEMAS DE VEÍCULO
# ============================================================================

class VeiculoBase(BaseModel):
    """Schema base para Veículo"""
    placa: str = Field(..., min_length=7, max_length=10, description="Placa do veículo")
    modelo: Optional[str] = Field(None, max_length=100, description="Modelo do veículo")
    cor: Optional[str] = Field(None, max_length=50, description="Cor do veículo")
    proprietario_id: int = Field(..., gt=0, description="ID do proprietário")
    observacoes: Optional[str] = Field(None, max_length=500, description="Observações sobre o veículo")

    @field_validator("placa")
    @classmethod
    def validar_placa(cls, v: str) -> str:
        """
        Valida e corrige formato de placa moçambicana.

        Formato: XXX000XX (3 letras + 3 números + 2 letras)
        Exemplos: MPM123AB, AAA456CD, LMX789ZY
        """
        from shared.utils import corrigir_placa_ocr

        # Limpa e converte para maiúscula
        placa_limpa = v.upper().replace("-", "").replace(" ", "")

        # Aplica correção OCR inteligente
        placa_corrigida = corrigir_placa_ocr(placa_limpa)

        # Valida formato final: XXX000XX (3 letras + 3 números + 2 letras)
        if not re.match(r'^[A-Z]{3}\d{3}[A-Z]{2}$', placa_corrigida):
            raise ValueError(
                f"Placa inválida: '{v}'. Use formato moçambicano XXX000XX "
                f"(3 letras + 3 números + 2 letras). Exemplo: MPM123AB"
            )

        return placa_corrigida


class VeiculoCreate(VeiculoBase):
    """Schema para criar veículo"""
    pass


class VeiculoUpdate(BaseModel):
    """Schema para atualizar veículo"""
    placa: Optional[str] = Field(None, min_length=7, max_length=10)
    modelo: Optional[str] = Field(None, max_length=100)
    cor: Optional[str] = Field(None, max_length=50)
    proprietario_id: Optional[int] = Field(None, gt=0)
    observacoes: Optional[str] = Field(None, max_length=500)


class VeiculoResponse(VeiculoBase):
    """Schema de resposta para Veículo"""
    id: int
    data_cadastro: datetime

    class Config:
        from_attributes = True


class VeiculoComProprietario(VeiculoResponse):
    """Schema de Veículo com dados do Proprietário"""
    proprietario: ProprietarioResponse

    class Config:
        from_attributes = True


# ============================================================================
# SCHEMAS DE REGISTRO DE ACESSO
# ============================================================================

class RegistroAcessoBase(BaseModel):
    """Schema base para Registro de Acesso"""
    placa_detectada: str = Field(..., min_length=7, max_length=10, description="Placa detectada pelo sistema")
    tipo_movimento: Literal["entrada", "saida"] = Field(..., description="Tipo de movimento: entrada ou saída")
    confianca_ocr: float = Field(..., ge=0.0, le=1.0, description="Confiança do OCR (0.0 a 1.0)")
    metodo_ocr: Literal["easyocr", "tesseract", "hibrido"] = Field(..., description="Método OCR utilizado")
    imagem_path: Optional[str] = Field(None, max_length=500, description="Caminho da imagem capturada")


class RegistroAcessoCreate(RegistroAcessoBase):
    """Schema para criar registro de acesso"""
    veiculo_id: Optional[int] = Field(None, description="ID do veículo (se cadastrado)")


class RegistradoPorInfo(BaseModel):
    """Informação resumida do usuário que registou manualmente"""
    id: int
    username: str
    nome_completo: str

    class Config:
        from_attributes = True


class RegistroAcessoResponse(RegistroAcessoBase):
    """Schema de resposta para Registro de Acesso"""
    id: int
    veiculo_id: Optional[int]
    data_hora: datetime
    # Sobrescreve os campos do base para permitir null em registros manuais
    confianca_ocr: Optional[float] = None
    metodo_ocr: Optional[str] = None
    origem: str = "automatico"
    observacoes: Optional[str] = None

    class Config:
        from_attributes = True


class RegistroAcessoDetalhado(RegistroAcessoResponse):
    """Schema de Registro com dados completos do Veículo e Proprietário"""
    veiculo: Optional[VeiculoComProprietario] = None
    registrado_por: Optional[RegistradoPorInfo] = None

    class Config:
        from_attributes = True


# ============================================================================
# SCHEMAS DE REGISTRO MANUAL
# ============================================================================

class RegistroManualCreate(BaseModel):
    """Schema para criar registro manual de acesso"""
    placa_detectada: str = Field(..., min_length=7, max_length=10, description="Placa do veículo")
    tipo_movimento: Literal["entrada", "saida"] = Field(..., description="Tipo de movimento")
    data_hora: Optional[datetime] = Field(None, description="Data/hora do evento (padrão: agora)")
    observacoes: Optional[str] = Field(None, max_length=500, description="Observações sobre o registro")

    @field_validator("placa_detectada")
    @classmethod
    def normalizar_placa(cls, v: str) -> str:
        return v.upper().replace("-", "").replace(" ", "")


class RegistroManualUpdate(BaseModel):
    """Schema para editar registro manual de acesso"""
    placa_detectada: Optional[str] = Field(None, min_length=7, max_length=10)
    tipo_movimento: Optional[Literal["entrada", "saida"]] = None
    data_hora: Optional[datetime] = None
    observacoes: Optional[str] = Field(None, max_length=500)

    @field_validator("placa_detectada")
    @classmethod
    def normalizar_placa(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return v.upper().replace("-", "").replace(" ", "")


# ============================================================================
# SCHEMAS DE USUÁRIO
# ============================================================================

class UsuarioBase(BaseModel):
    """Schema base para Usuário"""
    username: str = Field(..., min_length=3, max_length=50, description="Nome de usuário")
    email: EmailStr = Field(..., description="Email do usuário")
    nome_completo: str = Field(..., min_length=3, max_length=150, description="Nome completo")
    nivel_acesso: Literal["admin", "operador", "visualizador"] = Field(..., description="Nível de acesso")

    @field_validator("username")
    @classmethod
    def validar_username(cls, v: str) -> str:
        """Valida username (apenas letras, números e underscore)"""
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError("Username deve conter apenas letras, números e underscore")
        return v.lower()


class UsuarioCreate(UsuarioBase):
    """Schema para criar usuário"""
    senha: str = Field(..., min_length=8, max_length=100, description="Senha do usuário")

    @field_validator("senha")
    @classmethod
    def validar_senha(cls, v: str) -> str:
        """Valida força da senha"""
        if len(v) < 8:
            raise ValueError("Senha deve ter no mínimo 8 caracteres")
        if not re.search(r'[A-Z]', v):
            raise ValueError("Senha deve conter pelo menos uma letra maiúscula")
        if not re.search(r'[a-z]', v):
            raise ValueError("Senha deve conter pelo menos uma letra minúscula")
        if not re.search(r'\d', v):
            raise ValueError("Senha deve conter pelo menos um número")
        return v


class UsuarioUpdate(BaseModel):
    """Schema para atualizar usuário"""
    email: Optional[EmailStr] = None
    nome_completo: Optional[str] = Field(None, min_length=3, max_length=150)
    nivel_acesso: Optional[Literal["admin", "operador", "visualizador"]] = None
    ativo: Optional[bool] = None
    senha: Optional[str] = Field(None, min_length=8, max_length=100)


class UsuarioResponse(UsuarioBase):
    """Schema de resposta para Usuário"""
    id: int
    ativo: bool
    data_cadastro: datetime

    class Config:
        from_attributes = True


# ============================================================================
# SCHEMAS DE AUTENTICAÇÃO
# ============================================================================

class LoginRequest(BaseModel):
    """Schema para requisição de login"""
    username: str = Field(..., description="Nome de usuário ou email")
    senha: str = Field(..., description="Senha do usuário")


class Token(BaseModel):
    """Schema para token JWT"""
    access_token: str = Field(..., description="Token de acesso JWT")
    token_type: str = Field(default="bearer", description="Tipo do token")
    usuario: UsuarioResponse = Field(..., description="Dados do usuário autenticado")


class TokenData(BaseModel):
    """Schema para dados decodificados do token"""
    username: Optional[str] = None
    user_id: Optional[int] = None
    nivel_acesso: Optional[str] = None


# ============================================================================
# SCHEMAS DE DETECÇÃO (COMUNICAÇÃO DESKTOP → API)
# ============================================================================

class ResultadoOCR(BaseModel):
    """Schema para resultado de OCR individual"""
    texto: str = Field(..., description="Texto detectado")
    confianca: float = Field(..., ge=0.0, le=1.0, description="Confiança da detecção")
    metodo: Literal["easyocr", "tesseract"] = Field(..., description="Método utilizado")
    coordenadas: Optional[List[List[int]]] = Field(None, description="Coordenadas do bounding box")


class DeteccaoRequest(BaseModel):
    """Schema para enviar detecção do Desktop para API"""
    placa_detectada: str = Field(..., min_length=7, max_length=10, description="Placa detectada")
    tipo_movimento: Literal["entrada", "saida"] = Field(..., description="Tipo de movimento")
    confianca_ocr: float = Field(..., ge=0.0, le=1.0, description="Confiança final do OCR")
    metodo_ocr: Literal["easyocr", "tesseract", "hibrido"] = Field(..., description="Método OCR usado")
    imagem_base64: Optional[str] = Field(None, description="Imagem codificada em base64")
    resultados_ocr: Optional[List[ResultadoOCR]] = Field(None, description="Detalhes de todos resultados OCR")
    timestamp: Optional[datetime] = Field(default_factory=datetime.now, description="Timestamp da detecção")

    @field_validator("placa_detectada")
    @classmethod
    def validar_placa_detectada(cls, v: str) -> str:
        """Limpa e valida placa"""
        return v.upper().replace("-", "").replace(" ", "")


class DeteccaoResponse(BaseModel):
    """Schema de resposta para detecção"""
    sucesso: bool = Field(..., description="Indica se a detecção foi processada com sucesso")
    mensagem: str = Field(..., description="Mensagem de feedback")
    registro_id: Optional[int] = Field(None, description="ID do registro criado")
    veiculo_cadastrado: bool = Field(..., description="Indica se o veículo está cadastrado")
    veiculo: Optional[VeiculoComProprietario] = Field(None, description="Dados do veículo (se cadastrado)")
    duplicata: bool = Field(default=False, description="Indica se é registro duplicado (< 5 min)")
    tempo_desde_ultimo_registro: Optional[int] = Field(None, description="Tempo desde último registro (segundos)")


# ============================================================================
# SCHEMAS DE RELATÓRIOS
# ============================================================================

class FiltroRelatorio(BaseModel):
    """Schema para filtros de relatórios"""
    data_inicio: Optional[datetime] = Field(None, description="Data de início do período")
    data_fim: Optional[datetime] = Field(None, description="Data de fim do período")
    proprietario_id: Optional[int] = Field(None, gt=0, description="Filtrar por proprietário")
    veiculo_id: Optional[int] = Field(None, gt=0, description="Filtrar por veículo")
    categoria: Optional[Literal["docente", "tecnico", "visitante", "aluno"]] = Field(None, description="Filtrar por categoria")
    tipo_movimento: Optional[Literal["entrada", "saida"]] = Field(None, description="Filtrar por tipo de movimento")
    departamento: Optional[str] = Field(None, description="Filtrar por departamento")


class RelatorioProprietario(BaseModel):
    """Schema para relatório de proprietário"""
    proprietario: ProprietarioResponse
    total_entradas: int = Field(..., ge=0, description="Total de entradas no período")
    total_saidas: int = Field(..., ge=0, description="Total de saídas no período")
    tempo_total_permanencia: int = Field(..., ge=0, description="Tempo total em minutos")
    tempo_medio_permanencia: float = Field(..., ge=0.0, description="Tempo médio em minutos")
    dias_presentes: int = Field(..., ge=0, description="Número de dias presentes")
    ultima_entrada: Optional[datetime] = Field(None, description="Data/hora da última entrada")
    ultima_saida: Optional[datetime] = Field(None, description="Data/hora da última saída")
    veiculos_utilizados: List[VeiculoResponse] = Field(default_factory=list, description="Veículos utilizados")


class RelatorioVeiculo(BaseModel):
    """Schema para relatório de veículo"""
    veiculo: VeiculoComProprietario
    total_acessos: int = Field(..., ge=0, description="Total de acessos")
    total_entradas: int = Field(..., ge=0, description="Total de entradas")
    total_saidas: int = Field(..., ge=0, description="Total de saídas")
    primeira_deteccao: Optional[datetime] = Field(None, description="Primeira detecção")
    ultima_deteccao: Optional[datetime] = Field(None, description="Última detecção")
    confianca_media: float = Field(..., ge=0.0, le=1.0, description="Confiança média OCR")


# ============================================================================
# SCHEMAS DE DASHBOARD
# ============================================================================

class EstatisticasDashboard(BaseModel):
    """Schema para estatísticas do dashboard"""
    total_veiculos_cadastrados: int = Field(..., ge=0, description="Total de veículos cadastrados")
    total_proprietarios: int = Field(..., ge=0, description="Total de proprietários")
    total_registros_hoje: int = Field(..., ge=0, description="Total de registros hoje")
    total_registros_mes: int = Field(..., ge=0, description="Total de registros no mês")
    veiculos_no_campus: int = Field(..., ge=0, description="Veículos atualmente no campus")
    entradas_hoje: int = Field(..., ge=0, description="Entradas hoje")
    saidas_hoje: int = Field(..., ge=0, description="Saídas hoje")
    taxa_ocupacao: float = Field(..., ge=0.0, le=100.0, description="Taxa de ocupação (%)")
    registros_por_categoria: dict = Field(default_factory=dict, description="Registros por categoria")
    registros_por_hora: List[dict] = Field(default_factory=list, description="Registros por hora do dia")


class VeiculoNoCampus(BaseModel):
    """Schema para veículo atualmente no campus"""
    veiculo: VeiculoComProprietario
    hora_entrada: datetime = Field(..., description="Hora da entrada")
    tempo_permanencia: int = Field(..., ge=0, description="Tempo de permanência em minutos")
    tempo_formatado: str = Field(..., description="Tempo formatado (ex: 2h 30min)")


class AlertaProprietario(BaseModel):
    """Schema para alertas de proprietários"""
    proprietario: ProprietarioResponse
    veiculo: VeiculoResponse
    tipo_alerta: Literal["ausencia_prolongada", "saida_precoce", "entrada_tardia", "permanencia_curta"] = Field(
        ..., description="Tipo do alerta"
    )
    descricao: str = Field(..., description="Descrição do alerta")
    data_hora: datetime = Field(..., description="Data/hora do evento")
    severidade: Literal["baixa", "media", "alta"] = Field(..., description="Severidade do alerta")


# ============================================================================
# SCHEMAS DE CONFIGURAÇÃO
# ============================================================================

class ConfiguracaoBase(BaseModel):
    """Schema base para Configuração"""
    chave: str = Field(..., min_length=1, max_length=100, description="Chave da configuração")
    valor: str = Field(..., description="Valor da configuração")
    tipo: Literal["string", "integer", "float", "boolean", "json"] = Field(..., description="Tipo do valor")
    descricao: Optional[str] = Field(None, max_length=500, description="Descrição da configuração")


class ConfiguracaoCreate(ConfiguracaoBase):
    """Schema para criar configuração"""
    pass


class ConfiguracaoResponse(ConfiguracaoBase):
    """Schema de resposta para Configuração"""
    id: int

    class Config:
        from_attributes = True


# ============================================================================
# SCHEMAS AUXILIARES
# ============================================================================

class MessageResponse(BaseModel):
    """Schema genérico para respostas de mensagem"""
    mensagem: str
    sucesso: bool = True


class ErrorResponse(BaseModel):
    """Schema para respostas de erro"""
    erro: str
    detalhes: Optional[str] = None
    codigo: Optional[str] = None


class PaginationParams(BaseModel):
    """Schema para parâmetros de paginação"""
    pagina: int = Field(default=1, ge=1, description="Número da página")
    itens_por_pagina: int = Field(default=50, ge=1, le=100, description="Itens por página")


class PaginatedResponse(BaseModel):
    """Schema genérico para respostas paginadas"""
    itens: List[dict] = Field(default_factory=list, description="Lista de itens")
    total: int = Field(..., ge=0, description="Total de itens")
    pagina: int = Field(..., ge=1, description="Página atual")
    total_paginas: int = Field(..., ge=0, description="Total de páginas")
    itens_por_pagina: int = Field(..., ge=1, description="Itens por página")
