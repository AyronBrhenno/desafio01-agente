from scripts.validar_entrega import sem_pii_persistida


def test_uuid_de_metadados_nao_e_cpf():
    uuid = "abcdef12-1234-5678-1234-12345678901a"
    assert sem_pii_persistida({"id": uuid})
    assert not sem_pii_persistida({"justificativa": "CPF 12345678901"})


def test_cpf_no_json_aninhado_inclusive_em_id_e_detectado():
    assert not sem_pii_persistida({"run_data": '{"input": {"justificativa": "CPF 052.318.947-20"}}'})
    assert not sem_pii_persistida({"id": "052.318.947-20"})


def test_hash_tipado_nao_e_cpf_mas_texto_pessoal_continua_verificado():
    digest = "a" * 20 + "12345678901" + "b" * 33
    assert sem_pii_persistida({"sha256_fontes_src": digest,
                              "arquivos_sha256": {"src/agente.py": digest}})
    assert not sem_pii_persistida({"justificativa": digest})
    assert not sem_pii_persistida({"arquivos_sha256": {"src/agente.py": "052.318.947-20"}})
