"""
Rotas de Autenticação - Sistema ALPR UNIPIAGET
Endpoints para login, logout e gestão de usuários
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional

from web_module.database import get_db
from web_module.models import Usuario
from web_module.services.auth_service import (
    autenticar_usuario,
    criar_token_acesso,
    verificar_token,
    obter_usuario_por_id,
    criar_usuario,
    atualizar_senha,
)
from shared.schemas import (
    LoginRequest,
    Token,
    UsuarioResponse,
    UsuarioCreate,
    UsuarioUpdate,
    MessageResponse,
)

router = APIRouter()
security = HTTPBearer()


# ============================================================================
# DEPENDÊNCIAS
# ============================================================================

async def obter_usuario_atual(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Usuario:
    """
    Dependency para obter usuário autenticado

    Args:
        credentials: Token JWT do header Authorization
        db: Sessão do banco

    Returns:
        Usuario autenticado

    Raises:
        HTTPException: Se token inválido ou usuário não encontrado
    """
    token = credentials.credentials

    # Verifica token
    token_data = verificar_token(token)
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Busca usuário
    usuario = obter_usuario_por_id(db, token_data.user_id)
    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not usuario.ativo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário inativo",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return usuario


def verificar_admin(usuario_atual: Usuario = Depends(obter_usuario_atual)) -> Usuario:
    """
    Dependency para verificar se usuário é admin

    Args:
        usuario_atual: Usuario autenticado

    Returns:
        Usuario se é admin

    Raises:
        HTTPException: Se não é admin
    """
    if usuario_atual.nivel_acesso != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Requer nível de administrador."
        )
    return usuario_atual


# ============================================================================
# ROTAS DE AUTENTICAÇÃO
# ============================================================================

@router.post("/auth/login", response_model=Token)
def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    """
    Autentica usuário e retorna token JWT

    - **username**: Username ou email
    - **senha**: Senha do usuário

    Returns:
        Token JWT e dados do usuário
    """
    # Autentica usuário
    usuario = autenticar_usuario(db, login_data.username, login_data.senha)

    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Username ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Cria token JWT
    token_data = {
        "sub": usuario.username,
        "user_id": usuario.id,
        "nivel_acesso": usuario.nivel_acesso
    }
    access_token = criar_token_acesso(token_data)

    # Retorna token e dados do usuário
    return Token(
        access_token=access_token,
        token_type="bearer",
        usuario=UsuarioResponse.model_validate(usuario)
    )


@router.get("/auth/me", response_model=UsuarioResponse)
def obter_perfil(usuario_atual: Usuario = Depends(obter_usuario_atual)):
    """
    Retorna dados do usuário autenticado

    Requer autenticação (token JWT)
    """
    return UsuarioResponse.model_validate(usuario_atual)


@router.post("/auth/logout", response_model=MessageResponse)
def logout(usuario_atual: Usuario = Depends(obter_usuario_atual)):
    """
    Logout do usuário

    Nota: Em JWT stateless, o logout é feito no client (descartando o token).
    Este endpoint serve apenas para registro de auditoria.
    """
    return MessageResponse(
        mensagem="Logout realizado com sucesso",
        sucesso=True
    )


# ============================================================================
# GESTÃO DE USUÁRIOS
# ============================================================================

@router.post("/usuarios", response_model=UsuarioResponse, status_code=status.HTTP_201_CREATED)
def criar_novo_usuario(
    usuario_data: UsuarioCreate,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(verificar_admin)
):
    """
    Cria novo usuário (apenas admin)

    - **username**: Username único
    - **email**: Email único
    - **nome_completo**: Nome completo
    - **senha**: Senha (mínimo 8 caracteres)
    - **nivel_acesso**: admin, operador ou visualizador

    Requer: Nível admin
    """
    try:
        usuario = criar_usuario(
            db=db,
            username=usuario_data.username,
            email=usuario_data.email,
            nome_completo=usuario_data.nome_completo,
            senha=usuario_data.senha,
            nivel_acesso=usuario_data.nivel_acesso
        )
        return UsuarioResponse.model_validate(usuario)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/usuarios", response_model=list[UsuarioResponse])
def listar_usuarios(
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    skip: int = 0,
    limit: int = 100,
    ativo: Optional[bool] = None
):
    """
    Lista todos os usuários

    Query parameters:
    - **skip**: Número de registros a pular
    - **limit**: Número máximo de registros
    - **ativo**: Filtrar por usuários ativos/inativos

    Requer: Autenticação
    """
    query = db.query(Usuario)

    if ativo is not None:
        query = query.filter(Usuario.ativo == ativo)

    usuarios = query.offset(skip).limit(limit).all()
    return [UsuarioResponse.model_validate(u) for u in usuarios]


@router.get("/usuarios/{user_id}", response_model=UsuarioResponse)
def obter_usuario(
    user_id: int,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(obter_usuario_atual)
):
    """
    Obtém dados de um usuário específico

    Requer: Autenticação
    """
    usuario = obter_usuario_por_id(db, user_id)

    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )

    return UsuarioResponse.model_validate(usuario)


@router.put("/usuarios/{user_id}", response_model=UsuarioResponse)
def atualizar_usuario(
    user_id: int,
    usuario_data: UsuarioUpdate,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(obter_usuario_atual)
):
    """
    Atualiza dados do usuário

    - Usuários podem atualizar seus próprios dados
    - Admin pode atualizar qualquer usuário

    Requer: Autenticação
    """
    usuario = obter_usuario_por_id(db, user_id)

    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )

    # Verifica permissão: só pode atualizar próprio perfil ou ser admin
    if usuario_atual.id != user_id and usuario_atual.nivel_acesso != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sem permissão para atualizar este usuário"
        )

    # Atualiza campos fornecidos
    if usuario_data.email is not None:
        usuario.email = usuario_data.email
    if usuario_data.nome_completo is not None:
        usuario.nome_completo = usuario_data.nome_completo
    if usuario_data.nivel_acesso is not None and usuario_atual.nivel_acesso == "admin":
        usuario.nivel_acesso = usuario_data.nivel_acesso
    if usuario_data.ativo is not None and usuario_atual.nivel_acesso == "admin":
        usuario.ativo = usuario_data.ativo
    if usuario_data.senha is not None:
        from services.auth_service import hash_senha
        usuario.senha_hash = hash_senha(usuario_data.senha)

    db.commit()
    db.refresh(usuario)

    return UsuarioResponse.model_validate(usuario)


@router.delete("/usuarios/{user_id}", response_model=MessageResponse)
def deletar_usuario(
    user_id: int,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(verificar_admin)
):
    """
    Deleta usuário (na verdade desativa)

    Requer: Nível admin
    """
    usuario = obter_usuario_por_id(db, user_id)

    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )

    # Não permite deletar próprio usuário
    if usuario.id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não é possível deletar seu próprio usuário"
        )

    # Desativa ao invés de deletar
    usuario.ativo = False
    db.commit()

    return MessageResponse(
        mensagem=f"Usuário {usuario.username} desativado com sucesso",
        sucesso=True
    )
