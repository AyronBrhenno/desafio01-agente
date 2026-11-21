"""Vincula evidências aos fontes, dados e configuração usados na execução."""

import hashlib
from pathlib import Path

from .config import RAIZ

EVIDENCIAS_REAIS = (
    "medicao_sequencial.json",
    "medicao_paralelo.json",
    "memoria.json",
    "formulario_real.json",
    "eliminacao_real_sem.json",
    "eliminacao_real_historico.json",
    "eliminacao_real_usuario.json",
)


def capturar_versao(raiz: Path = RAIZ) -> dict:
    raiz = Path(raiz)
    fontes = sorted((raiz / "src").glob("*.py"))
    arquivos = set(fontes)
    for pasta, extensoes in (
        ("src", {".py"}),
        ("scripts", {".py"}),
        ("dados", {".csv", ".json", ".md"}),
        (".streamlit", {".toml"}),
    ):
        arquivos.update(
            p
            for p in (raiz / pasta).rglob("*")
            if p.is_file() and p.suffix in extensoes
        )
    arquivos.update(
        raiz / nome
        for nome in ("app.py", "requirements.txt", "tarifas.json", "gabarito.json")
        if (raiz / nome).is_file()
    )
    return {
        # Mantém o algoritmo original para comparação com medições anteriores.
        "sha256_fontes_src": hashlib.sha256(
            b"".join(p.read_bytes() for p in fontes)
        ).hexdigest(),
        "arquivos_sha256": {
            p.relative_to(raiz).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(arquivos)
        },
    }


def divergencias_versao(registro: dict, raiz: Path = RAIZ) -> list[str]:
    atual = capturar_versao(raiz)
    gravados = registro.get("arquivos_sha256", {})
    divergentes = sorted(
        nome
        for nome in set(gravados) | set(atual["arquivos_sha256"])
        if gravados.get(nome) != atual["arquivos_sha256"].get(nome)
    )
    if registro.get("sha256_fontes_src") != atual["sha256_fontes_src"]:
        divergentes.append("sha256_fontes_src")
    return divergentes


def exigir_versao(registro: dict):
    divergentes = divergencias_versao(registro)
    if divergentes:
        raise RuntimeError(
            "Os arquivos mudaram desde a execução: " + ", ".join(divergentes)
        )
