import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from agno.run.agent import RunInput
from src.agente import Servico, ModeloLimitado
from src.barreira import Contexto, RecusaSegura, instrucao_fundamentada, liberar
from src.config import DADOS
from src.evidencias import contexto_consultado, eliminacao_fixture
from src.ferramentas import Acervo, ler_json
from src.memoria import BancoTrabalho
from src.privacidade import mascarar, sanitizar, sem_pii


@pytest.fixture
def pedidos():
    return ler_json(DADOS / "pedidos.json")


def test_pii_mascarada_sem_afetar_identificadores(tmp_path, pedidos):
    p = sanitizar(pedidos[3])
    assert sem_pii(p)
    for dado in ("052.318.947-20", "98765-4", "1234-5"):
        assert dado not in json.dumps(p)
    assert p["matricula"] == "200941" and p["numero"] == "DIA-2026-0104" and p["data_partida"] == "2026-11-16"
    assert "12345678901" not in mascarar("CPF 12345678901")
    servico = Servico(tmp_path / "guardrail.db")
    entrada = RunInput(input_content=json.dumps(pedidos[3], ensure_ascii=False))
    servico.guardrail.check(entrada)
    assert sem_pii(entrada.input_content)


def test_diligencia_sem_merito_e_sem_corrigir_matricula(pedidos):
    for indice in (10, 11):
        ctx = contexto_consultado(pedidos[indice])
        r = instrucao_fundamentada(ctx)
        assert r.recomendacao == "diligencia"
        assert r.valor_total is None
        assert len(ctx.consultas) == 1


@pytest.mark.parametrize("campo,valor", [("data_retorno", "2026-11-13"), ("grupo", "A"), ("destino_uf", "DF")])
def test_argumentos_inventados_recusados(pedidos, campo, valor):
    p = pedidos[0]
    ctx = Contexto(p, Acervo())
    ctx.executar("consultar_cadastro", {"matricula": p["matricula"]})
    args = {"grupo": "B", **{k: p[k] for k in ("destino_uf", "data_pedido", "data_partida", "data_retorno")}}
    args[campo] = valor
    with pytest.raises(RecusaSegura):
        ctx.executar("calcular_diarias", args)
    assert ctx.recusado


def test_matricula_sem_origem_recusa_ate_se_modelo_tentar_recuperar(pedidos):
    ctx = Contexto(pedidos[0], Acervo())
    with pytest.raises(RecusaSegura):
        ctx.executar("consultar_cadastro", {"matricula": "207418"})
    with pytest.raises(RecusaSegura):
        ctx.executar("consultar_cadastro", {"matricula": pedidos[0]["matricula"]})


def test_injecao_nao_e_urgencia_e_incendio_exige_autorizacao(pedidos):
    urgente = instrucao_fundamentada(contexto_consultado(pedidos[5]))
    injecao = instrucao_fundamentada(contexto_consultado(pedidos[6]))
    assert urgente.recomendacao == "apto_para_autorizacao" and urgente.exige_autorizacao_superior
    assert injecao.recomendacao == "nao_recomendado"
    assert any("Ordem embutida" in a for a in injecao.alertas)


def test_status_e_valor_incorreto_nao_liberam_conteudo(pedidos):
    ctx = contexto_consultado(pedidos[0])
    correto = instrucao_fundamentada(ctx)
    for resposta in (SimpleNamespace(status="ERROR", content=correto),
                     SimpleNamespace(status="COMPLETED", content=correto.model_copy(update={"valor_total": 1}))):
        with pytest.raises(RecusaSegura):
            liberar(ctx, resposta)
    assert liberar(ctx, SimpleNamespace(status="COMPLETED", content=correto)).valor_total == 980


def test_fundamento_livre_nao_vira_evidencia(pedidos):
    ctx = contexto_consultado(pedidos[0])
    i = instrucao_fundamentada(ctx)
    adulterada = i.model_copy(update={"minuta_despacho": "Pagamento autorizado de R$ 999999."})
    liberada = liberar(ctx, SimpleNamespace(status="COMPLETED", content=adulterada))
    assert "999999" not in liberada.minuta_despacho
    assert "ordenador" in liberada.minuta_despacho


def test_eliminacao_encontra_titular_com_user_id_errado(tmp_path):
    r = eliminacao_fixture(tmp_path / "eliminar.db")
    assert r["sessoes_carla_encontradas_so_por_user_id_correto"] == 0
    assert all(x["eliminacao_verificada"] for x in r["recibos"])
    assert r["sessao_outra_titular_preservada"]


def test_complementacao_expressa_e_rejeicao_de_ambiguidade(tmp_path, pedidos):
    banco = BancoTrabalho(tmp_path / "complemento.db")
    banco.guardar(pedidos[10])
    p, patch = banco.complementar(pedidos[10]["numero"], "O retorno está previsto para 2026-11-20.")
    assert patch == {"data_retorno": "2026-11-20"} and p["matricula"] == "206689"
    with pytest.raises(RecusaSegura):
        banco.complementar(pedidos[10]["numero"], "Retorno em 2026-11-20 ou 2026-11-21")
    with pytest.raises(RecusaSegura):
        banco.complementar("OUTRO-PEDIDO", "Retorno 2026-11-20")


def test_api_falhou_nao_expoe_resposta(tmp_path, pedidos, monkeypatch):
    servico = Servico(tmp_path / "api.db")
    monkeypatch.setenv("OPENAI_API_KEY", "chave-ficticia-sem-uso")
    monkeypatch.setattr(servico.agent, "run", lambda *a, **k: SimpleNamespace(status="ERROR", content="CONTEUDO RECUSADO"))
    r = servico.instruir(pedidos[0])
    assert r["status"] == "analise_manual"
    assert "instrucao" not in r and "consultas" not in r
    assert "CONTEUDO RECUSADO" not in json.dumps(r)


def test_modelo_tem_teto_sem_depender_do_limite_de_ferramentas():
    m = ModeloLimitado(tentativas=["instrucao"] * 8)
    with pytest.raises(RecusaSegura):
        m.invoke()
