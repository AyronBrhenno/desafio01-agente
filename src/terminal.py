"""Mensagens curtas para recusas esperadas, sem alterar a execução do agente."""

import logging
import sys
from contextlib import contextmanager
from contextvars import ContextVar

from .barreira import RecusaSegura

_avisos = ContextVar("avisos_recusa_terminal", default=None)
_MENSAGENS = {
    "Matrícula sem origem no pedido vigente.":
        "Consulta bloqueada: a matrícula está ausente ou difere do pedido.",
    "Data de histórico sem origem.":
        "Consulta bloqueada: a data do histórico difere do pedido.",
    "Cálculo com argumento sem origem.":
        "Cálculo bloqueado: os dados não correspondem ao pedido e ao cadastro.",
    "Saldo sem vínculo com cadastro e cálculo.":
        "Consulta de saldo bloqueada: unidade ou valor não conferem.",
    "Mérito sem identidade e dados completos.":
        "Análise bloqueada: confira a identidade e os dados obrigatórios.",
    "Teto de chamadas ao modelo atingido.":
        "Limite de chamadas ao modelo atingido. O caso segue para análise manual.",
    "Teto de ferramentas excedido.":
        "Limite de consultas atingido. O caso segue para análise manual.",
}


@contextmanager
def agrupar_avisos_recusa():
    """Deduplica avisos somente dentro desta análise; libera o estado ao sair."""
    token = _avisos.set(set())
    try:
        yield
    finally:
        _avisos.reset(token)


class FiltroRecusas(logging.Filter):
    def filter(self, registro):
        avisos = _avisos.get()
        erro = registro.exc_info[1] if registro.exc_info else sys.exc_info()[1]
        if avisos is None or not isinstance(erro, RecusaSegura):
            return True
        motivo = str(erro)
        if motivo == "Execução previamente recusada." and avisos:
            return False
        mensagem = _MENSAGENS.get(
            motivo,
            "Execução bloqueada pela validação de segurança. O caso segue para análise manual.",
        )
        if mensagem in avisos:
            return False
        avisos.add(mensagem)
        # Mensagens fixas: não reproduzir argumentos, conteúdo recusado ou segredos.
        registro.msg = mensagem
        registro.args = ()
        registro.levelno = logging.WARNING
        registro.levelname = "AVISO"
        registro.exc_info = None
        registro.exc_text = None
        registro.stack_info = None
        return True


def configurar_logs_terminal():
    """Aplica o resumo aos loggers do Agno usados pelos comandos da CLI."""
    from agno.utils.log import agent_logger, team_logger, workflow_logger

    for logger in (agent_logger, team_logger, workflow_logger):
        if not any(isinstance(filtro, FiltroRecusas) for filtro in logger.filters):
            logger.addFilter(FiltroRecusas())
