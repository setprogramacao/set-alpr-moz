"""
Rotas de Registros de Acesso - Sistema ALPR UNIPIAGET
Gerenciamento de registros de entrada/saída e recepção de detecções
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
from datetime import datetime, timedelta
from typing import Optional

from web_module.database import get_db
from web_module.models import RegistroAcesso, Veiculo, Usuario
from web_module.routes.auth import obter_usuario_atual
from web_module.services.deteccao_service import processar_deteccao, obter_registros_hoje, contar_registros_hoje
from shared.schemas import (
    DeteccaoRequest,
    DeteccaoResponse,
    RegistroAcessoResponse,
    RegistroAcessoDetalhado,
    RegistroManualCreate,
    RegistroManualUpdate,
    MessageResponse,
)

router = APIRouter()


# ============================================================================
# ENDPOINT PARA RECEBER DETECÇÕES DO DESKTOP
# ============================================================================

@router.post("/registros/deteccao", response_model=DeteccaoResponse)
def receber_deteccao(
    deteccao: DeteccaoRequest,
    db: Session = Depends(get_db)
):
    """
    Recebe detecção de placa do módulo Desktop

    Este endpoint é chamado pelo módulo Desktop quando uma placa é detectada.

    - **placa_detectada**: Placa detectada
    - **tipo_movimento**: "entrada" ou "saida"
    - **confianca_ocr**: Confiança do OCR (0.0 a 1.0)
    - **metodo_ocr**: Método usado ("easyocr", "tesseract", "hibrido")
    - **imagem_base64**: Imagem da detecção em base64 (opcional)
    - **timestamp**: Data/hora da detecção (opcional)

    Não requer autenticação (endpoint público para o Desktop)
    """
    try:
        resposta = processar_deteccao(db, deteccao, salvar_imagem=True)
        return resposta

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao processar detecção: {str(e)}"
        )


# ============================================================================
# CONSULTA DE REGISTROS
# ============================================================================

@router.get("/registros", response_model=list[RegistroAcessoDetalhado])
def listar_registros(
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    veiculo_id: Optional[int] = None,
    placa: Optional[str] = None,
    tipo_movimento: Optional[str] = None,
    data_inicio: Optional[datetime] = None,
    data_fim: Optional[datetime] = None,
    cadastrado_apenas: Optional[bool] = None
):
    """
    Lista registros de acesso

    Query parameters:
    - **skip**: Número de registros a pular
    - **limit**: Número máximo de registros (max 100)
    - **veiculo_id**: Filtrar por veículo específico
    - **placa**: Buscar por placa (parcial)
    - **tipo_movimento**: Filtrar por "entrada" ou "saida"
    - **data_inicio**: Data/hora de início do período
    - **data_fim**: Data/hora de fim do período
    - **cadastrado_apenas**: Mostrar apenas veículos cadastrados

    Requer: Autenticação
    """
    query = db.query(RegistroAcesso)

    # Filtros
    if veiculo_id:
        query = query.filter(RegistroAcesso.veiculo_id == veiculo_id)

    if placa:
        placa_busca = placa.upper().replace("-", "").replace(" ", "")
        query = query.filter(RegistroAcesso.placa_detectada.contains(placa_busca))

    if tipo_movimento:
        query = query.filter(RegistroAcesso.tipo_movimento == tipo_movimento)

    if data_inicio:
        query = query.filter(RegistroAcesso.data_hora >= data_inicio)

    if data_fim:
        query = query.filter(RegistroAcesso.data_hora <= data_fim)

    if cadastrado_apenas:
        query = query.filter(RegistroAcesso.veiculo_id.isnot(None))

    registros = query.order_by(desc(RegistroAcesso.data_hora)).offset(skip).limit(limit).all()

    return [RegistroAcessoDetalhado.model_validate(r) for r in registros]


@router.get("/registros/hoje", response_model=list[RegistroAcessoDetalhado])
def listar_registros_hoje(
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    limit: int = Query(100, ge=1, le=200)
):
    """
    Lista registros de hoje

    Requer: Autenticação
    """
    registros = obter_registros_hoje(db, limite=limit)
    return [RegistroAcessoDetalhado.model_validate(r) for r in registros]


@router.get("/registros/{registro_id}", response_model=RegistroAcessoDetalhado)
def obter_registro(
    registro_id: int,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(obter_usuario_atual)
):
    """
    Obtém detalhes de um registro específico

    Requer: Autenticação
    """
    registro = db.query(RegistroAcesso).filter(RegistroAcesso.id == registro_id).first()

    if not registro:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registro não encontrado"
        )

    return RegistroAcessoDetalhado.model_validate(registro)


@router.delete("/registros/{registro_id}", response_model=MessageResponse)
def deletar_registro(
    registro_id: int,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(obter_usuario_atual)
):
    """
    Deleta um registro

    Requer: Nível admin
    """
    # Apenas admin pode deletar registros
    if usuario_atual.nivel_acesso != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sem permissão. Requer nível admin."
        )

    registro = db.query(RegistroAcesso).filter(RegistroAcesso.id == registro_id).first()

    if not registro:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registro não encontrado"
        )

    db.delete(registro)
    db.commit()

    return MessageResponse(
        mensagem=f"Registro {registro_id} deletado com sucesso",
        sucesso=True
    )


# ============================================================================
# REGISTRO MANUAL (operador / admin)
# ============================================================================

@router.post("/registros/manual", response_model=RegistroAcessoDetalhado)
def criar_registro_manual(
    dados: RegistroManualCreate,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(obter_usuario_atual)
):
    """
    Cria um registro de acesso manual

    Usado quando o OCR falha e o agente de segurança precisa registar
    a entrada/saída manualmente.

    Requer: Nível operador ou admin
    """
    if usuario_atual.nivel_acesso not in ("operador", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sem permissão. Requer nível operador ou admin."
        )

    # Tenta associar a um veículo cadastrado
    veiculo = db.query(Veiculo).filter(Veiculo.placa == dados.placa_detectada).first()

    registro = RegistroAcesso(
        placa_detectada=dados.placa_detectada,
        tipo_movimento=dados.tipo_movimento,
        data_hora=dados.data_hora or datetime.now(),
        confianca_ocr=None,
        metodo_ocr=None,
        origem="manual",
        veiculo_id=veiculo.id if veiculo else None,
        registrado_por_id=usuario_atual.id,
        observacoes=dados.observacoes,
    )
    db.add(registro)
    db.commit()
    db.refresh(registro)

    return RegistroAcessoDetalhado.model_validate(registro)


@router.put("/registros/{registro_id}/manual", response_model=RegistroAcessoDetalhado)
def editar_registro_manual(
    registro_id: int,
    dados: RegistroManualUpdate,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(obter_usuario_atual)
):
    """
    Edita um registro de acesso manual existente

    Apenas registros com origem='manual' podem ser editados por esta rota.

    Requer: Nível operador ou admin
    """
    if usuario_atual.nivel_acesso not in ("operador", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sem permissão. Requer nível operador ou admin."
        )

    registro = db.query(RegistroAcesso).filter(RegistroAcesso.id == registro_id).first()
    if not registro:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registro não encontrado")

    if registro.origem != "manual":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Apenas registros manuais podem ser editados por esta rota."
        )

    if dados.placa_detectada is not None:
        registro.placa_detectada = dados.placa_detectada
        veiculo = db.query(Veiculo).filter(Veiculo.placa == dados.placa_detectada).first()
        registro.veiculo_id = veiculo.id if veiculo else None

    if dados.tipo_movimento is not None:
        registro.tipo_movimento = dados.tipo_movimento

    if dados.data_hora is not None:
        registro.data_hora = dados.data_hora

    if dados.observacoes is not None:
        registro.observacoes = dados.observacoes

    db.commit()
    db.refresh(registro)

    return RegistroAcessoDetalhado.model_validate(registro)


# ============================================================================
# ESTATÍSTICAS DE REGISTROS
# ============================================================================

@router.get("/registros/count/hoje")
def contar_registros_hoje_endpoint(
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(obter_usuario_atual)
):
    """
    Conta registros de hoje por tipo

    Returns:
        Dict com totais de entradas, saídas e total

    Requer: Autenticação
    """
    return contar_registros_hoje(db)


@router.get("/registros/count/periodo")
def contar_registros_periodo(
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    data_inicio: Optional[datetime] = None,
    data_fim: Optional[datetime] = None
):
    """
    Conta registros em período específico

    Query parameters:
    - **data_inicio**: Data/hora de início (default: início do mês)
    - **data_fim**: Data/hora de fim (default: agora)

    Requer: Autenticação
    """
    if data_inicio is None:
        # Primeiro dia do mês atual
        hoje = datetime.now()
        data_inicio = datetime(hoje.year, hoje.month, 1)

    if data_fim is None:
        data_fim = datetime.now()

    # Total
    total = db.query(RegistroAcesso).filter(
        and_(
            RegistroAcesso.data_hora >= data_inicio,
            RegistroAcesso.data_hora <= data_fim
        )
    ).count()

    # Entradas
    entradas = db.query(RegistroAcesso).filter(
        and_(
            RegistroAcesso.data_hora >= data_inicio,
            RegistroAcesso.data_hora <= data_fim,
            RegistroAcesso.tipo_movimento == "entrada"
        )
    ).count()

    # Saídas
    saidas = db.query(RegistroAcesso).filter(
        and_(
            RegistroAcesso.data_hora >= data_inicio,
            RegistroAcesso.data_hora <= data_fim,
            RegistroAcesso.tipo_movimento == "saida"
        )
    ).count()

    # Veículos únicos
    veiculos_unicos = db.query(RegistroAcesso.veiculo_id).filter(
        and_(
            RegistroAcesso.data_hora >= data_inicio,
            RegistroAcesso.data_hora <= data_fim,
            RegistroAcesso.veiculo_id.isnot(None)
        )
    ).distinct().count()

    return {
        "data_inicio": data_inicio,
        "data_fim": data_fim,
        "total": total,
        "entradas": entradas,
        "saidas": saidas,
        "veiculos_unicos": veiculos_unicos
    }


@router.get("/registros/historico/placa/{placa}")
def obter_historico_placa(
    placa: str,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    limite: int = Query(50, ge=1, le=200)
):
    """
    Obtém histórico completo de uma placa

    Requer: Autenticação
    """
    placa_limpa = placa.upper().replace("-", "").replace(" ", "")

    registros = db.query(RegistroAcesso).filter(
        RegistroAcesso.placa_detectada == placa_limpa
    ).order_by(desc(RegistroAcesso.data_hora)).limit(limite).all()

    if not registros:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Nenhum registro encontrado para placa {placa}"
        )

    return {
        "placa": placa_limpa,
        "total_registros": len(registros),
        "registros": [RegistroAcessoDetalhado.model_validate(r) for r in registros]
    }


@router.get("/registros/ultimos/por-hora")
def registros_por_hora(
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    horas: int = Query(24, ge=1, le=168)
):
    """
    Agrupa registros por hora nas últimas X horas

    Query parameters:
    - **horas**: Número de horas para análise (default: 24, max: 168 = 1 semana)

    Requer: Autenticação
    """
    data_limite = datetime.now() - timedelta(hours=horas)

    # Agrupa por hora
    resultados = db.query(
        func.strftime('%Y-%m-%d %H:00:00', RegistroAcesso.data_hora).label('hora'),
        func.count(RegistroAcesso.id).label('total'),
        func.sum(func.case((RegistroAcesso.tipo_movimento == 'entrada', 1), else_=0)).label('entradas'),
        func.sum(func.case((RegistroAcesso.tipo_movimento == 'saida', 1), else_=0)).label('saidas')
    ).filter(
        RegistroAcesso.data_hora >= data_limite
    ).group_by(
        func.strftime('%Y-%m-%d %H:00:00', RegistroAcesso.data_hora)
    ).all()

    return [
        {
            "hora": hora,
            "total": total,
            "entradas": entradas,
            "saidas": saidas
        }
        for hora, total, entradas, saidas in resultados
    ]
