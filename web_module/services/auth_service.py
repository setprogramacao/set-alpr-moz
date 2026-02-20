"""
Serviço de Autenticação - Sistema ALPR UNIPIAGET
Gerencia autenticação, autorização e tokens JWT
"""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
import bcrypt
from sqlalchemy.orm import Session
import os

from web_module.models import Usuario
from shared.schemas import TokenData


# ============================================================================
# CONFIGURAÇÕES
# ============================================================================

# Chave secreta para JWT (deve estar no .env em produção!)
SECRET_KEY = os.getenv("SECRET_KEY", "sua-chave-secreta-super-segura-mude-em-producao")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24 horas


# ============================================================================
# FUNÇÕES DE SENHA
# ============================================================================

def verificar_senha(senha_plana: str, senha_hash: str) -> bool:
    """
    Verifica se senha corresponde ao hash

    Args:
        senha_plana: Senha em texto plano
        senha_hash: Hash da senha

    Returns:
        True se corresponde, False caso contrário
    """
    try:
        return bcrypt.checkpw(senha_plana.encode('utf-8'), senha_hash.encode('utf-8'))
    except Exception:
        return False


def hash_senha(senha: str) -> str:
    """
    Gera hash bcrypt da senha

    Args:
        senha: Senha em texto plano

    Returns:
        Hash da senha
    """
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(senha.encode('utf-8'), salt)
    return hashed.decode('utf-8')


# ============================================================================
# FUNÇÕES DE TOKEN JWT
# ============================================================================

def criar_token_acesso(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Cria token JWT de acesso

    Args:
        data: Dados a codificar no token
        expires_delta: Tempo de expiração customizado

    Returns:
        Token JWT codificado
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt


def verificar_token(token: str) -> Optional[TokenData]:
    """
    Verifica e decodifica token JWT

    Args:
        token: Token JWT

    Returns:
        TokenData com dados do usuário ou None se inválido
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        user_id: int = payload.get("user_id")
        nivel_acesso: str = payload.get("nivel_acesso")

        if username is None or user_id is None:
            return None

        token_data = TokenData(
            username=username,
            user_id=user_id,
            nivel_acesso=nivel_acesso
        )

        return token_data

    except JWTError:
        return None


# ============================================================================
# FUNÇÕES DE AUTENTICAÇÃO
# ============================================================================

def autenticar_usuario(db: Session, username: str, senha: str) -> Optional[Usuario]:
    """
    Autentica usuário por username/email e senha

    Args:
        db: Sessão do banco
        username: Username ou email
        senha: Senha em texto plano

    Returns:
        Usuario se autenticado, None caso contrário
    """
    # Busca por username ou email
    usuario = db.query(Usuario).filter(
        (Usuario.username == username) | (Usuario.email == username)
    ).first()

    if not usuario:
        return None

    # Verifica se está ativo
    if not usuario.ativo:
        return None

    # Verifica senha
    if not verificar_senha(senha, usuario.senha_hash):
        return None

    return usuario


def verificar_nivel_acesso(usuario: Usuario, nivel_minimo: str) -> bool:
    """
    Verifica se usuário tem nível de acesso suficiente

    Hierarquia: admin > operador > visualizador

    Args:
        usuario: Usuário a verificar
        nivel_minimo: Nível mínimo requerido

    Returns:
        True se tem acesso, False caso contrário
    """
    niveis = {
        "visualizador": 1,
        "operador": 2,
        "admin": 3
    }

    nivel_usuario = niveis.get(usuario.nivel_acesso, 0)
    nivel_requerido = niveis.get(nivel_minimo, 999)

    return nivel_usuario >= nivel_requerido


def obter_usuario_por_id(db: Session, user_id: int) -> Optional[Usuario]:
    """
    Busca usuário por ID

    Args:
        db: Sessão do banco
        user_id: ID do usuário

    Returns:
        Usuario ou None
    """
    return db.query(Usuario).filter(Usuario.id == user_id).first()


def obter_usuario_por_username(db: Session, username: str) -> Optional[Usuario]:
    """
    Busca usuário por username

    Args:
        db: Sessão do banco
        username: Username

    Returns:
        Usuario ou None
    """
    return db.query(Usuario).filter(Usuario.username == username).first()


def obter_usuario_por_email(db: Session, email: str) -> Optional[Usuario]:
    """
    Busca usuário por email

    Args:
        db: Sessão do banco
        email: Email

    Returns:
        Usuario ou None
    """
    return db.query(Usuario).filter(Usuario.email == email).first()


# ============================================================================
# GERENCIAMENTO DE USUÁRIOS
# ============================================================================

def criar_usuario(db: Session, username: str, email: str, nome_completo: str,
                  senha: str, nivel_acesso: str = "visualizador") -> Usuario:
    """
    Cria novo usuário

    Args:
        db: Sessão do banco
        username: Username único
        email: Email único
        nome_completo: Nome completo
        senha: Senha em texto plano
        nivel_acesso: Nível de acesso

    Returns:
        Usuario criado

    Raises:
        ValueError: Se username ou email já existe
    """
    # Verifica se username já existe
    if obter_usuario_por_username(db, username):
        raise ValueError("Username já existe")

    # Verifica se email já existe
    if obter_usuario_por_email(db, email):
        raise ValueError("Email já existe")

    # Cria usuário
    usuario = Usuario(
        username=username,
        email=email,
        nome_completo=nome_completo,
        senha_hash=hash_senha(senha),
        nivel_acesso=nivel_acesso,
        ativo=True
    )

    db.add(usuario)
    db.commit()
    db.refresh(usuario)

    return usuario


def atualizar_senha(db: Session, user_id: int, senha_nova: str) -> bool:
    """
    Atualiza senha do usuário

    Args:
        db: Sessão do banco
        user_id: ID do usuário
        senha_nova: Nova senha em texto plano

    Returns:
        True se atualizado, False caso contrário
    """
    usuario = obter_usuario_por_id(db, user_id)

    if not usuario:
        return False

    usuario.senha_hash = hash_senha(senha_nova)
    db.commit()

    return True


def desativar_usuario(db: Session, user_id: int) -> bool:
    """
    Desativa usuário (não deleta, apenas marca como inativo)

    Args:
        db: Sessão do banco
        user_id: ID do usuário

    Returns:
        True se desativado, False caso contrário
    """
    usuario = obter_usuario_por_id(db, user_id)

    if not usuario:
        return False

    usuario.ativo = False
    db.commit()

    return True


def reativar_usuario(db: Session, user_id: int) -> bool:
    """
    Reativa usuário

    Args:
        db: Sessão do banco
        user_id: ID do usuário

    Returns:
        True se reativado, False caso contrário
    """
    usuario = obter_usuario_por_id(db, user_id)

    if not usuario:
        return False

    usuario.ativo = True
    db.commit()

    return True
