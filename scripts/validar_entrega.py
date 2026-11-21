"""Verificação local da suíte, integridade e minimização; não chama o modelo."""

import json
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

from src.config import RAIZ, ESTADO, RESULTADOS
from src.privacidade import sem_pii
from src.rastreabilidade import EVIDENCIAS_REAIS, divergencias_versao


def verificar_rastreabilidade(pasta=RESULTADOS):
    verificacoes = {}
    for nome in EVIDENCIAS_REAIS:
        caminho = pasta / nome
        if not caminho.is_file():
            verificacoes[nome] = {"valido": False, "motivo": "Arquivo ausente."}
            continue
        config = json.loads(caminho.read_text(encoding="utf-8")).get("configuracao", {})
        divergentes = divergencias_versao(config)
        verificacoes[nome] = {
            "valido": not divergentes and config.get("concluida") is True,
            "concluida": config.get("concluida") is True,
            "arquivos_divergentes": divergentes,
        }
    return verificacoes


def sem_pii_persistida(valor, campo=""):
    if campo == "arquivos_sha256" and isinstance(valor, dict) and all(
        isinstance(v, str) and re.fullmatch(r"[0-9a-f]{64}", v) for v in valor.values()
    ):
        return True
    if isinstance(valor, str):
        if campo == "sha256_fontes_src" and re.fullmatch(r"[0-9a-f]{64}", valor):
            return True
        if campo in {"id", "run_id", "session_id", "agent_id", "memory_id", "tool_call_id"} and re.fullmatch(
            r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}", valor
        ):
            return True
        if valor.startswith(("{", "[")):
            try:
                return sem_pii_persistida(json.loads(valor))
            except (ValueError, TypeError):
                pass
        return sem_pii(valor)
    if isinstance(valor, dict):
        return all(sem_pii_persistida(v, k) for k, v in valor.items())
    if isinstance(valor, (list, tuple)):
        return all(sem_pii_persistida(v, campo) for v in valor)
    return True


def main():
    RESULTADOS.mkdir(exist_ok=True)
    ambiente = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1")
    pasta_temporaria = str(Path(tempfile.gettempdir()) / ("pytest-validacao-" + uuid.uuid4().hex))
    teste = subprocess.run(
        [sys.executable, "-B", "-m", "pytest", "-q", "--tb=short",
         "-p", "no:cacheprovider", "--basetemp", pasta_temporaria],
        cwd=RAIZ, capture_output=True, text=True, encoding="utf-8", errors="replace", env=ambiente,
    )
    (RESULTADOS / "testes.txt").write_text(teste.stdout + teste.stderr, encoding="utf-8")
    bancos = {}
    for caminho in sorted(ESTADO.glob("*.db")):
        con = sqlite3.connect(caminho)
        con.row_factory = sqlite3.Row
        try:
            tabelas = [r[0] for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )]
            por_tabela = {}
            for tabela in tabelas:
                nome = '"' + tabela.replace('"', '""') + '"'
                linhas = [dict(r) for r in con.execute(f"SELECT * FROM {nome}")]
                por_tabela[tabela] = {
                    "linhas": len(linhas), "sem_cpf_ou_dados_bancarios": sem_pii_persistida(linhas)
                }
            bancos[caminho.name] = por_tabela
        finally:
            con.close()
    auditoria = {
        "bancos": bancos,
        "criterio": "Textos de todas as tabelas, preservando UUIDs e hashes tipados.",
        "todos_sem_pii": all(t["sem_cpf_ou_dados_bancarios"] for b in bancos.values() for t in b.values()),
    }
    (RESULTADOS / "auditoria_privacidade.json").write_text(
        json.dumps(auditoria, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    evidencias_livres = all(
        sem_pii_persistida(json.loads(p.read_text(encoding="utf-8")))
        for p in RESULTADOS.rglob("*.json")
    )
    rastreabilidade = verificar_rastreabilidade()
    (RESULTADOS / "rastreabilidade.json").write_text(
        json.dumps(rastreabilidade, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    status = {
        "testes_passaram": teste.returncode == 0,
        "bancos_sem_pii": auditoria["todos_sem_pii"],
        "hashes_conferem": all(r["valido"] for r in rastreabilidade.values()),
        "evidencias_sem_pii": evidencias_livres,
        "bancos_verificados": len(bancos),
    }
    (RESULTADOS / "validacao_entrega.json").write_text(json.dumps(status, indent=2), encoding="utf-8")
    print(json.dumps(status, ensure_ascii=True, indent=2))
    if not all(status[k] for k in ("testes_passaram", "bancos_sem_pii", "hashes_conferem", "evidencias_sem_pii")):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
