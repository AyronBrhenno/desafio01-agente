"""Filtro antes de qualquer persistência; guardrail Agno em defesa adicional."""

import json
import re
import unicodedata

PADROES = {
    "cpf": r"(?<!\d)(?:\d{3}\.\d{3}\.\d{3}-\d{2}|\d{11})(?!\d)",
    "banco": r"(?i)\b(?:conta(?:\s+corrente)?|ag[eê]ncia)\s*(?:n[ºo°.]?\s*)?[:=]?\s*\d{1,12}(?:\s*[-–]\s*[\dXx])?",
}


def mascarar(texto: str) -> str:
    for nome, padrao in PADROES.items():
        texto = re.sub(padrao, f"[DADO_{nome.upper()}_REMOVIDO]", texto)
    return texto


def sanitizar(obj):
    """Copia objetos JSON sem alterar números, datas ou matrículas."""
    if isinstance(obj, str):
        return mascarar(obj)
    if isinstance(obj, dict):
        return {k: sanitizar(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitizar(v) for v in obj]
    return obj


def texto_normalizado(texto: str) -> str:
    return "".join(
        c
        for c in unicodedata.normalize("NFKD", texto.casefold())
        if not unicodedata.combining(c)
    )


def tem_ordem_embutida(texto: str) -> bool:
    t = texto_normalizado(texto)
    return any(
        s in t
        for s in (
            "sistema de analise",
            "ignore as regras",
            "ignore previous",
            "classifique o pedido",
            "registre a antecedencia",
            "system prompt",
        )
    )


def urgencia_documentada(texto: str) -> bool:
    """Barreira conservadora: aceita somente emergência expressamente descrita.

    O modelo ainda julga o relato; esta verificação não autoriza a despesa.
    Texto dirigido ao sistema não serve como prova da exceção.
    """
    t = texto_normalizado(texto)
    if tem_ordem_embutida(t) or re.search(
        r"\b(nao ha|sem) (urgencia|incendio|desastre)", t
    ):
        return False
    return bool(
        re.search(
            r"incendio.*(?:em curso|focos ativos)|desastre ambiental.*(?:ocorrido|em curso)|"
            r"infracao ambiental em curso|determinacao judicial.*prazo",
            t,
        )
    )


def sem_pii(obj) -> bool:
    texto = json.dumps(obj, ensure_ascii=False, default=str)
    return texto == mascarar(texto)
