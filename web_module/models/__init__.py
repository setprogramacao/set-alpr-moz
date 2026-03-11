"""
Modelos SQLAlchemy - Sistema ALPR UNIPIAGET
Define todas as tabelas do banco de dados
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
from datetime import datetime

# Base para todos os modelos
Base = declarative_base()


# ============================================================================
# MODELO: PROPRIETÁRIOS
# ============================================================================

class Proprietario(Base):
    """
    Tabela de proprietários de veículos (docentes, técnicos, visitantes, alunos)
    """
    __tablename__ = "proprietarios"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nome = Column(String(150), nullable=False, index=True)
    categoria = Column(String(20), nullable=False, index=True)  # docente, tecnico, visitante, aluno
    departamento = Column(String(100), nullable=True, index=True)
    telefone = Column(String(20), nullable=True)
    email = Column(String(100), nullable=True, unique=True)
    ativo = Column(Boolean, default=True, nullable=False, index=True)
    data_cadastro = Column(DateTime, default=func.now(), nullable=False)

    # Relacionamentos
    veiculos = relationship("Veiculo", back_populates="proprietario", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Proprietario(id={self.id}, nome='{self.nome}', categoria='{self.categoria}')>"


# ============================================================================
# MODELO: VEÍCULOS
# ============================================================================

class Veiculo(Base):
    """
    Tabela de veículos cadastrados
    """
    __tablename__ = "veiculos"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    placa = Column(String(10), nullable=False, unique=True, index=True)
    modelo = Column(String(100), nullable=True)
    cor = Column(String(50), nullable=True)
    proprietario_id = Column(Integer, ForeignKey("proprietarios.id", ondelete="CASCADE"), nullable=False, index=True)
    observacoes = Column(String(500), nullable=True)
    data_cadastro = Column(DateTime, default=func.now(), nullable=False)

    # Relacionamentos
    proprietario = relationship("Proprietario", back_populates="veiculos")
    registros_acesso = relationship("RegistroAcesso", back_populates="veiculo", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Veiculo(id={self.id}, placa='{self.placa}', proprietario_id={self.proprietario_id})>"


# ============================================================================
# MODELO: REGISTROS DE ACESSO
# ============================================================================

class RegistroAcesso(Base):
    """
    Tabela de registros de entrada/saída de veículos
    """
    __tablename__ = "registros_acesso"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    veiculo_id = Column(Integer, ForeignKey("veiculos.id", ondelete="SET NULL"), nullable=True, index=True)
    placa_detectada = Column(String(10), nullable=False, index=True)
    tipo_movimento = Column(String(10), nullable=False, index=True)  # entrada, saida
    data_hora = Column(DateTime, default=func.now(), nullable=False, index=True)
    confianca_ocr = Column(Float, nullable=True)
    metodo_ocr = Column(String(20), nullable=True)  # easyocr, tesseract, hibrido, None (manual)
    imagem_path = Column(String(500), nullable=True)
    origem = Column(String(10), nullable=False, default="automatico")  # automatico, manual
    registrado_por_id = Column(Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True, index=True)
    observacoes = Column(String(500), nullable=True)

    # Relacionamentos
    veiculo = relationship("Veiculo", back_populates="registros_acesso")
    registrado_por = relationship("Usuario", foreign_keys=[registrado_por_id])

    def __repr__(self):
        return f"<RegistroAcesso(id={self.id}, placa='{self.placa_detectada}', tipo='{self.tipo_movimento}', data_hora='{self.data_hora}')>"


# ============================================================================
# MODELO: USUÁRIOS
# ============================================================================

class Usuario(Base):
    """
    Tabela de usuários do sistema web
    """
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), nullable=False, unique=True, index=True)
    email = Column(String(100), nullable=False, unique=True, index=True)
    nome_completo = Column(String(150), nullable=False)
    senha_hash = Column(String(255), nullable=False)
    nivel_acesso = Column(String(20), nullable=False, index=True)  # admin, operador, visualizador
    ativo = Column(Boolean, default=True, nullable=False, index=True)
    data_cadastro = Column(DateTime, default=func.now(), nullable=False)

    # Relacionamentos
    logs_auditoria = relationship("LogAuditoria", back_populates="usuario", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Usuario(id={self.id}, username='{self.username}', nivel='{self.nivel_acesso}')>"


# ============================================================================
# MODELO: CONFIGURAÇÕES
# ============================================================================

class Configuracao(Base):
    """
    Tabela de configurações do sistema
    """
    __tablename__ = "configuracoes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    chave = Column(String(100), nullable=False, unique=True, index=True)
    valor = Column(Text, nullable=False)
    tipo = Column(String(20), nullable=False)  # string, integer, float, boolean, json
    descricao = Column(String(500), nullable=True)

    def __repr__(self):
        return f"<Configuracao(chave='{self.chave}', valor='{self.valor}')>"


# ============================================================================
# MODELO: LOGS DE AUDITORIA
# ============================================================================

class LogAuditoria(Base):
    """
    Tabela de logs de auditoria (ações de usuários)
    """
    __tablename__ = "logs_auditoria"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True, index=True)
    acao = Column(String(100), nullable=False, index=True)
    detalhes = Column(Text, nullable=True)
    data_hora = Column(DateTime, default=func.now(), nullable=False, index=True)

    # Relacionamentos
    usuario = relationship("Usuario", back_populates="logs_auditoria")

    def __repr__(self):
        return f"<LogAuditoria(id={self.id}, usuario_id={self.usuario_id}, acao='{self.acao}', data_hora='{self.data_hora}')>"


# ============================================================================
# EXPORTAÇÕES
# ============================================================================

__all__ = [
    "Base",
    "Proprietario",
    "Veiculo",
    "RegistroAcesso",
    "Usuario",
    "Configuracao",
    "LogAuditoria",
]
