"""
Rotas de Relatórios - Sistema ALPR UNIPIAGET
Geração de relatórios em diversos formatos (JSON, CSV, PDF)
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc
from datetime import datetime, timedelta
from typing import Optional, List
import csv
import io

from web_module.database import get_db
from web_module.models import Veiculo, Proprietario, RegistroAcesso, Usuario
from web_module.routes.auth import obter_usuario_atual
from shared.schemas import (
    FiltroRelatorio,
    RelatorioProprietario,
    RelatorioVeiculo,
)
from shared.utils import calcular_tempo_permanencia, formatar_tempo_permanencia

router = APIRouter()


# ============================================================================
# RELATÓRIOS DE PROPRIETÁRIOS
# ============================================================================

@router.post("/relatorios/proprietarios", response_model=List[RelatorioProprietario])
def gerar_relatorio_proprietarios(
    filtro: FiltroRelatorio,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(obter_usuario_atual)
):
    """
    Gera relatório detalhado de proprietários

    Filtros disponíveis:
    - **data_inicio**: Data de início do período
    - **data_fim**: Data de fim do período
    - **proprietario_id**: Proprietário específico
    - **categoria**: Filtrar por categoria (docente, tecnico, etc)
    - **departamento**: Filtrar por departamento

    Returns:
        Lista de relatórios por proprietário com estatísticas de acesso

    Requer: Autenticação
    """
    # Define período padrão se não fornecido
    if not filtro.data_inicio:
        filtro.data_inicio = datetime.now() - timedelta(days=30)
    if not filtro.data_fim:
        filtro.data_fim = datetime.now()

    # Query base de proprietários
    query_prop = db.query(Proprietario).filter(Proprietario.ativo == True)

    if filtro.proprietario_id:
        query_prop = query_prop.filter(Proprietario.id == filtro.proprietario_id)
    if filtro.categoria:
        query_prop = query_prop.filter(Proprietario.categoria == filtro.categoria)
    if filtro.departamento:
        query_prop = query_prop.filter(Proprietario.departamento.contains(filtro.departamento))

    proprietarios = query_prop.all()
    relatorios = []

    for proprietario in proprietarios:
        # Busca veículos do proprietário
        veiculos = proprietario.veiculos
        if not veiculos:
            continue

        veiculo_ids = [v.id for v in veiculos]

        # Busca registros no período
        registros = db.query(RegistroAcesso).filter(
            and_(
                RegistroAcesso.veiculo_id.in_(veiculo_ids),
                RegistroAcesso.data_hora >= filtro.data_inicio,
                RegistroAcesso.data_hora <= filtro.data_fim
            )
        ).all()

        if not registros:
            continue

        # Calcula estatísticas
        entradas = [r for r in registros if r.tipo_movimento == "entrada"]
        saidas = [r for r in registros if r.tipo_movimento == "saida"]

        total_entradas = len(entradas)
        total_saidas = len(saidas)

        # Calcula tempo de permanência (pareamento entrada-saída)
        tempos_permanencia = []
        dias_presentes_set = set()

        for entrada in entradas:
            dias_presentes_set.add(entrada.data_hora.date())

            # Busca saída correspondente (mesma placa, após entrada)
            saida_correspondente = None
            for saida in saidas:
                if (saida.veiculo_id == entrada.veiculo_id and
                    saida.data_hora > entrada.data_hora):
                    saida_correspondente = saida
                    break

            if saida_correspondente:
                tempo = calcular_tempo_permanencia(entrada.data_hora, saida_correspondente.data_hora)
                tempos_permanencia.append(tempo)

        tempo_total = sum(tempos_permanencia)
        tempo_medio = tempo_total / len(tempos_permanencia) if tempos_permanencia else 0

        # Última entrada e saída
        ultima_entrada = max([e.data_hora for e in entradas]) if entradas else None
        ultima_saida = max([s.data_hora for s in saidas]) if saidas else None

        # Veículos utilizados
        from shared.schemas import VeiculoResponse
        veiculos_utilizados = [VeiculoResponse.model_validate(v) for v in veiculos]

        from shared.schemas import ProprietarioResponse
        relatorios.append(RelatorioProprietario(
            proprietario=ProprietarioResponse.model_validate(proprietario),
            total_entradas=total_entradas,
            total_saidas=total_saidas,
            tempo_total_permanencia=tempo_total,
            tempo_medio_permanencia=tempo_medio,
            dias_presentes=len(dias_presentes_set),
            ultima_entrada=ultima_entrada,
            ultima_saida=ultima_saida,
            veiculos_utilizados=veiculos_utilizados
        ))

    # Ordena por total de entradas (decrescente)
    relatorios.sort(key=lambda x: x.total_entradas, reverse=True)

    return relatorios


# ============================================================================
# RELATÓRIOS DE VEÍCULOS
# ============================================================================

@router.post("/relatorios/veiculos", response_model=List[RelatorioVeiculo])
def gerar_relatorio_veiculos(
    filtro: FiltroRelatorio,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(obter_usuario_atual)
):
    """
    Gera relatório detalhado de veículos

    Filtros disponíveis:
    - **data_inicio**: Data de início do período
    - **data_fim**: Data de fim do período
    - **veiculo_id**: Veículo específico
    - **proprietario_id**: Filtrar por proprietário

    Returns:
        Lista de relatórios por veículo com estatísticas de acesso

    Requer: Autenticação
    """
    # Define período padrão se não fornecido
    if not filtro.data_inicio:
        filtro.data_inicio = datetime.now() - timedelta(days=30)
    if not filtro.data_fim:
        filtro.data_fim = datetime.now()

    # Query base de veículos
    query_veic = db.query(Veiculo)

    if filtro.veiculo_id:
        query_veic = query_veic.filter(Veiculo.id == filtro.veiculo_id)
    if filtro.proprietario_id:
        query_veic = query_veic.filter(Veiculo.proprietario_id == filtro.proprietario_id)

    veiculos = query_veic.all()
    relatorios = []

    for veiculo in veiculos:
        # Busca registros no período
        registros = db.query(RegistroAcesso).filter(
            and_(
                RegistroAcesso.veiculo_id == veiculo.id,
                RegistroAcesso.data_hora >= filtro.data_inicio,
                RegistroAcesso.data_hora <= filtro.data_fim
            )
        ).all()

        if not registros:
            continue

        # Estatísticas
        total_acessos = len(registros)
        entradas = [r for r in registros if r.tipo_movimento == "entrada"]
        saidas = [r for r in registros if r.tipo_movimento == "saida"]

        total_entradas = len(entradas)
        total_saidas = len(saidas)

        primeira_deteccao = min([r.data_hora for r in registros])
        ultima_deteccao = max([r.data_hora for r in registros])

        # Confiança média OCR
        confianca_media = sum([r.confianca_ocr for r in registros]) / len(registros)

        from shared.schemas import VeiculoComProprietario
        relatorios.append(RelatorioVeiculo(
            veiculo=VeiculoComProprietario.model_validate(veiculo),
            total_acessos=total_acessos,
            total_entradas=total_entradas,
            total_saidas=total_saidas,
            primeira_deteccao=primeira_deteccao,
            ultima_deteccao=ultima_deteccao,
            confianca_media=confianca_media
        ))

    # Ordena por total de acessos (decrescente)
    relatorios.sort(key=lambda x: x.total_acessos, reverse=True)

    return relatorios


# ============================================================================
# EXPORTAÇÃO CSV - REGISTROS
# ============================================================================

@router.get("/relatorios/exportar/registros")
def exportar_registros_csv(
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    data_inicio: Optional[datetime] = None,
    data_fim: Optional[datetime] = None,
    tipo_movimento: Optional[str] = None
):
    """
    Exporta registros em formato CSV

    Query parameters:
    - **data_inicio**: Data de início (default: último mês)
    - **data_fim**: Data de fim (default: agora)
    - **tipo_movimento**: Filtrar por "entrada" ou "saida"

    Returns:
        Arquivo CSV para download

    Requer: Autenticação
    """
    # Define período padrão
    if not data_inicio:
        data_inicio = datetime.now() - timedelta(days=30)
    if not data_fim:
        data_fim = datetime.now()

    # Query registros
    query = db.query(RegistroAcesso).filter(
        and_(
            RegistroAcesso.data_hora >= data_inicio,
            RegistroAcesso.data_hora <= data_fim
        )
    )

    if tipo_movimento:
        query = query.filter(RegistroAcesso.tipo_movimento == tipo_movimento)

    registros = query.order_by(desc(RegistroAcesso.data_hora)).all()

    # Cria CSV em memória
    output = io.StringIO()
    writer = csv.writer(output)

    # Cabeçalho
    writer.writerow([
        "ID",
        "Data/Hora",
        "Placa",
        "Tipo Movimento",
        "Proprietário",
        "Categoria",
        "Departamento",
        "Modelo Veículo",
        "Confiança OCR",
        "Método OCR"
    ])

    # Dados
    for registro in registros:
        veiculo = registro.veiculo
        proprietario_nome = veiculo.proprietario.nome if veiculo and veiculo.proprietario else "Não cadastrado"
        categoria = veiculo.proprietario.categoria if veiculo and veiculo.proprietario else "-"
        departamento = veiculo.proprietario.departamento if veiculo and veiculo.proprietario else "-"
        modelo = veiculo.modelo if veiculo else "-"

        writer.writerow([
            registro.id,
            registro.data_hora.strftime("%d/%m/%Y %H:%M:%S"),
            registro.placa_detectada,
            registro.tipo_movimento.upper(),
            proprietario_nome,
            categoria,
            departamento,
            modelo,
            f"{registro.confianca_ocr:.2%}",
            registro.metodo_ocr
        ])

    # Prepara resposta
    output.seek(0)
    filename = f"registros_{data_inicio.strftime('%Y%m%d')}_{data_fim.strftime('%Y%m%d')}.csv"

    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8-sig')),  # BOM para Excel
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ============================================================================
# EXPORTAÇÃO CSV - PROPRIETÁRIOS
# ============================================================================

@router.get("/relatorios/exportar/proprietarios")
def exportar_proprietarios_csv(
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    data_inicio: Optional[datetime] = None,
    data_fim: Optional[datetime] = None,
    categoria: Optional[str] = None
):
    """
    Exporta relatório de proprietários em formato CSV

    Query parameters:
    - **data_inicio**: Data de início (default: último mês)
    - **data_fim**: Data de fim (default: agora)
    - **categoria**: Filtrar por categoria

    Returns:
        Arquivo CSV para download

    Requer: Autenticação
    """
    # Define período padrão
    if not data_inicio:
        data_inicio = datetime.now() - timedelta(days=30)
    if not data_fim:
        data_fim = datetime.now()

    # Gera relatório
    filtro = FiltroRelatorio(
        data_inicio=data_inicio,
        data_fim=data_fim,
        categoria=categoria
    )

    relatorios = gerar_relatorio_proprietarios(filtro, db, usuario_atual)

    # Cria CSV em memória
    output = io.StringIO()
    writer = csv.writer(output)

    # Cabeçalho
    writer.writerow([
        "Nome",
        "Categoria",
        "Departamento",
        "Email",
        "Telefone",
        "Total Entradas",
        "Total Saídas",
        "Dias Presentes",
        "Tempo Total (min)",
        "Tempo Médio (min)",
        "Última Entrada",
        "Última Saída"
    ])

    # Dados
    for relatorio in relatorios:
        prop = relatorio.proprietario
        writer.writerow([
            prop.nome,
            prop.categoria,
            prop.departamento or "-",
            prop.email or "-",
            prop.telefone or "-",
            relatorio.total_entradas,
            relatorio.total_saidas,
            relatorio.dias_presentes,
            relatorio.tempo_total_permanencia,
            f"{relatorio.tempo_medio_permanencia:.1f}",
            relatorio.ultima_entrada.strftime("%d/%m/%Y %H:%M") if relatorio.ultima_entrada else "-",
            relatorio.ultima_saida.strftime("%d/%m/%Y %H:%M") if relatorio.ultima_saida else "-"
        ])

    # Prepara resposta
    output.seek(0)
    filename = f"relatorio_proprietarios_{data_inicio.strftime('%Y%m%d')}_{data_fim.strftime('%Y%m%d')}.csv"

    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8-sig')),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ============================================================================
# RELATÓRIO RESUMIDO
# ============================================================================

@router.get("/relatorios/resumo")
def obter_resumo_periodo(
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    data_inicio: Optional[datetime] = None,
    data_fim: Optional[datetime] = None
):
    """
    Gera resumo estatístico do período

    Query parameters:
    - **data_inicio**: Data de início (default: último mês)
    - **data_fim**: Data de fim (default: agora)

    Returns:
        Resumo com estatísticas gerais

    Requer: Autenticação
    """
    # Define período padrão
    if not data_inicio:
        data_inicio = datetime.now() - timedelta(days=30)
    if not data_fim:
        data_fim = datetime.now()

    # Estatísticas gerais
    total_registros = db.query(RegistroAcesso).filter(
        and_(
            RegistroAcesso.data_hora >= data_inicio,
            RegistroAcesso.data_hora <= data_fim
        )
    ).count()

    total_entradas = db.query(RegistroAcesso).filter(
        and_(
            RegistroAcesso.data_hora >= data_inicio,
            RegistroAcesso.data_hora <= data_fim,
            RegistroAcesso.tipo_movimento == "entrada"
        )
    ).count()

    total_saidas = db.query(RegistroAcesso).filter(
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

    # Confiança média OCR
    confianca_media_result = db.query(
        func.avg(RegistroAcesso.confianca_ocr)
    ).filter(
        and_(
            RegistroAcesso.data_hora >= data_inicio,
            RegistroAcesso.data_hora <= data_fim
        )
    ).scalar()

    confianca_media = float(confianca_media_result) if confianca_media_result else 0.0

    # Registros por categoria
    registros_por_categoria = db.query(
        Proprietario.categoria,
        func.count(RegistroAcesso.id).label("total")
    ).join(
        Veiculo, Veiculo.proprietario_id == Proprietario.id
    ).join(
        RegistroAcesso, RegistroAcesso.veiculo_id == Veiculo.id
    ).filter(
        and_(
            RegistroAcesso.data_hora >= data_inicio,
            RegistroAcesso.data_hora <= data_fim
        )
    ).group_by(Proprietario.categoria).all()

    return {
        "periodo": {
            "data_inicio": data_inicio,
            "data_fim": data_fim,
            "dias": (data_fim - data_inicio).days
        },
        "totais": {
            "registros": total_registros,
            "entradas": total_entradas,
            "saidas": total_saidas,
            "veiculos_unicos": veiculos_unicos
        },
        "qualidade": {
            "confianca_media_ocr": round(confianca_media, 3)
        },
        "por_categoria": {
            categoria: total for categoria, total in registros_por_categoria
        }
    }
