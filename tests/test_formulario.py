from pathlib import Path
from unittest.mock import patch
import streamlit as st
from streamlit.testing.v1 import AppTest
from src.agente import Servico
from src.config import RAIZ, DADOS, MENSAGEM_MANUAL
from src.evidencias import contexto_consultado
from src.barreira import instrucao_fundamentada
from src.ferramentas import ler_json


def resposta_validada():
    ctx = contexto_consultado(ler_json(DADOS / "pedidos.json")[0])
    return {"status": "validado", "instrucao": instrucao_fundamentada(ctx).model_dump(),
            "consultas": ctx.consultas, "metricas": {"tokens_entrada": 0, "tokens_saida": 0,
                                                     "segundos": 0, "custo_usd": None}}


def test_formulario_renderiza_conferencia_e_exige_motivo(tmp_path):
    # Sem chamadas API: a UI é testada com uma instrução construída das consultas.
    servico = Servico(tmp_path / "interface.db")
    servico.banco.guardar(ler_json(DADOS / "pedidos.json")[0])
    st.cache_resource.clear()
    with patch.object(Servico, "instruir", return_value=resposta_validada()), patch("src.agente.Servico", return_value=servico):
        app = AppTest.from_file(str(RAIZ / "app.py")).run(timeout=30)
        app.button[0].click().run(timeout=30)
        assert not app.exception
        assert any(x.label == "Minuta do despacho — editável" for x in app.text_area)
        decisao = next(s for s in app.selectbox if s.label == "Encaminhamento decidido pelo conferente")
        decisao.select("diligencia")
        next(b for b in app.button if b.label == "Registrar conferência").click().run(timeout=30)
        assert any("motivo" in e.value.lower() for e in app.error)


def test_formulario_falha_sem_conteudo_recusado(tmp_path):
    r = {"status": "analise_manual", "mensagem": MENSAGEM_MANUAL,
         "metricas": {"tokens_entrada": 0, "tokens_saida": 0, "segundos": 0, "custo_usd": None}}
    servico = Servico(tmp_path / "falha-interface.db")
    st.cache_resource.clear()
    with patch.object(Servico, "instruir", return_value=r), patch("src.agente.Servico", return_value=servico):
        app = AppTest.from_file(str(RAIZ / "app.py")).run(timeout=30)
        app.button[0].click().run(timeout=30)
        assert not app.exception
        assert any(e.value == MENSAGEM_MANUAL for e in app.error)
        assert not any(x.label == "Minuta do despacho — editável" for x in app.text_area)
