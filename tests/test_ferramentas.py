from datetime import date
import json
import pytest
from src.ferramentas import Acervo, somar_uteis


@pytest.fixture
def acervo():
    return Acervo()


def test_minimizacao_e_matricula_divergente(acervo):
    r = acervo.consultar_cadastro("207481")
    assert r["servidor"]["nome"] == "Rafael Lima Antunes"
    assert set(r["servidor"]) == {"matricula", "nome", "cargo", "grupo_diaria", "unidade", "municipio_sede"}
    assert acervo.consultar_cadastro("000000") == {"encontrado": False, "servidor": None}


def test_pendente_dentro_prazo_nao_e_vencida(acervo):
    r = acervo.consultar_historico("205882", "2026-11-09")
    assert r["prestacoes_pendentes"][0]["prazo"] == "2026-10-13"
    assert not r["possui_prestacao_vencida"]
    assert acervo.consultar_historico("203648", "2026-11-03")["possui_prestacao_vencida"]


def test_limite_inclui_viagens_futuras(acervo):
    h = acervo.consultar_historico("208114", "2026-11-23")
    assert h["quantidade_concedida"] == 8
    assert h["saldo_mensal"] == 2


@pytest.mark.parametrize("grupo,uf,pedido,partida,retorno,qtd,total", [
    ("B", "MT", "2026-10-07", "2026-11-05", "2026-11-05", 0.5, 140),
    ("A", "DF", "2026-10-06", "2026-11-16", "2026-11-18", 2.5, 1500),
    ("B", "RO", "2026-10-02", "2026-11-10", "2026-11-14", 4.5, 1800),
])
def test_calculo(acervo, grupo, uf, pedido, partida, retorno, qtd, total):
    r = acervo.calcular_diarias(grupo, uf, pedido, partida, retorno)
    assert (r["quantidade_diarias"], r["valor_total"]) == (qtd, total)


def test_saldo_e_limites(acervo):
    assert not acervo.consultar_saldo_diarias("CRH", 1800)["suficiente"]
    assert acervo.consultar_saldo_diarias("CRH", 640)["suficiente"]
    for valor in (-1, float("nan"), float("inf")):
        with pytest.raises(ValueError):
            acervo.consultar_saldo_diarias("CRH", valor)
    with pytest.raises(ValueError):
        acervo.calcular_diarias("B", "MT", "2026-10-01", "2026-11-05", "2026-11-04")


def test_dias_uteis_ignoram_fim_de_semana():
    assert somar_uteis(date(2026, 9, 18), 5) == date(2026, 9, 25)
