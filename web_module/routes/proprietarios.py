"""
Rotas de Proprietários - Sistema ALPR UNIPIAGET
CRUD completo de proprietários de veículos
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from sqlalchemy import func
from sqlalchemy.orm import Session
from typing import Optional

from web_module.database import get_db
from web_module.models import Proprietario, Usuario
from web_module.routes.auth import obter_usuario_atual
from web_module.services.audit_service import registrar_log
from shared.schemas import (
    ProprietarioCreate,
    ProprietarioUpdate,
    ProprietarioResponse,
    MessageResponse,
)

router = APIRouter()


# ============================================================================
# CRUD DE PROPRIETÁRIOS
# ============================================================================

@router.post("/proprietarios", response_model=ProprietarioResponse, status_code=status.HTTP_201_CREATED)
def criar_proprietario(
    proprietario_data: ProprietarioCreate,
    response: Response,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(obter_usuario_atual)
):
    """
    Cadastra novo proprietário

    - **nome**: Nome completo
    - **categoria**: docente, tecnico, visitante, aluno
    - **departamento**: Departamento/Faculdade
    - **telefone**: Número de telefone moçambicano
    - **email**: Email usado para identificar e reutilizar um proprietário existente

    Requer: Nível gestor ou admin
    """
    # Verifica permissão
    if usuario_atual.nivel_acesso not in ("gestor", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sem permissão. Requer nível gestor ou admin."
        )

    # Um proprietario pode ter varios veiculos. Se o cliente repetir os dados
    # ao cadastrar outro carro, reutiliza o registro existente em vez de criar
    # uma pessoa duplicada ou bloquear o fluxo.
    if proprietario_data.email:
        email_normalizado = str(proprietario_data.email).strip().lower()
        email_existente = db.query(Proprietario).filter(
            func.lower(Proprietario.email) == email_normalizado
        ).first()
        if email_existente:
            response.status_code = status.HTTP_200_OK
            return ProprietarioResponse.model_validate(email_existente)
    else:
        email_normalizado = None

    # Cria proprietário
    proprietario = Proprietario(
        nome=proprietario_data.nome,
        categoria=proprietario_data.categoria,
        departamento=proprietario_data.departamento,
        telefone=proprietario_data.telefone,
        email=email_normalizado,
        ativo=True
    )

    db.add(proprietario)
    registrar_log(db, usuario_atual.id, "criar_proprietario", f"Nome: {proprietario_data.nome}")
    db.commit()
    db.refresh(proprietario)

    return ProprietarioResponse.model_validate(proprietario)


@router.get("/proprietarios", response_model=list[ProprietarioResponse])
def listar_proprietarios(
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    categoria: Optional[str] = None,
    departamento: Optional[str] = None,
    ativo: Optional[bool] = None,
    nome: Optional[str] = None
):
    """
    Lista proprietários cadastrados

    Query parameters:
    - **skip**: Número de registros a pular
    - **limit**: Número máximo de registros (max 100)
    - **categoria**: Filtrar por categoria (docente, tecnico, visitante, aluno)
    - **departamento**: Filtrar por departamento
    - **ativo**: Filtrar por status ativo/inativo
    - **nome**: Buscar por nome (parcial)

    Requer: Autenticação
    """
    query = db.query(Proprietario)

    # Filtros
    if categoria:
        query = query.filter(Proprietario.categoria == categoria)

    if departamento:
        query = query.filter(Proprietario.departamento.contains(departamento))

    if ativo is not None:
        query = query.filter(Proprietario.ativo == ativo)

    if nome:
        query = query.filter(Proprietario.nome.contains(nome))

    proprietarios = query.offset(skip).limit(limit).all()
    return [ProprietarioResponse.model_validate(p) for p in proprietarios]


@router.get("/proprietarios/{proprietario_id}", response_model=ProprietarioResponse)
def obter_proprietario(
    proprietario_id: int,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(obter_usuario_atual)
):
    """
    Obtém dados de um proprietário específico

    Requer: Autenticação
    """
    proprietario = db.query(Proprietario).filter(Proprietario.id == proprietario_id).first()

    if not proprietario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proprietário não encontrado"
        )

    return ProprietarioResponse.model_validate(proprietario)


@router.put("/proprietarios/{proprietario_id}", response_model=ProprietarioResponse)
def atualizar_proprietario(
    proprietario_id: int,
    proprietario_data: ProprietarioUpdate,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(obter_usuario_atual)
):
    """
    Atualiza dados do proprietário

    Requer: Nível gestor ou admin
    """
    # Verifica permissão
    if usuario_atual.nivel_acesso not in ("gestor", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sem permissão. Requer nível gestor ou admin."
        )

    proprietario = db.query(Proprietario).filter(Proprietario.id == proprietario_id).first()

    if not proprietario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proprietário não encontrado"
        )

    # Atualiza campos fornecidos
    if proprietario_data.nome is not None:
        proprietario.nome = proprietario_data.nome
    if proprietario_data.categoria is not None:
        proprietario.categoria = proprietario_data.categoria
    if proprietario_data.departamento is not None:
        proprietario.departamento = proprietario_data.departamento
    if proprietario_data.telefone is not None:
        proprietario.telefone = proprietario_data.telefone
    if proprietario_data.email is not None:
        email_normalizado = str(proprietario_data.email).strip().lower()
        # Verifica se novo email já existe
        if email_normalizado != (proprietario.email or "").lower():
            email_existente = db.query(Proprietario).filter(
                func.lower(Proprietario.email) == email_normalizado,
                Proprietario.id != proprietario_id,
            ).first()
            if email_existente:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Email {email_normalizado} já pertence a outro proprietário"
                )
        proprietario.email = email_normalizado
    if proprietario_data.ativo is not None:
        proprietario.ativo = proprietario_data.ativo

    registrar_log(db, usuario_atual.id, "editar_proprietario", f"ID: {proprietario_id}, Nome: {proprietario.nome}")
    db.commit()
    db.refresh(proprietario)

    return ProprietarioResponse.model_validate(proprietario)


@router.delete("/proprietarios/{proprietario_id}", response_model=MessageResponse)
def deletar_proprietario(
    proprietario_id: int,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(obter_usuario_atual)
):
    """
    Deleta proprietário do sistema

    ATENÇÃO: Também deleta todos os veículos e registros associados (CASCADE)

    Requer: Nível admin
    """
    # Apenas admin pode deletar
    if usuario_atual.nivel_acesso != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sem permissão. Requer nível admin."
        )

    proprietario = db.query(Proprietario).filter(Proprietario.id == proprietario_id).first()

    if not proprietario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proprietário não encontrado"
        )

    nome = proprietario.nome
    registrar_log(db, usuario_atual.id, "deletar_proprietario", f"ID: {proprietario_id}, Nome: {nome}")
    db.delete(proprietario)
    db.commit()

    return MessageResponse(
        mensagem=f"Proprietário {nome} deletado com sucesso",
        sucesso=True
    )


@router.get("/proprietarios/count/total")
def contar_proprietarios(
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    categoria: Optional[str] = None,
    ativo: Optional[bool] = None
):
    """
    Conta total de proprietários cadastrados

    Query parameters:
    - **categoria**: Filtrar por categoria
    - **ativo**: Filtrar por status ativo/inativo

    Requer: Autenticação
    """
    query = db.query(Proprietario)

    if categoria:
        query = query.filter(Proprietario.categoria == categoria)

    if ativo is not None:
        query = query.filter(Proprietario.ativo == ativo)

    total = query.count()

    return {
        "total_proprietarios": total,
        "categoria": categoria,
        "ativo": ativo
    }


@router.get("/proprietarios/categorias/listar")
def listar_categorias(
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(obter_usuario_atual)
):
    """
    Lista categorias disponíveis com contagens

    Requer: Autenticação
    """
    from sqlalchemy import func

    categorias = db.query(
        Proprietario.categoria,
        func.count(Proprietario.id).label("total")
    ).group_by(Proprietario.categoria).all()

    return [
        {"categoria": cat, "total": total}
        for cat, total in categorias
    ]
