"""Relatórios não podem certificar medições ainda em execução."""

import json
import pytest

from src import relatorio
from src.rastreabilidade import capturar_versao


@pytest.mark.parametrize("nome", ["medicao_sequencial.json", "memoria.json"])
def test_relatorio_recusa_evidencia_incompleta(tmp_path, monkeypatch, nome):
    registro = {"configuracao": {**capturar_versao(), "concluida": False}}
    (tmp_path / nome).write_text(json.dumps(registro), encoding="utf-8")
    monkeypatch.setattr(relatorio, "RESULTADOS", tmp_path)
    with pytest.raises(RuntimeError, match="incompleta"):
        relatorio.gerar()
