"""
Serviço de Auditoria - Sistema ALPR UNIPIAGET
Regista todas as ações realizadas pelos utilizadores no sistema
"""

from sqlalchemy.orm import Session
from web_module.models import LogAuditoria


def registrar_log(db: Session, usuario_id: int, acao: str, detalhes: str = None) -> None:
    """
    Regista uma ação de auditoria.

    Deve ser chamado ANTES do db.commit() da operação principal,
    para que o log faça parte da mesma transação.

    Args:
        db: Sessão do banco de dados
        usuario_id: ID do utilizador que realizou a ação
        acao: Descrição curta da ação (ex: "criar_veiculo", "deletar_proprietario")
        detalhes: Detalhes adicionais em texto livre (ex: "Placa: MPM123AB")
    """
    log = LogAuditoria(
        usuario_id=usuario_id,
        acao=acao,
        detalhes=detalhes,
    )
    db.add(log)
