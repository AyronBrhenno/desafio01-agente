"""Regressões de mensagens do terminal; sem chamadas à API."""

import io
import logging
from types import SimpleNamespace

import pytest
from agno.tools.function import Function, FunctionCall
from agno.utils import log as agno_log

from src.agente import Servico
from src.barreira import RecusaSegura, instrucao_fundamentada
from src.config import DADOS
from src.evidencias import contexto_consultado
from src.ferramentas import ler_json
from src.terminal import agrupar_avisos_recusa, configurar_logs_terminal


@pytest.fixture
def saida_terminal(monkeypatch):
    saida = io.StringIO()
    handler = logging.StreamHandler(saida)
    handler.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
    for logger in (agno_log.agent_logger, agno_log.team_logger, agno_log.workflow_logger):
        monkeypatch.setattr(logger, "handlers", [handler])
        monkeypatch.setattr(logger, "filters", [])
    monkeypatch.setattr(agno_log, "logger", agno_log.agent_logger)
    monkeypatch.setattr(agno_log, "log_tracebacks", True)
    configurar_logs_terminal()
    configurar_logs_terminal()  # Configurar novamente não duplica os avisos.
    return saida


def test_recusas_reais_do_agno_ficam_curtas_sem_mudar_bloqueio(
    tmp_path, monkeypatch, saida_terminal
):
    servico = Servico(tmp_path / "terminal.db")
    pedido = ler_json(DADOS / "pedidos.json")[0]
    monkeypatch.setenv("OPENAI_API_KEY", "chave-ficticia-sem-uso")

    def run_controlado(*args, **kwargs):
        funcao = Function.from_callable(servico._ferramentas()[0])
        for _ in range(3):
            chamada = FunctionCall(
                function=funcao, arguments={"matricula": "ARGUMENTO-NAO-EXIBIR"}
            )
            assert chamada.execute().status == "failure"
        servico.model.tentativas.extend(["instrucao"] * 8)
        try:
            servico.model.invoke()  # O teto impede chegar ao transporte.
        except RecusaSegura as erro:
            agno_log.log_error(f"Error in Agent run: {erro}")
            raise

    monkeypatch.setattr(servico.agent, "run", run_controlado)
    for _ in range(2):
        resultado = servico.instruir(pedido)
        assert resultado["status"] == "analise_manual"
        assert resultado["tipo_falha"] == "RecusaSegura"
        assert "instrucao" not in resultado and "consultas" not in resultado
        assert resultado["metricas"]["tentativas_modelo"] == 8
        assert resultado["metricas"]["chamadas_modelo"] == 0

    texto = saida_terminal.getvalue()
    assert texto.count("Consulta bloqueada:") == 2  # Um aviso por análise.
    assert texto.count("Limite de chamadas ao modelo atingido.") == 2
    assert len(texto.splitlines()) == 4
    for proibido in ("Traceback", "Could not run function", "Execução previamente recusada",
                     "ARGUMENTO-NAO-EXIBIR"):
        assert proibido not in texto


def test_falha_inesperada_conserva_diagnostico_e_traceback(saida_terminal):
    with agrupar_avisos_recusa():
        try:
            raise RuntimeError("Falha interna de teste")
        except RuntimeError as erro:
            agno_log.log_exception(erro)
    texto = saida_terminal.getvalue()
    assert "RuntimeError" in texto and "Traceback" in texto


def test_recusa_desconhecida_nao_expoe_conteudo(saida_terminal):
    with agrupar_avisos_recusa():
        try:
            raise RecusaSegura("CONTEUDO-NAO-EXIBIR")
        except RecusaSegura as erro:
            agno_log.log_warning(f"argumentos: CONTEUDO-NAO-EXIBIR; {erro}")
            agno_log.log_exception(erro)
    texto = saida_terminal.getvalue()
    assert texto.count("Execução bloqueada pela validação de segurança.") == 1
    assert "CONTEUDO-NAO-EXIBIR" not in texto and "Traceback" not in texto


def test_resposta_valida_nao_recebe_aviso(tmp_path, monkeypatch, saida_terminal):
    servico = Servico(tmp_path / "valida.db")
    pedido = ler_json(DADOS / "pedidos.json")[0]
    monkeypatch.setenv("OPENAI_API_KEY", "chave-ficticia-sem-uso")

    def run_controlado(*args, **kwargs):
        servico.contexto = contexto_consultado(pedido)
        return SimpleNamespace(
            status="COMPLETED", content=instrucao_fundamentada(servico.contexto)
        )

    monkeypatch.setattr(servico.agent, "run", run_controlado)
    assert servico.instruir(pedido)["status"] == "validado"
    assert saida_terminal.getvalue() == ""
