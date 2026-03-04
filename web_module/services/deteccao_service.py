"""
Serviço de Detecção - Sistema ALPR UNIPIAGET
Processa detecções de placas enviadas pelo módulo Desktop
"""

from datetime import datetime, timedelta
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc

from web_module.models import Veiculo, RegistroAcesso, Proprietario
from shared.schemas import DeteccaoRequest, DeteccaoResponse, VeiculoComProprietario
from shared.utils import validar_placa_mocambique, salvar_imagem_deteccao, base64_para_imagem


# ============================================================================
# CONFIGURAÇÕES
# ============================================================================

INTERVALO_DUPLICATA_MINUTOS = 5  # Intervalo mínimo para considerar duplicata


# ============================================================================
# PROCESSAMENTO DE DETECÇÕES
# ============================================================================

def processar_deteccao(db: Session, deteccao: DeteccaoRequest, salvar_imagem: bool = True) -> DeteccaoResponse:
    """
    Processa detecção de placa recebida do módulo Desktop

    Fluxo:
    1. Valida placa detectada
    2. Busca veículo no banco
    3. Verifica duplicata temporal
    4. Salva imagem (se fornecida)
    5. Registra acesso no banco
    6. Retorna resposta com status

    Args:
        db: Sessão do banco
        deteccao: Dados da detecção
        salvar_imagem: Se deve salvar imagem

    Returns:
        DeteccaoResponse com resultado do processamento
    """
    # Valida formato da placa
    placa_valida, placa_limpa = validar_placa_mocambique(deteccao.placa_detectada)

    if not placa_valida:
        return DeteccaoResponse(
            sucesso=False,
            mensagem=f"Placa inválida: {deteccao.placa_detectada}",
            registro_id=None,
            veiculo_cadastrado=False,
            duplicata=False
        )

    # Busca veículo cadastrado
    veiculo = buscar_veiculo_por_placa(db, placa_limpa)
    veiculo_cadastrado = veiculo is not None

    # Determina automaticamente o tipo de movimento pela lógica de alternância
    # (ignora o tipo enviado pelo desktop — o histórico da placa é a fonte da verdade)
    tipo_movimento_real = determinar_tipo_movimento(
        db, placa_limpa, veiculo.id if veiculo else None
    )

    # Verifica duplicata temporal (cobre placas cadastradas e não cadastradas)
    eh_duplicata, tempo_desde_ultimo = verificar_duplicata(
        db, placa_limpa, veiculo.id if veiculo else None, INTERVALO_DUPLICATA_MINUTOS
    )

    # Se for duplicata, não registra novamente
    if eh_duplicata:
        # Busca dados do veículo para resposta
        veiculo_response = None
        if veiculo:
            veiculo_response = VeiculoComProprietario.model_validate(veiculo)

        return DeteccaoResponse(
            sucesso=False,
            mensagem=f"Registro duplicado. Última detecção há {tempo_desde_ultimo} segundos",
            registro_id=None,
            veiculo_cadastrado=veiculo_cadastrado,
            veiculo=veiculo_response,
            duplicata=True,
            tempo_desde_ultimo_registro=tempo_desde_ultimo
        )

    # Salva imagem se fornecida
    imagem_path = None
    if salvar_imagem and deteccao.imagem_base64:
        try:
            imagem = base64_para_imagem(deteccao.imagem_base64)
            if imagem is not None:
                imagem_path = salvar_imagem_deteccao(
                    imagem,
                    placa_limpa,
                    timestamp=deteccao.timestamp
                )
        except Exception as e:
            print(f"Erro ao salvar imagem: {e}")
            # Continua mesmo se falhar ao salvar imagem

    # Registra acesso no banco usando o tipo determinado automaticamente
    registro = registrar_acesso(
        db=db,
        veiculo_id=veiculo.id if veiculo else None,
        placa_detectada=placa_limpa,
        tipo_movimento=tipo_movimento_real,
        confianca_ocr=deteccao.confianca_ocr,
        metodo_ocr=deteccao.metodo_ocr,
        imagem_path=imagem_path,
        data_hora=deteccao.timestamp
    )

    # Prepara resposta
    veiculo_response = None
    if veiculo:
        veiculo_response = VeiculoComProprietario.model_validate(veiculo)

    tipo_label = "ENTRADA" if tipo_movimento_real == "entrada" else "SAÍDA"
    mensagem = f"Detecção registrada [{tipo_label}]"
    if veiculo_cadastrado:
        proprietario = veiculo.proprietario
        mensagem += f" - {proprietario.nome} ({proprietario.categoria})"
    else:
        mensagem += " - Veículo não cadastrado"

    return DeteccaoResponse(
        sucesso=True,
        mensagem=mensagem,
        registro_id=registro.id,
        veiculo_cadastrado=veiculo_cadastrado,
        veiculo=veiculo_response,
        duplicata=False,
        tempo_desde_ultimo_registro=tempo_desde_ultimo
    )


# ============================================================================
# CONSULTAS DE VEÍCULOS
# ============================================================================

