"""
Rotas de Veículos - Sistema ALPR UNIPIAGET
CRUD completo de veículos cadastrados
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional

from web_module.database import get_db
from web_module.models import Veiculo, Usuario
from web_module.routes.auth import obter_usuario_atual
from web_module.services.audit_service import registrar_log
from shared.schemas import (
    VeiculoCreate,
    VeiculoUpdate,
    VeiculoResponse,
    VeiculoComProprietario,
    MessageResponse,
)
from shared.utils import validar_placa_mocambique

router = APIRouter()


# ============================================================================
# CRUD DE VEÍCULOS
# ============================================================================

@router.post("/veiculos", response_model=VeiculoResponse, status_code=status.HTTP_201_CREATED)
def criar_veiculo(
    veiculo_data: VeiculoCreate,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(obter_usuario_atual)
):
    """
    Cadastra novo veículo

    - **placa**: Placa do veículo (formato moçambicano)
    - **modelo**: Modelo do veículo
    - **cor**: Cor do veículo
    - **proprietario_id**: ID do proprietário
    - **observacoes**: Observações adicionais

    Requer: Autenticação (operador ou admin)
    """
    # Verifica permissão
    if usuario_atual.nivel_acesso not in ("gestor", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sem permissão. Requer nível gestor ou admin."
        )

    # Valida placa
    placa_valida, placa_limpa = validar_placa_mocambique(veiculo_data.placa)
    if not placa_valida:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Placa inválida: {veiculo_data.placa}. Use formato moçambicano XXX000XX (3 letras + 3 números + 2 letras). Exemplo: MPM123AB"
        )

    # Verifica se placa já existe
    veiculo_existente = db.query(Veiculo).filter(Veiculo.placa == placa_limpa).first()
    if veiculo_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Placa {placa_limpa} já cadastrada"
        )

    # Cria veículo
    veiculo = Veiculo(
        placa=placa_limpa,
        modelo=veiculo_data.modelo,
        cor=veiculo_data.cor,
        proprietario_id=veiculo_data.proprietario_id,
        observacoes=veiculo_data.observacoes
    )

    db.add(veiculo)
    registrar_log(db, usuario_atual.id, "criar_veiculo", f"Placa: {placa_limpa}")
    db.commit()
    db.refresh(veiculo)

    return VeiculoResponse.model_validate(veiculo)


@router.get("/veiculos", response_model=list[VeiculoComProprietario])
def listar_veiculos(
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    proprietario_id: Optional[int] = None,
    placa: Optional[str] = None
):
    """
    Lista veículos cadastrados

    Query parameters:
    - **skip**: Número de registros a pular
    - **limit**: Número máximo de registros (max 100)
    - **proprietario_id**: Filtrar por proprietário
    - **placa**: Buscar por placa (parcial)

    Requer: Autenticação
    """
    query = db.query(Veiculo)

    # Filtros
    if proprietario_id:
        query = query.filter(Veiculo.proprietario_id == proprietario_id)

    if placa:
        placa_busca = placa.upper().replace("-", "").replace(" ", "")
        query = query.filter(Veiculo.placa.contains(placa_busca))

    veiculos = query.offset(skip).limit(limit).all()
    return [VeiculoComProprietario.model_validate(v) for v in veiculos]


@router.get("/veiculos/{veiculo_id}", response_model=VeiculoComProprietario)
def obter_veiculo(
    veiculo_id: int,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(obter_usuario_atual)
):
    """
    Obtém dados de um veículo específico

    Requer: Autenticação
    """
    veiculo = db.query(Veiculo).filter(Veiculo.id == veiculo_id).first()

    if not veiculo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Veículo não encontrado"
        )

    return VeiculoComProprietario.model_validate(veiculo)


@router.get("/veiculos/placa/{placa}", response_model=VeiculoComProprietario)
def buscar_veiculo_por_placa(
    placa: str,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(obter_usuario_atual)
):
    """
    Busca veículo por placa exata

    Requer: Autenticação
    """
    placa_limpa = placa.upper().replace("-", "").replace(" ", "")

    veiculo = db.query(Veiculo).filter(Veiculo.placa == placa_limpa).first()

    if not veiculo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Veículo com placa {placa} não encontrado"
        )

    return VeiculoComProprietario.model_validate(veiculo)


@router.put("/veiculos/{veiculo_id}", response_model=VeiculoResponse)
def atualizar_veiculo(
    veiculo_id: int,
    veiculo_data: VeiculoUpdate,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(obter_usuario_atual)
):
    """
    Atualiza dados do veículo

    Requer: Nível gestor ou admin
    """
    # Verifica permissão
    if usuario_atual.nivel_acesso not in ("gestor", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sem permissão. Requer nível gestor ou admin."
        )

    veiculo = db.query(Veiculo).filter(Veiculo.id == veiculo_id).first()

    if not veiculo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Veículo não encontrado"
        )

    # Atualiza campos fornecidos
    if veiculo_data.placa is not None:
        placa_valida, placa_limpa = validar_placa_mocambique(veiculo_data.placa)
        if not placa_valida:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Placa inválida: {veiculo_data.placa}. Use formato moçambicano XXX000XX. Exemplo: MPM123AB"
            )
        # Verifica se nova placa já existe
        if placa_limpa != veiculo.placa:
            veiculo_existente = db.query(Veiculo).filter(Veiculo.placa == placa_limpa).first()
            if veiculo_existente:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Placa {placa_limpa} já cadastrada"
                )
        veiculo.placa = placa_limpa

    if veiculo_data.modelo is not None:
        veiculo.modelo = veiculo_data.modelo
    if veiculo_data.cor is not None:
        veiculo.cor = veiculo_data.cor
    if veiculo_data.proprietario_id is not None:
        veiculo.proprietario_id = veiculo_data.proprietario_id
    if veiculo_data.observacoes is not None:
        veiculo.observacoes = veiculo_data.observacoes

    registrar_log(db, usuario_atual.id, "editar_veiculo", f"ID: {veiculo_id}, Placa: {veiculo.placa}")
    db.commit()
    db.refresh(veiculo)

    return VeiculoResponse.model_validate(veiculo)


@router.delete("/veiculos/{veiculo_id}", response_model=MessageResponse)
def deletar_veiculo(
    veiculo_id: int,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(obter_usuario_atual)
):
    """
    Deleta veículo do sistema

    ATENÇÃO: Também deleta todos os registros de acesso associados (CASCADE)

    Requer: Nível admin
    """
    # Apenas admin pode deletar
    if usuario_atual.nivel_acesso != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sem permissão. Requer nível admin."
        )

    veiculo = db.query(Veiculo).filter(Veiculo.id == veiculo_id).first()

    if not veiculo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Veículo não encontrado"
        )

    placa = veiculo.placa
    registrar_log(db, usuario_atual.id, "deletar_veiculo", f"ID: {veiculo_id}, Placa: {placa}")
    db.delete(veiculo)
    db.commit()

    return MessageResponse(
        mensagem=f"Veículo {placa} deletado com sucesso",
        sucesso=True
    )


@router.get("/veiculos/count/total")
def contar_veiculos(
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    proprietario_id: Optional[int] = None
):
    """
    Conta total de veículos cadastrados

    Query parameters:
    - **proprietario_id**: Filtrar por proprietário

    Requer: Autenticação
    """
    query = db.query(Veiculo)

    if proprietario_id:
        query = query.filter(Veiculo.proprietario_id == proprietario_id)

    total = query.count()

    return {
        "total_veiculos": total,
        "proprietario_id": proprietario_id
    }
