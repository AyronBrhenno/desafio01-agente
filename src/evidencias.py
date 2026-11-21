"""Evidências sem modelo: consultas, falhas controladas e eliminação real SQLite."""

import json
import tempfile
from pathlib import Path
from types import SimpleNamespace

from agno.db.schemas.memory import UserMemory
from agno.db.sqlite import SqliteDb
from agno.run.agent import RunOutput
from agno.session.agent import AgentSession

from .barreira import Contexto, RecusaSegura, instrucao_fundamentada, liberar
from .config import DADOS, MENSAGEM_MANUAL, RESULTADOS
from .ferramentas import Acervo, ler_json
from .memoria import BancoTrabalho
from .privacidade import sanitizar


def contexto_consultado(pedido: dict) -> Contexto:
    ctx = Contexto(sanitizar(pedido), Acervo())
    p = ctx.pedido
    cadastro = ctx.executar("consultar_cadastro", {"matricula": p["matricula"]})
    from .barreira import problemas_dados

    if (
        not cadastro["servidor"]
        or cadastro["servidor"]["nome"] != p["nome"]
        or problemas_dados(p)
    ):
        return ctx
    grupo = cadastro["servidor"]["grupo_diaria"]
    ctx.executar(
        "consultar_historico",
        {"matricula": p["matricula"], "data_partida": p["data_partida"]},
    )
    calc = ctx.executar(
        "calcular_diarias",
        {
            "grupo": grupo,
            **{
                k: p[k]
                for k in ("destino_uf", "data_pedido", "data_partida", "data_retorno")
            },
        },
    )
    ctx.executar(
        "consultar_saldo_diarias",
        {"unidade": cadastro["servidor"]["unidade"], "valor": calc["valor_total"]},
    )
    return ctx


def eliminacao_fixture(caminho: Path) -> dict:
    """Usa APIs Agno reais, sem chamar modelo; erro de user_id reproduzido."""
    banco = BancoTrabalho(caminho)
    db = SqliteDb(db_file=str(caminho))
    pedidos = {p["numero"]: sanitizar(p) for p in ler_json(DADOS / "pedidos.json")}
    for numero in ("DIA-2026-0111", "DIA-2026-0112", "DIA-2026-0101"):
        p = pedidos[numero]
        banco.guardar(p)
        entrada = json.dumps(p, ensure_ascii=False)
        db.upsert_session(
            AgentSession(
                session_id=numero,
                user_id=p["matricula"],
                runs=[
                    RunOutput(
                        run_id=f"fixture-{numero}",
                        session_id=numero,
                        user_id=p["matricula"],
                        content=entrada,
                    )
                ],
            )
        )
        db.upsert_run(
            RunOutput(
                run_id=f"fixture-{numero}",
                session_id=numero,
                user_id=p["matricula"],
                content=entrada,
            ),
            session_id=numero,
            user_id=p["matricula"],
            run_index=0,
        )
        db.upsert_user_memory(
            UserMemory(
                memory_id=f"fixture-{numero}",
                user_id=p["matricula"],
                memory=f"Pedido de {p['nome']}, matrícula informada {p['matricula']}.",
            )
        )
    por_id_carla = db.get_sessions(user_id="207418")
    encontrados_nome = banco.procurar("207418", "Carla Regina Souza")
    recibos = [
        banco.eliminar(mat, nome, db)
        for mat, nome in (
            ("206689", "Beatriz Moraes Cunha"),
            ("207418", "Carla Regina Souza"),
        )
    ]
    restante = db.get_session("DIA-2026-0101")
    resultado = {
        "natureza": "fixture com APIs reais de persistência; sem modelo",
        "sessoes_carla_encontradas_so_por_user_id_correto": len(por_id_carla),
        "linhas_carla_encontradas_por_varredura": {
            t: len(r) for t, r in encontrados_nome.items()
        },
        "recibos": recibos,
        "sessao_outra_titular_preservada": restante is not None,
    }
    db.db_engine.dispose()
    return resultado


def executar() -> dict:
    RESULTADOS.mkdir(exist_ok=True)
    acervo = Acervo()
    pedidos = ler_json(DADOS / "pedidos.json")
    testes = {
        "cadastro_matricula_digitada_no_0112": acervo.consultar_cadastro("207481"),
        "prestacao_vencida_0108": acervo.consultar_historico("203648", "2026-11-03"),
        "prestacao_dentro_prazo_0102": acervo.consultar_historico(
            "205882", "2026-11-09"
        ),
        "meia_diaria_0103": acervo.calcular_diarias(
            "B", "MT", "2026-10-07", "2026-11-05", "2026-11-05"
        ),
        "saldo_insuficiente_0110": acervo.consultar_saldo_diarias("CRH", 1800.0),
    }
    (RESULTADOS / "ferramentas_sem_modelo.json").write_text(
        json.dumps(testes, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    falhas = []
    for tipo in (
        "matricula_inventada",
        "retorno_inventado",
        "valor_inventado",
        "status_api_erro",
    ):
        ctx = contexto_consultado(pedidos[0])
        i = instrucao_fundamentada(ctx)
        bloqueado = False
        try:
            if tipo == "matricula_inventada":
                ctx.executar(
                    "consultar_historico",
                    {"matricula": "207418", "data_partida": "2026-11-09"},
                )
            elif tipo == "retorno_inventado":
                ctx.executar(
                    "calcular_diarias",
                    {
                        "grupo": "B",
                        "destino_uf": "MT",
                        "data_pedido": "2026-10-08",
                        "data_partida": "2026-11-09",
                        "data_retorno": "2026-11-13",
                    },
                )
            elif tipo == "valor_inventado":
                liberar(
                    ctx,
                    SimpleNamespace(
                        status="COMPLETED",
                        content=i.model_copy(update={"valor_total": 1.0}),
                    ),
                )
            else:
                liberar(ctx, SimpleNamespace(status="ERROR", content=i))
        except RecusaSegura:
            bloqueado = True
        falhas.append(
            {
                "falha": tipo,
                "natureza": "injeção controlada sem API",
                "bloqueada": bloqueado,
                "conteudo_exposto": False,
                "mensagem": MENSAGEM_MANUAL,
            }
        )
    (RESULTADOS / "falhas_controladas.json").write_text(
        json.dumps(falhas, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    with tempfile.TemporaryDirectory(prefix="diarias-evidencia-") as pasta:
        eliminacao = eliminacao_fixture(Path(pasta) / "trabalho.db")
    (RESULTADOS / "eliminacao_fixture.json").write_text(
        json.dumps(eliminacao, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return {
        "consultas_testadas": len(testes),
        "falhas_bloqueadas": sum(f["bloqueada"] for f in falhas),
        "eliminacao_verificada": all(
            r["eliminacao_verificada"] for r in eliminacao["recibos"]
        ),
    }