def buscar_veiculo_por_placa(db: Session, placa: str) -> Optional[Veiculo]:
    """
    Busca veículo cadastrado por placa

    Args:
        db: Sessão do banco
        placa: Placa do veículo (limpa, sem hífens)

    Returns:
        Veiculo ou None se não encontrado
    """
    return db.query(Veiculo).filter(Veiculo.placa == placa).first()


def buscar_veiculo_por_id(db: Session, veiculo_id: int) -> Optional[Veiculo]:
    """
    Busca veículo por ID

    Args:
        db: Sessão do banco
        veiculo_id: ID do veículo

    Returns:
        Veiculo ou None
    """
    return db.query(Veiculo).filter(Veiculo.id == veiculo_id).first()


# ============================================================================
# LÓGICA DE TIPO DE MOVIMENTO (TOGGLE POR PLACA)
# ============================================================================

def determinar_tipo_movimento(db: Session, placa: str, veiculo_id: Optional[int] = None) -> str:
    """
    Determina automaticamente o tipo de movimento para uma placa.

    Regra: o próximo movimento é sempre o oposto do último registrado para
    aquela placa. Se não houver registro anterior, assume-se "entrada".

    Args:
        db: Sessão do banco
        placa: Placa detectada (limpa, sem hífens)
        veiculo_id: ID do veículo cadastrado (se existir)

    Returns:
        "entrada" ou "saida"
    """
    ultimo = obter_ultimo_registro_placa(db, placa, veiculo_id)

    if not ultimo:
        return "entrada"  # primeiro registo da placa é sempre entrada

    return "saida" if ultimo.tipo_movimento == "entrada" else "entrada"


def obter_ultimo_registro_placa(
    db: Session,
    placa: str,
    veiculo_id: Optional[int] = None
) -> Optional[RegistroAcesso]:
    """
    Obtém o último registro de acesso de uma placa (cadastrada ou não).

    Prioriza a busca por veiculo_id quando disponível para consistência,
    mas também verifica por placa_detectada para cobrir registros antigos
    sem vínculo de veículo.

    Args:
        db: Sessão do banco
        placa: Placa detectada
        veiculo_id: ID do veículo (opcional)

    Returns:
        RegistroAcesso mais recente ou None
    """
    if veiculo_id:
        # Busca por ID do veículo (mais preciso para veículos cadastrados)
        return db.query(RegistroAcesso).filter(
            RegistroAcesso.veiculo_id == veiculo_id
        ).order_by(desc(RegistroAcesso.data_hora)).first()

    # Para veículos não cadastrados, busca pela placa detectada
    return db.query(RegistroAcesso).filter(
        RegistroAcesso.placa_detectada == placa
    ).order_by(desc(RegistroAcesso.data_hora)).first()


# ============================================================================
# VERIFICAÇÕES DE DUPLICATA
# ============================================================================

def verificar_duplicata(db: Session, placa: str, veiculo_id: Optional[int], intervalo_minutos: int = 5) -> Tuple[bool, Optional[int]]:
    """
    Verifica se existe registro recente da placa (duplicata temporal).

    Funciona tanto para veículos cadastrados quanto para não cadastrados.

    Args:
        db: Sessão do banco
        placa: Placa detectada
        veiculo_id: ID do veículo (None se não cadastrado)
        intervalo_minutos: Intervalo mínimo em minutos para considerar duplicata

    Returns:
        Tupla (eh_duplicata: bool, segundos_desde_ultimo: Optional[int])
    """
    ultimo_registro = obter_ultimo_registro_placa(db, placa, veiculo_id)

    if not ultimo_registro:
        return False, None

    agora = datetime.now()
    delta = agora - ultimo_registro.data_hora
    segundos = int(delta.total_seconds())

    eh_duplicata = segundos < (intervalo_minutos * 60)

    return eh_duplicata, segundos


def obter_ultimo_registro_veiculo(db: Session, veiculo_id: int) -> Optional[RegistroAcesso]:
    """
    Obtém último registro de acesso de um veículo cadastrado.

    Args:
        db: Sessão do banco
        veiculo_id: ID do veículo

    Returns:
        RegistroAcesso mais recente ou None
    """
    return db.query(RegistroAcesso).filter(
        RegistroAcesso.veiculo_id == veiculo_id
    ).order_by(desc(RegistroAcesso.data_hora)).first()


# ============================================================================
# REGISTRO DE ACESSOS
# ============================================================================

