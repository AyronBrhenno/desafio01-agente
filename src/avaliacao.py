"""Avaliador separado: único módulo de produção que pode abrir o gabarito."""

import json
import statistics
import time
from pathlib import Path

from .agente import Servico
from .config import DADOS, ESTADO, RAIZ, RESULTADOS
from .ferramentas import ler_json
from .rastreabilidade import capturar_versao, exigir_versao


def gravar(caminho: Path, obj):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def confrontar(resultado: dict, esperado: dict) -> dict:
    if resultado["status"] != "validado":
        return {
            "acerto_exato": False,
            "recusa_segura": True,
            "divergencias": ["analise_manual"],
        }
    i = resultado["instrucao"]
    campos = [
        "recomendacao",
        "quantidade_diarias",
        "valor_total",
        "exige_autorizacao_superior",
    ]
    divergencias = [k for k in campos if i[k] != esperado[k]]
    obtidos = {
        v["criterio"] for v in i["verificacoes"] if v["situacao"] == "nao_atende"
    }
    if obtidos != set(esperado["criterios_nao_atendidos"]):
        divergencias.append("criterios_nao_atendidos")
    return {
        "acerto_exato": not divergencias,
        "recusa_segura": False,
        "divergencias": divergencias,
    }


def resumo(linhas: list) -> dict:
    metricas = [l["resultado"]["metricas"] for l in linhas]
    duracoes = sorted(m["segundos"] for m in metricas)
    custos = [m["custo_usd"] for m in metricas]
    return {
        "casos": len(linhas),
        "acertos_exatos": sum(l["avaliacao"]["acerto_exato"] for l in linhas),
        "recusas_seguras": sum(l["avaliacao"]["recusa_segura"] for l in linhas),
        "erros_liberados": sum(
            not l["avaliacao"]["acerto_exato"] and not l["avaliacao"]["recusa_segura"]
            for l in linhas
        ),
        "tokens_entrada": sum(m["tokens_entrada"] for m in metricas),
        "tokens_saida": sum(m["tokens_saida"] for m in metricas),
        "chamadas_modelo_media": statistics.mean(
            m["chamadas_modelo"] for m in metricas
        ),
        "segundos_mediana": statistics.median(duracoes),
        "segundos_p95": duracoes[min(len(duracoes) - 1, int(0.95 * len(duracoes)))],
        "segundos_total": sum(duracoes),
        "custo_estimado_usd": sum(custos)
        if all(c is not None for c in custos)
        else None,
    }


def medir(rodadas: int = 3, paralelo: bool = False, etiqueta: str | None = None):
    pedidos = ler_json(DADOS / "pedidos.json")
    complementos = ler_json(DADOS / "complementacoes.json")
    # Nunca é repassado a Servico, ao prompt ou ao banco do agente.
    gabarito = ler_json(RAIZ / "gabarito.json")
    nome = etiqueta or ("paralelo" if paralelo else "sequencial")
    saida = RESULTADOS / f"medicao_{nome}.json"
    linhas = []
    lote = time.strftime("%Y%m%d-%H%M%S")
    configuracao = {
        "paralelo": paralelo,
        "memoria": "historico",
        "rodadas": rodadas,
        **capturar_versao(),
        "inicio_lote": lote,
        "concluida": False,
    }
    for rodada in range(1, rodadas + 1):
        servico = Servico(
            ESTADO / f"medicao-{nome}-{lote}-{rodada}.db", paralelo=paralelo
        )
        casos = [("pedidos", p["numero"], p) for p in pedidos]
        casos += [("complementacoes", c["numero"], c) for c in complementos]
        for tipo, numero, entrada in casos:
            r = (
                servico.instruir(entrada)
                if tipo == "pedidos"
                else servico.instruir(numero=numero, complementacao=entrada["texto"])
            )
            avaliacao = confrontar(r, gabarito[tipo][numero])
            linhas.append(
                {
                    "rodada": rodada,
                    "tipo": tipo,
                    "numero": numero,
                    "resultado": r,
                    "avaliacao": avaliacao,
                }
            )
            gravar(
                saida,
                {
                    "configuracao": configuracao,
                    "linhas": linhas,
                    "resumo": resumo(linhas),
                },
            )
            print(
                f"{nome} rodada {rodada} {numero} {tipo}: {r['status']} acerto={avaliacao['acerto_exato']}",
                flush=True,
            )
    exigir_versao(configuracao)
    configuracao["concluida"] = True
    gravar(
        saida,
        {"configuracao": configuracao, "linhas": linhas, "resumo": resumo(linhas)},
    )
    return resumo(linhas)


def medir_memoria():
    pedidos = {p["numero"]: p for p in ler_json(DADOS / "pedidos.json")}
    complementos = ler_json(DADOS / "complementacoes.json")
    gabarito = ler_json(RAIZ / "gabarito.json")
    linhas = []
    lote = time.strftime("%Y%m%d-%H%M%S")
    configuracao = {**capturar_versao(), "inicio_lote": lote, "concluida": False}
    for modo in ("sem", "historico", "usuario"):
        servico = Servico(ESTADO / f"memoria-{modo}-{lote}.db", memoria=modo)
        for c in complementos:
            numero = c["numero"]
            primeiro = servico.instruir(pedidos[numero])
            segundo = servico.instruir(numero=numero, complementacao=c["texto"])
            linha = {
                "modo": modo,
                "numero": numero,
                "primeiro_turno": primeiro,
                "complementacao": segundo,
                "avaliacao": confrontar(segundo, gabarito["complementacoes"][numero]),
                "aplicada_ao_pedido_certo": segundo.get("instrucao", {}).get(
                    "numero_pedido"
                )
                == numero,
            }
            linhas.append(linha)
            gravar(
                RESULTADOS / "memoria.json",
                {"configuracao": configuracao, "linhas": linhas},
            )
            print(
                f"memoria={modo} {numero}: {segundo['status']} acerto={linha['avaliacao']['acerto_exato']}",
                flush=True,
            )
        # Eliminação também exercitada no banco REAL preenchido pelas chamadas.
        recibos = []
        for mat, nome in (
            ("206689", "Beatriz Moraes Cunha"),
            ("207418", "Carla Regina Souza"),
        ):
            recibos.append(servico.eliminar(mat, nome))
        exigir_versao(configuracao)
        gravar(
            RESULTADOS / f"eliminacao_real_{modo}.json",
            {"configuracao": {**configuracao, "concluida": True}, "recibos": recibos},
        )
    exigir_versao(configuracao)
    configuracao["concluida"] = True
    gravar(
        RESULTADOS / "memoria.json", {"configuracao": configuracao, "linhas": linhas}
    )
    return {
        "configuracoes": 3,
        "complementacoes": len(linhas),
        "acertos": sum(l["avaliacao"]["acerto_exato"] for l in linhas),
    }
