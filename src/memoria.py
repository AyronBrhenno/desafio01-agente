"""Persistência local e eliminação verificada, incluindo identidade digitada errada."""

import json
import re
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

from .barreira import RecusaSegura
from .privacidade import sanitizar, texto_normalizado

RETENCAO_DIAS = 30


def identificador(nome: str) -> str:
    return '"' + nome.replace('"', '""') + '"'


class BancoTrabalho:
    def __init__(self, caminho: Path):
        self.caminho = Path(caminho)
        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        with self.conectar() as con:
            con.execute(
                "CREATE TABLE IF NOT EXISTS casos (numero TEXT PRIMARY KEY, matricula TEXT NOT NULL, nome TEXT NOT NULL, pedido TEXT NOT NULL, atualizado REAL NOT NULL)"
            )
            con.execute(
                "CREATE TABLE IF NOT EXISTS conferencias (id INTEGER PRIMARY KEY, numero TEXT NOT NULL, sugestao TEXT NOT NULL, decisao TEXT NOT NULL, motivo TEXT NOT NULL, despacho TEXT NOT NULL, criado REAL NOT NULL)"
            )

    @contextmanager
    def conectar(self):
        con = sqlite3.connect(self.caminho, timeout=30)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA secure_delete=ON")
        try:
            with con:
                yield con
        finally:
            con.close()

    def guardar(self, pedido: dict):
        p = sanitizar(pedido)
        with self.conectar() as con:
            con.execute(
                "INSERT INTO casos VALUES (?,?,?,?,?) ON CONFLICT(numero) DO UPDATE SET matricula=excluded.matricula,nome=excluded.nome,pedido=excluded.pedido,atualizado=excluded.atualizado",
                (
                    p["numero"],
                    p["matricula"],
                    p["nome"],
                    json.dumps(p, ensure_ascii=False),
                    time.time(),
                ),
            )

    def recuperar(self, numero: str) -> dict:
        with self.conectar() as con:
            r = con.execute(
                "SELECT pedido, atualizado FROM casos WHERE numero=?", (numero,)
            ).fetchone()
        if not r or r["atualizado"] < time.time() - RETENCAO_DIAS * 86400:
            raise RecusaSegura("Sessão inexistente ou fora do prazo de retenção.")
        return json.loads(r["pedido"])

    def complementar(self, numero: str, texto: str) -> tuple[dict, dict]:
        """Aceita apenas datas/correção de matrícula expressas, nunca inferidas.

        A sessão fornece os campos anteriores; este parser restrito altera só o
        campo explicitamente nomeado. Ambiguidade exige análise manual.
        """
        p = self.recuperar(numero)
        texto = sanitizar(texto)
        normal = texto_normalizado(texto)
        patch = {}
        if "retorno" in normal:
            datas = set(re.findall(r"\b\d{4}-\d{2}-\d{2}\b", texto))
            if len(datas) != 1:
                raise RecusaSegura("Complementação de data ambígua.")
            patch["data_retorno"] = datas.pop()
        if "matricula" in normal:
            matriculas = set(re.findall(r"(?<![\d-])\d{6}(?![\d-])", texto))
            if len(matriculas) != 1:
                raise RecusaSegura("Complementação de matrícula ambígua.")
            patch["matricula"] = matriculas.pop()
        if not patch:
            raise RecusaSegura(
                "Complementação não contém correção explícita suportada."
            )
        return {**p, **patch}, patch

    def corrigir_titular_sessao(self, numero: str, matricula: str):
        """Correção explícita permite recuperar o histórico com o novo user_id."""
        with self.conectar() as con:
            tabelas = {
                r[0]
                for r in con.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            for tabela in ("agno_sessions", "agno_runs"):
                if tabela in tabelas:
                    colunas = {
                        r[1]
                        for r in con.execute(
                            f"PRAGMA table_info({identificador(tabela)})"
                        )
                    }
                    if {"user_id", "session_id"} <= colunas:
                        con.execute(
                            f"UPDATE {identificador(tabela)} SET user_id=? WHERE session_id=?",
                            (matricula, numero),
                        )

    def conferir(
        self, numero: str, sugestao: str, decisao: str, motivo: str, despacho: str
    ):
        self.recuperar(numero)
        if decisao != sugestao and not motivo.strip():
            raise ValueError("Informe o motivo da divergência.")
        with self.conectar() as con:
            con.execute(
                "INSERT INTO conferencias(numero,sugestao,decisao,motivo,despacho,criado) VALUES (?,?,?,?,?,?)",
                (
                    numero,
                    sugestao,
                    decisao,
                    sanitizar(motivo),
                    sanitizar(despacho),
                    time.time(),
                ),
            )

    def linhas(self):
        with self.conectar() as con:
            tabelas = [
                r[0]
                for r in con.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                )
            ]
            return {
                t: [
                    dict(r)
                    for r in con.execute(
                        f"SELECT rowid AS _rid_, * FROM {identificador(t)}"
                    )
                ]
                for t in tabelas
            }

    def procurar(self, matricula: str, nome: str) -> dict:
        termos = [texto_normalizado(matricula), texto_normalizado(nome)]
        return {
            t: [
                r
                for r in linhas
                if any(
                    termo
                    and termo
                    in texto_normalizado(json.dumps(r, ensure_ascii=False, default=str))
                    for termo in termos
                )
            ]
            for t, linhas in self.linhas().items()
        }

    def eliminar(self, matricula: str, nome: str, db_agno=None) -> dict:
        if not re.fullmatch(r"\d{6}", matricula) or len(nome.strip().split()) < 2:
            raise ValueError(
                "Informe matrícula e nome completo para localizar as cópias."
            )
        antes = self.procurar(matricula, nome)
        sessoes = set()
        for linhas in antes.values():
            for r in linhas:
                if r.get("session_id"):
                    sessoes.add(r["session_id"])
                if r.get("numero"):
                    sessoes.add(r["numero"])
        memorias_apagadas = 0
        if db_agno is not None:
            # API pública: apagar as sessões do titular e também as encontradas
            # pela varredura, inclusive sob outra matrícula digitada por engano.
            for s in db_agno.get_sessions(user_id=matricula) or []:
                sessoes.add(s.session_id)
            if sessoes:
                db_agno.delete_sessions(session_ids=sorted(sessoes))
            memorias = db_agno.get_user_memories(user_id=matricula) or []
            ids = [m.memory_id for m in memorias]
            # Inclui memórias contaminadas pelo nome, mesmo sob outro user_id.
            ids += [
                r["memory_id"]
                for t, linhas in antes.items()
                for r in linhas
                if "memory_id" in r
            ]
            if ids:
                db_agno.delete_user_memories(memory_ids=sorted(set(ids)))
                memorias_apagadas = len(set(ids))
        # Remover resíduos em TODAS as tabelas: runs, spans, estado da aplicação,
        # conferência e qualquer nova tabela do framework que retenha o titular.
        apagadas = {}
        for tabela, linhas in self.linhas().items():
            termos = [texto_normalizado(matricula), texto_normalizado(nome)]
            rowids = [
                r["_rid_"]
                for r in linhas
                if any(
                    termo
                    in texto_normalizado(json.dumps(r, ensure_ascii=False, default=str))
                    for termo in termos
                )
                or any(
                    s in json.dumps(r, ensure_ascii=False, default=str) for s in sessoes
                )
            ]
            if rowids:
                with self.conectar() as con:
                    con.executemany(
                        f"DELETE FROM {identificador(tabela)} WHERE rowid=?",
                        [(i,) for i in rowids],
                    )
                apagadas[tabela] = len(rowids)
        with self.conectar() as con:
            con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            con.execute("VACUUM")
        depois = self.procurar(matricula, nome)
        restos = {t: len(linhas) for t, linhas in depois.items()}
        # O recibo não contém nome/matrícula e não é salvo no banco eliminado.
        return {
            "linhas_encontradas_antes": {t: len(r) for t, r in antes.items()},
            "sessoes_apagadas": len(sessoes),
            "memorias_apagadas": memorias_apagadas,
            "residuos_apagados": apagadas,
            "restantes_por_tabela": restos,
            "eliminacao_verificada": not any(restos.values()),
        }

    def expirar(self, db_agno=None) -> list[dict]:
        with self.conectar() as con:
            titulares = con.execute(
                "SELECT DISTINCT matricula,nome FROM casos WHERE atualizado < ?",
                (time.time() - RETENCAO_DIAS * 86400,),
            ).fetchall()
        return [self.eliminar(r["matricula"], r["nome"], db_agno) for r in titulares]
