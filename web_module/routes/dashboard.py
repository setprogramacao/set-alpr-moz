"""
Rotas de Dashboard - Sistema ALPR UNIPIAGET
Estatísticas, KPIs e dados para o dashboard principal
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc
from datetime import datetime, timedelta
from typing import List

from web_module.database import get_db
from web_module.models import Veiculo, Proprietario, RegistroAcesso, Usuario
from web_module.routes.auth import obter_usuario_atual
from web_module.services.deteccao_service import obter_veiculos_no_campus, contar_veiculos_no_campus
from shared.schemas import EstatisticasDashboard, VeiculoNoCampus, AlertaProprietario
from shared.utils import calcular_tempo_permanencia, formatar_tempo_permanencia

router = APIRouter()


# ============================================================================
# ESTATÍSTICAS PRINCIPAIS
# ============================================================================

@router.get("/dashboard/estatisticas", response_model=EstatisticasDashboard)
def obter_estatisticas_dashboard(
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(obter_usuario_atual)
):
    """
    Retorna estatísticas principais para o dashboard

    - Total de veículos cadastrados
    - Total de proprietários
    - Registros de hoje e do mês
    - Veículos atualmente no campus
    - Entradas e saídas de hoje
    - Taxa de ocupação
    - Registros por categoria
    - Registros por hora do dia

    Requer: Autenticação
    """
    # Datas de referência
    hoje_inicio = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    mes_inicio = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Contagens básicas
    total_veiculos = db.query(Veiculo).count()
    total_proprietarios = db.query(Proprietario).filter(Proprietario.ativo == True).count()

    # Registros de hoje
    total_registros_hoje = db.query(RegistroAcesso).filter(
        RegistroAcesso.data_hora >= hoje_inicio
    ).count()

    entradas_hoje = db.query(RegistroAcesso).filter(
        and_(
            RegistroAcesso.data_hora >= hoje_inicio,
            RegistroAcesso.tipo_movimento == "entrada"
        )
    ).count()

    saidas_hoje = db.query(RegistroAcesso).filter(
        and_(
            RegistroAcesso.data_hora >= hoje_inicio,
            RegistroAcesso.tipo_movimento == "saida"
        )
    ).count()

    # Registros do mês
    total_registros_mes = db.query(RegistroAcesso).filter(
        RegistroAcesso.data_hora >= mes_inicio
    ).count()

    # Veículos no campus
    veiculos_no_campus = contar_veiculos_no_campus(db)

    # Taxa de ocupação (assume capacidade máxima de 100 veículos)
    capacidade_maxima = 100
    taxa_ocupacao = (veiculos_no_campus / capacidade_maxima * 100) if capacidade_maxima > 0 else 0

    # Registros por categoria (hoje)
    registros_por_categoria_query = db.query(
        Proprietario.categoria,
        func.count(RegistroAcesso.id).label("total")
    ).join(
        Veiculo, Veiculo.proprietario_id == Proprietario.id
    ).join(
        RegistroAcesso, RegistroAcesso.veiculo_id == Veiculo.id
    ).filter(
        RegistroAcesso.data_hora >= hoje_inicio
    ).group_by(Proprietario.categoria).all()

    registros_por_categoria = {
        categoria: total for categoria, total in registros_por_categoria_query
    }

    # Registros por hora (últimas 24 horas)
    vinte_quatro_horas_atras = datetime.now() - timedelta(hours=24)

    registros_por_hora_query = db.query(
        func.strftime('%H', RegistroAcesso.data_hora).label('hora'),
        func.count(RegistroAcesso.id).label('total')
    ).filter(
        RegistroAcesso.data_hora >= vinte_quatro_horas_atras
    ).group_by(
        func.strftime('%H', RegistroAcesso.data_hora)
    ).all()

    registros_por_hora = [
        {"hora": int(hora), "total": total}
        for hora, total in registros_por_hora_query
    ]

    return EstatisticasDashboard(
        total_veiculos_cadastrados=total_veiculos,
        total_proprietarios=total_proprietarios,
        total_registros_hoje=total_registros_hoje,
        total_registros_mes=total_registros_mes,
        veiculos_no_campus=veiculos_no_campus,
        entradas_hoje=entradas_hoje,
        saidas_hoje=saidas_hoje,
        taxa_ocupacao=round(taxa_ocupacao, 2),
        registros_por_categoria=registros_por_categoria,
        registros_por_hora=registros_por_hora
    )


# ============================================================================
# VEÍCULOS NO CAMPUS
# ============================================================================

@router.get("/dashboard/veiculos-no-campus", response_model=List[VeiculoNoCampus])
def listar_veiculos_no_campus(
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(obter_usuario_atual)
):
    """
    Lista veículos atualmente no campus

    Retorna veículos cuja última movimentação foi "entrada"

    Requer: Autenticação
    """
    veiculos_no_campus = obter_veiculos_no_campus(db)

    resultado = []
    for item in veiculos_no_campus:
        from shared.schemas import VeiculoComProprietario

        veiculo_schema = VeiculoComProprietario.model_validate(item["veiculo"])
        tempo_minutos = item["tempo_permanencia_minutos"]
        tempo_formatado = formatar_tempo_permanencia(tempo_minutos)

        resultado.append(VeiculoNoCampus(
            veiculo=veiculo_schema,
            hora_entrada=item["hora_entrada"],
            tempo_permanencia=tempo_minutos,
            tempo_formatado=tempo_formatado
        ))

    return resultado


# ============================================================================
# ALERTAS E NOTIFICAÇÕES
# ============================================================================

@router.get("/dashboard/alertas", response_model=List[AlertaProprietario])
def obter_alertas(
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(obter_usuario_atual)
):
    """
    Gera alertas sobre comportamento de proprietários

    Tipos de alertas:
    - **ausencia_prolongada**: Docente sem registros há mais de X dias
    - **saida_precoce**: Saída antes do horário normal
    - **permanencia_curta**: Tempo no campus muito curto

    Requer: Autenticação
    """
    alertas = []

    # Data de referência (últimos 7 dias)
    sete_dias_atras = datetime.now() - timedelta(days=7)
    hoje_inicio = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    # 1. Docentes sem registros nos últimos 3 dias
    tres_dias_atras = datetime.now() - timedelta(days=3)

    docentes = db.query(Proprietario).filter(
        and_(
            Proprietario.categoria == "docente",
            Proprietario.ativo == True
        )
    ).all()

    for docente in docentes:
        # Verifica se tem veículos cadastrados
        if not docente.veiculos:
            continue

        # Busca último registro de qualquer veículo do docente
        veiculo_ids = [v.id for v in docente.veiculos]

        ultimo_registro = db.query(RegistroAcesso).filter(
            RegistroAcesso.veiculo_id.in_(veiculo_ids)
        ).order_by(desc(RegistroAcesso.data_hora)).first()

        if not ultimo_registro or ultimo_registro.data_hora < tres_dias_atras:
            from shared.schemas import ProprietarioResponse, VeiculoResponse

            alertas.append(AlertaProprietario(
                proprietario=ProprietarioResponse.model_validate(docente),
                veiculo=VeiculoResponse.model_validate(docente.veiculos[0]) if docente.veiculos else None,
                tipo_alerta="ausencia_prolongada",
                descricao=f"Sem registros há mais de 3 dias (última: {ultimo_registro.data_hora.strftime('%d/%m/%Y') if ultimo_registro else 'nunca'})",
                data_hora=ultimo_registro.data_hora if ultimo_registro else datetime.now(),
                severidade="alta"
            ))

    # 2. Permanências muito curtas hoje (menos de 1 hora para docentes)
    veiculos_hoje = obter_veiculos_no_campus(db)

    for item in veiculos_hoje:
        veiculo = item["veiculo"]
        proprietario = item["proprietario"]
        tempo_minutos = item["tempo_permanencia_minutos"]

        # Se for docente e tempo < 60 minutos
        if proprietario.categoria == "docente" and tempo_minutos < 60:
            from shared.schemas import ProprietarioResponse, VeiculoResponse

            alertas.append(AlertaProprietario(
                proprietario=ProprietarioResponse.model_validate(proprietario),
                veiculo=VeiculoResponse.model_validate(veiculo),
                tipo_alerta="permanencia_curta",
                descricao=f"No campus há apenas {formatar_tempo_permanencia(tempo_minutos)}",
                data_hora=item["hora_entrada"],
                severidade="media"
            ))

    # Limita a 20 alertas mais recentes
    alertas = sorted(alertas, key=lambda x: x.data_hora, reverse=True)[:20]

    return alertas


# ============================================================================
# ATIVIDADE RECENTE
# ============================================================================

@router.get("/dashboard/atividade-recente")
def obter_atividade_recente(
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    limite: int = 10
):
    """
    Obtém atividade recente do sistema

    Query parameters:
    - **limite**: Número de registros (default: 10)

    Requer: Autenticação
    """
    from shared.schemas import RegistroAcessoDetalhado

    registros = db.query(RegistroAcesso).order_by(
        desc(RegistroAcesso.data_hora)
    ).limit(limite).all()

    return [RegistroAcessoDetalhado.model_validate(r) for r in registros]


# ============================================================================
# TOP PROPRIETÁRIOS
# ============================================================================

@router.get("/dashboard/top-proprietarios")
def obter_top_proprietarios(
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    limite: int = 10,
    periodo_dias: int = 30
):
    """
    Retorna proprietários com mais acessos no período

    Query parameters:
    - **limite**: Número de proprietários (default: 10)
    - **periodo_dias**: Dias para análise (default: 30)

    Requer: Autenticação
    """
    data_limite = datetime.now() - timedelta(days=periodo_dias)

    # Agrupa por proprietário e conta registros
    resultados = db.query(
        Proprietario.id,
        Proprietario.nome,
        Proprietario.categoria,
        Proprietario.departamento,
        func.count(RegistroAcesso.id).label('total_acessos')
    ).join(
        Veiculo, Veiculo.proprietario_id == Proprietario.id
    ).join(
        RegistroAcesso, RegistroAcesso.veiculo_id == Veiculo.id
    ).filter(
        RegistroAcesso.data_hora >= data_limite
    ).group_by(
        Proprietario.id
    ).order_by(
        desc('total_acessos')
    ).limit(limite).all()

    return [
        {
            "proprietario_id": prop_id,
            "nome": nome,
            "categoria": categoria,
            "departamento": departamento,
            "total_acessos": total_acessos
        }
        for prop_id, nome, categoria, departamento, total_acessos in resultados
    ]


# ============================================================================
# GRÁFICOS E ANÁLISES
# ============================================================================

@router.get("/dashboard/grafico-semanal")
def obter_grafico_semanal(
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(obter_usuario_atual)
):
    """
    Dados para gráfico de acessos dos últimos 7 dias

    Requer: Autenticação
    """
    sete_dias_atras = datetime.now() - timedelta(days=7)

    # Agrupa por dia
    resultados = db.query(
        func.date(RegistroAcesso.data_hora).label('dia'),
        func.count(RegistroAcesso.id).label('total'),
        func.sum(func.case((RegistroAcesso.tipo_movimento == 'entrada', 1), else_=0)).label('entradas'),
        func.sum(func.case((RegistroAcesso.tipo_movimento == 'saida', 1), else_=0)).label('saidas')
    ).filter(
        RegistroAcesso.data_hora >= sete_dias_atras
    ).group_by(
        func.date(RegistroAcesso.data_hora)
    ).all()

    return [
        {
            "dia": str(dia),
            "total": total,
            "entradas": entradas,
            "saidas": saidas
        }
        for dia, total, entradas, saidas in resultados
    ]


@router.get("/dashboard/distribuicao-categorias")
def obter_distribuicao_categorias(
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(obter_usuario_atual)
):
    """
    Distribuição de registros por categoria de proprietário

    Requer: Autenticação
    """
    hoje_inicio = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    resultados = db.query(
        Proprietario.categoria,
        func.count(RegistroAcesso.id).label('total')
    ).join(
        Veiculo, Veiculo.proprietario_id == Proprietario.id
    ).join(
        RegistroAcesso, RegistroAcesso.veiculo_id == Veiculo.id
    ).filter(
        RegistroAcesso.data_hora >= hoje_inicio
    ).group_by(
        Proprietario.categoria
    ).all()

    return [
        {
            "categoria": categoria,
            "total": total
        }
        for categoria, total in resultados
    ]
