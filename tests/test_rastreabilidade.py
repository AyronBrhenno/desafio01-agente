from src.rastreabilidade import capturar_versao, divergencias_versao


def test_identifica_fonte_alterado_adicionado_e_removido(tmp_path):
    fontes = tmp_path / "src"
    fontes.mkdir()
    arquivo = fontes / "agente.py"
    arquivo.write_text("versao = 1\n", encoding="utf-8")
    registro = capturar_versao(tmp_path)
    assert divergencias_versao(registro, tmp_path) == []
    arquivo.write_text("versao = 2\n", encoding="utf-8")
    assert "src/agente.py" in divergencias_versao(registro, tmp_path)
    arquivo.unlink()
    (fontes / "outro.py").write_text("versao = 1\n", encoding="utf-8")
    # O hash agregado legado não detecta renomeação com conteúdo idêntico;
    # o manifesto por caminho precisa detectar a troca mesmo assim.
    assert set(divergencias_versao(registro, tmp_path)) == {"src/agente.py", "src/outro.py"}


def test_dados_e_formulario_tambem_invalidam_evidencia(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "dados").mkdir()
    dados = tmp_path / "dados" / "pedidos.json"
    app = tmp_path / "app.py"
    dados.write_text("[]", encoding="utf-8")
    app.write_text("# original", encoding="utf-8")
    registro = capturar_versao(tmp_path)
    dados.write_text("[{}]", encoding="utf-8")
    app.write_text("# alterado", encoding="utf-8")
    assert divergencias_versao(registro, tmp_path) == ["app.py", "dados/pedidos.json"]


def test_medicao_antiga_sem_manifesto_nao_e_certificada():
    assert divergencias_versao({"sha256_fontes_src": "hash-antigo"})


def test_validador_recusa_hash_trocado_e_medicao_incompleta(tmp_path):
    import json
    from scripts.validar_entrega import verificar_rastreabilidade
    from src.rastreabilidade import EVIDENCIAS_REAIS

    config = {**capturar_versao(), "concluida": True}
    for nome in EVIDENCIAS_REAIS:
        (tmp_path / nome).write_text(json.dumps({"configuracao": config}), encoding="utf-8")
    assert all(r["valido"] for r in verificar_rastreabilidade(tmp_path).values())

    config["arquivos_sha256"]["app.py"] = "0" * 64
    (tmp_path / "medicao_paralelo.json").write_text(json.dumps({"configuracao": config}), encoding="utf-8")
    config = {**capturar_versao(), "concluida": False}
    (tmp_path / "medicao_sequencial.json").write_text(json.dumps({"configuracao": config}), encoding="utf-8")
    verificacoes = verificar_rastreabilidade(tmp_path)
    assert verificacoes["medicao_paralelo.json"]["arquivos_divergentes"] == ["app.py"]
    assert not verificacoes["medicao_paralelo.json"]["valido"]
    assert not verificacoes["medicao_sequencial.json"]["valido"]
    assert verificacoes["memoria.json"]["valido"]
