"""
Configuração do Banco de Dados - Sistema ALPR UNIPIAGET
SQLAlchemy engine, session e utilitários
"""

import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.engine import Engine
from typing import Generator
from contextlib import contextmanager

# Importa a Base dos modelos
from web_module.models import Base, Proprietario, Veiculo, RegistroAcesso, Usuario, Configuracao, LogAuditoria


# ============================================================================
# CONFIGURAÇÃO DO BANCO DE DADOS
# ============================================================================

# URL do banco de dados (SQLite ou PostgreSQL)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./alpr_unipiaget.db"  # Default: SQLite local
)

# Configurações do engine
if DATABASE_URL.startswith("sqlite"):
    # SQLite: habilita chaves estrangeiras e otimizações
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},  # Permite múltiplas threads
        echo=False,  # Set True para debug (mostra SQL queries)
        pool_pre_ping=True,  # Verifica conexão antes de usar
    )

    # Habilita chaves estrangeiras no SQLite
    @event.listens_for(Engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

else:
    # PostgreSQL ou outros bancos
    engine = create_engine(
        DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
        pool_size=10,  # Número de conexões no pool
        max_overflow=20,  # Conexões extras permitidas
    )


# Cria SessionLocal para interagir com o banco
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


# ============================================================================
# GERENCIAMENTO DE SESSÕES
# ============================================================================

def get_db() -> Generator[Session, None, None]:
    """
    Dependency para FastAPI - fornece sessão do banco de dados

    Uso:
        @app.get("/exemplo")
        def exemplo(db: Session = Depends(get_db)):
            # usar db aqui
            pass

    Yields:
        Session: Sessão do SQLAlchemy
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context():
    """
    Context manager para uso fora do FastAPI

    Uso:
        with get_db_context() as db:
            # usar db aqui
            pass

    Yields:
        Session: Sessão do SQLAlchemy
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ============================================================================
# INICIALIZAÇÃO DO BANCO DE DADOS
# ============================================================================

def aplicar_migracoes() -> None:
    """
    Aplica migrações incrementais no banco de dados.
    Adiciona colunas novas sem destruir dados existentes.
    """
    from sqlalchemy import text, inspect as sa_inspect
    insp = sa_inspect(engine)

    # Migração: registros_acesso — novas colunas para registo manual
    if 'registros_acesso' in insp.get_table_names():
        colunas_existentes = {c['name'] for c in insp.get_columns('registros_acesso')}
        novas_colunas = [
            ("origem",             "VARCHAR(10) NOT NULL DEFAULT 'automatico'"),
            ("registrado_por_id",  "INTEGER REFERENCES usuarios(id)"),
            ("observacoes",        "VARCHAR(500)"),
        ]
        with engine.connect() as conn:
            for nome_col, definicao in novas_colunas:
                if nome_col not in colunas_existentes:
                    conn.execute(text(f"ALTER TABLE registros_acesso ADD COLUMN {nome_col} {definicao}"))
                    print(f"  ✓ Coluna '{nome_col}' adicionada a registros_acesso")
            conn.commit()


def init_db(criar_dados_exemplo: bool = False) -> None:
    """
    Inicializa o banco de dados

    - Cria todas as tabelas
    - Opcionalmente cria dados de exemplo

    Args:
        criar_dados_exemplo: Se True, cria usuário admin e dados de teste
    """
    # Cria todas as tabelas
    Base.metadata.create_all(bind=engine)
    print("✓ Tabelas criadas com sucesso")

    # Aplica migrações incrementais
    aplicar_migracoes()

    if criar_dados_exemplo:
        criar_dados_iniciais()


def drop_db() -> None:
    """
    CUIDADO: Remove todas as tabelas do banco de dados
    Usar apenas em desenvolvimento!
    """
    confirm = input("⚠️  ATENÇÃO: Isso vai apagar TODOS os dados! Digite 'CONFIRMAR' para continuar: ")
    if confirm == "CONFIRMAR":
        Base.metadata.drop_all(bind=engine)
        print("✓ Todas as tabelas foram removidas")
    else:
        print("✗ Operação cancelada")


def reset_db(criar_dados_exemplo: bool = True) -> None:
    """
    Reseta o banco de dados (drop + create)

    Args:
        criar_dados_exemplo: Se True, cria dados iniciais
    """
    print("Resetando banco de dados...")
    Base.metadata.drop_all(bind=engine)
    print("✓ Tabelas removidas")

    Base.metadata.create_all(bind=engine)
    print("✓ Tabelas recriadas")

    if criar_dados_exemplo:
        criar_dados_iniciais()


# ============================================================================
# DADOS INICIAIS
# ============================================================================

def criar_dados_iniciais() -> None:
    """
    Cria dados iniciais do sistema:
    - Usuário administrador padrão
    - Configurações padrão
    - Dados de exemplo (opcional)
    """
    import bcrypt

    with get_db_context() as db:
        # Verifica se já existe usuário admin
        admin_existente = db.query(Usuario).filter(Usuario.username == "admin").first()

        if not admin_existente:
            # Cria usuário administrador padrão
            salt = bcrypt.gensalt()
            senha_hash = bcrypt.hashpw("admin123".encode('utf-8'), salt).decode('utf-8')

            admin = Usuario(
                username="admin",
                email="admin@unipiaget.ac.mz",
                nome_completo="Administrador do Sistema",
                senha_hash=senha_hash,  # IMPORTANTE: Mudar em produção!
                nivel_acesso="admin",
                ativo=True
            )
            db.add(admin)
            print("[OK] Usuario admin criado (username: admin, senha: admin123)")

        # Cria configurações padrão
        configuracoes_padrao = [
            {
                "chave": "intervalo_duplicata_minutos",
                "valor": "5",
                "tipo": "integer",
                "descricao": "Intervalo mínimo em minutos para considerar detecção duplicada"
            },
            {
                "chave": "confianca_minima_ocr",
                "valor": "0.6",
                "tipo": "float",
                "descricao": "Confiança mínima do OCR para aceitar detecção (0.0 a 1.0)"
            },
            {
                "chave": "metodo_ocr_padrao",
                "valor": "hibrido",
                "tipo": "string",
                "descricao": "Método OCR padrão: easyocr, tesseract ou hibrido"
            },
            {
                "chave": "salvar_imagens_deteccao",
                "valor": "true",
                "tipo": "boolean",
                "descricao": "Se deve salvar imagens das detecções"
            },
            {
                "chave": "alerta_ausencia_docente_horas",
                "valor": "4",
                "tipo": "integer",
                "descricao": "Horas de ausência para gerar alerta de docente"
            },
        ]

        for config_data in configuracoes_padrao:
            config_existente = db.query(Configuracao).filter(
                Configuracao.chave == config_data["chave"]
            ).first()

            if not config_existente:
                config = Configuracao(**config_data)
                db.add(config)

        db.commit()
        print("✓ Configurações padrão criadas")

        # Cria dados de exemplo (proprietários e veículos)
        criar_dados_exemplo(db)


def criar_dados_exemplo(db: Session) -> None:
    """
    Cria dados de exemplo para testes

    Args:
        db: Sessão do banco de dados
    """
    # Verifica se já existem proprietários
    proprietarios_existentes = db.query(Proprietario).count()

    if proprietarios_existentes == 0:
        # Cria proprietários de exemplo
        proprietarios = [
            Proprietario(
                nome="Dr. João Silva",
                categoria="docente",
                departamento="Engenharia Electrónica",
                telefone="+258845678901",
                email="joao.silva@unipiaget.ac.mz",
                ativo=True
            ),
            Proprietario(
                nome="Prof. Maria Santos",
                categoria="docente",
                departamento="Telecomunicações",
                telefone="+258847654321",
                email="maria.santos@unipiaget.ac.mz",
                ativo=True
            ),
            Proprietario(
                nome="Eng. Pedro Costa",
                categoria="tecnico",
                departamento="Laboratório de Redes",
                telefone="+258849876543",
                email="pedro.costa@unipiaget.ac.mz",
                ativo=True
            ),
        ]

        for prop in proprietarios:
            db.add(prop)

        db.commit()
        print("✓ Proprietários de exemplo criados")

        # Cria veículos de exemplo
        veiculos = [
            Veiculo(
                placa="MP123456",
                modelo="Toyota Corolla",
                cor="Preto",
                proprietario_id=1,
                observacoes="Veículo do coordenador"
            ),
            Veiculo(
                placa="MP789012",
                modelo="Honda Civic",
                cor="Branco",
                proprietario_id=2,
                observacoes="Veículo da professora Maria"
            ),
            Veiculo(
                placa="MP345678",
                modelo="Nissan Patrol",
                cor="Prata",
                proprietario_id=3,
                observacoes="Viatura do laboratório"
            ),
        ]

        for veiculo in veiculos:
            db.add(veiculo)

        db.commit()
        print("✓ Veículos de exemplo criados")


# ============================================================================
# UTILITÁRIOS DE CONSULTA
# ============================================================================

def verificar_conexao() -> bool:
    """
    Verifica se a conexão com o banco está funcionando

    Returns:
        bool: True se conectado, False caso contrário
    """
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"Erro ao conectar ao banco: {e}")
        return False


def obter_estatisticas_db() -> dict:
    """
    Retorna estatísticas básicas do banco de dados

    Returns:
        dict: Dicionário com contagens de registros
    """
    with get_db_context() as db:
        stats = {
            "proprietarios": db.query(Proprietario).count(),
            "veiculos": db.query(Veiculo).count(),
            "registros_acesso": db.query(RegistroAcesso).count(),
            "usuarios": db.query(Usuario).count(),
            "configuracoes": db.query(Configuracao).count(),
            "logs_auditoria": db.query(LogAuditoria).count(),
        }
    return stats


# ============================================================================
# EXPORTAÇÕES
# ============================================================================

__all__ = [
    "engine",
    "SessionLocal",
    "get_db",
    "get_db_context",
    "init_db",
    "drop_db",
    "reset_db",
    "verificar_conexao",
    "obter_estatisticas_db",
    "Base",
    "Proprietario",
    "Veiculo",
    "RegistroAcesso",
    "Usuario",
    "Configuracao",
    "LogAuditoria",
]