def registrar_acesso(
    db: Session,
    placa_detectada: str,
    tipo_movimento: str,
    confianca_ocr: float,
    metodo_ocr: str,
    veiculo_id: Optional[int] = None,
    imagem_path: Optional[str] = None,
    data_hora: Optional[datetime] = None
) -> RegistroAcesso:
    """
    Cria novo registro de acesso no banco

    Args:
        db: Sessão do banco
        placa_detectada: Placa detectada
        tipo_movimento: "entrada" ou "saida"
        confianca_ocr: Confiança do OCR (0.0 a 1.0)
        metodo_ocr: Método usado ("easyocr", "tesseract", "hibrido")
        veiculo_id: ID do veículo (se cadastrado)
        imagem_path: Caminho da imagem salva
        data_hora: Data/hora da detecção (default: agora)

    Returns:
        RegistroAcesso criado
    """
    if data_hora is None:
        data_hora = datetime.now()

    registro = RegistroAcesso(
        veiculo_id=veiculo_id,
        placa_detectada=placa_detectada,
        tipo_movimento=tipo_movimento,
        data_hora=data_hora,
        confianca_ocr=confianca_ocr,
        metodo_ocr=metodo_ocr,
        imagem_path=imagem_path
    )

    db.add(registro)
    db.commit()
    db.refresh(registro)

    return registro


# ============================================================================
# CONSULTAS DE REGISTROS
# ============================================================================

def obter_registros_veiculo(
    db: Session,
    veiculo_id: int,
    data_inicio: Optional[datetime] = None,
    data_fim: Optional[datetime] = None,
    limite: int = 100
) -> list[RegistroAcesso]:
    """
    Obtém registros de um veículo em período específico

    Args:
        db: Sessão do banco
        veiculo_id: ID do veículo
        data_inicio: Data de início (default: sem limite)
        data_fim: Data de fim (default: agora)
        limite: Número máximo de registros

    Returns:
        Lista de RegistroAcesso
    """
    query = db.query(RegistroAcesso).filter(RegistroAcesso.veiculo_id == veiculo_id)

    if data_inicio:
        query = query.filter(RegistroAcesso.data_hora >= data_inicio)

    if data_fim:
        query = query.filter(RegistroAcesso.data_hora <= data_fim)

    return query.order_by(desc(RegistroAcesso.data_hora)).limit(limite).all()


def obter_registros_hoje(db: Session, limite: int = 100) -> list[RegistroAcesso]:
    """
    Obtém registros de hoje

    Args:
        db: Sessão do banco
        limite: Número máximo de registros

    Returns:
        Lista de RegistroAcesso
    """
    hoje_inicio = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    return db.query(RegistroAcesso).filter(
        RegistroAcesso.data_hora >= hoje_inicio
    ).order_by(desc(RegistroAcesso.data_hora)).limit(limite).all()


def contar_registros_hoje(db: Session) -> dict:
    """
    Conta entradas e saídas de hoje

    Args:
        db: Sessão do banco

    Returns:
        Dict com contagens: {"entradas": int, "saidas": int, "total": int}
    """
    hoje_inicio = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    total = db.query(RegistroAcesso).filter(
        RegistroAcesso.data_hora >= hoje_inicio
    ).count()

    entradas = db.query(RegistroAcesso).filter(
        and_(
            RegistroAcesso.data_hora >= hoje_inicio,
            RegistroAcesso.tipo_movimento == "entrada"
        )
    ).count()

    saidas = db.query(RegistroAcesso).filter(
        and_(
            RegistroAcesso.data_hora >= hoje_inicio,
            RegistroAcesso.tipo_movimento == "saida"
        )
    ).count()

    return {
        "entradas": entradas,
        "saidas": saidas,
        "total": total
    }


# ============================================================================
# VEÍCULOS NO CAMPUS
# ============================================================================

def obter_veiculos_no_campus(db: Session) -> list[dict]:
    """
    Obtém lista de veículos atualmente no campus

    Lógica:
    - Busca veículos com última movimentação = "entrada"
    - Sem saída correspondente posterior

    Args:
        db: Sessão do banco

    Returns:
        Lista de dicts com dados do veículo e tempo de permanência
    """
    from sqlalchemy import func

    # Subconsulta para obter último registro de cada veículo
    subquery = db.query(
        RegistroAcesso.veiculo_id,
        func.max(RegistroAcesso.data_hora).label("ultima_data")
    ).group_by(RegistroAcesso.veiculo_id).subquery()

    # Busca registros que sejam entrada e sejam os mais recentes
    veiculos_no_campus = db.query(RegistroAcesso).join(
        subquery,
        and_(
            RegistroAcesso.veiculo_id == subquery.c.veiculo_id,
            RegistroAcesso.data_hora == subquery.c.ultima_data,
            RegistroAcesso.tipo_movimento == "entrada"
        )
    ).all()

    resultado = []
    agora = datetime.now()

    for registro in veiculos_no_campus:
        if registro.veiculo:
            tempo_permanencia = int((agora - registro.data_hora).total_seconds() / 60)  # minutos

            resultado.append({
                "veiculo": registro.veiculo,
                "proprietario": registro.veiculo.proprietario,
                "hora_entrada": registro.data_hora,
                "tempo_permanencia_minutos": tempo_permanencia
            })

    return resultado


def contar_veiculos_no_campus(db: Session) -> int:
    """
    Conta número de veículos atualmente no campus

    Args:
        db: Sessão do banco

    Returns:
        Número de veículos
    """
    return len(obter_veiculos_no_campus(db))
