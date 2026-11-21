"""Quatro consultas somente leitura. Não abre gerador nem gabarito."""

import csv
import json
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from .config import DADOS


def ler_json(caminho: Path):
    return json.loads(caminho.read_text(encoding="utf-8"))


def data_iso(texto: str) -> date:
    if not isinstance(texto, str) or len(texto) != 10:
        raise ValueError("Data deve ter formato AAAA-MM-DD.")
    return date.fromisoformat(texto)


def somar_uteis(inicio: date, dias: int) -> date:
    atual = inicio
    while dias:
        atual += timedelta(days=1)
        if atual.weekday() < 5:
            dias -= 1
    return atual


class Acervo:
    def __init__(self, pasta: Path = DADOS):
        with (pasta / "servidores.csv").open(encoding="utf-8", newline="") as f:
            # CPF e e-mail não integram nem mesmo o cache do serviço.
            self.servidores = {
                r["matricula"]: {
                    k: r[k]
                    for k in (
                        "matricula",
                        "nome",
                        "cargo",
                        "grupo_diaria",
                        "unidade",
                        "municipio_sede",
                    )
                }
                for r in csv.DictReader(f)
            }
        with (pasta / "historico_diarias.csv").open(encoding="utf-8", newline="") as f:
            self.historico = list(csv.DictReader(f))
        self.tabela = ler_json(pasta / "tabela_diarias.json")
        self.unidades = ler_json(pasta / "unidades.json")
        self.norma = (pasta / "normas.md").read_text(encoding="utf-8")

    def consultar_cadastro(self, matricula: str) -> dict:
        """Consulte antes de qualquer cálculo para confrontar matrícula e nome.

        matricula: string de seis dígitos, exatamente como no pedido ou correção
        expressa, por exemplo '204317'. Retorna dicionário com encontrado e os
        campos funcionais nome, matrícula, cargo, grupo_diaria, unidade e sede;
        nunca retorna CPF ou e-mail. Ausência não autoriza busca aproximada.
        """
        s = self.servidores.get(matricula)
        return {"encontrado": s is not None, "servidor": dict(s) if s else None}

    def consultar_historico(self, matricula: str, data_partida: str) -> dict:
        """Use após confirmar a identidade para verificar contas e limite mensal.

        matricula: seis dígitos do pedido confirmado. data_partida: AAAA-MM-DD
        do pedido. Retorna mês, quantidade já concedida, limite, saldo mensal,
        prestações pendentes com prazo calculado em cinco dias úteis e vencida
        em relação à data fixa da análise. Não considera feriados neste acervo.
        Pendente dentro do prazo não impede concessão. Viagens futuras contam
        no mês da partida, sem reservar novas diárias durante a instrução.
        """
        partida = data_iso(data_partida)
        mes = partida.strftime("%Y-%m")
        linhas = [h for h in self.historico if h["matricula"] == matricula]
        usadas = sum(
            Decimal(h["quantidade"]) for h in linhas if h["data_partida"][:7] == mes
        )
        limite = Decimal(str(self.tabela["limite_mensal_diarias"]))
        analise = data_iso(self.tabela["data_da_analise"])
        pendentes = []
        for h in linhas:
            if h["prestacao_contas"] == "pendente":
                prazo = somar_uteis(
                    data_iso(h["data_retorno"]),
                    self.tabela["prazo_prestacao_dias_uteis"],
                )
                pendentes.append(
                    {
                        "pedido": h["pedido"],
                        "data_retorno": h["data_retorno"],
                        "prazo": prazo.isoformat(),
                        "vencida": prazo < analise,
                    }
                )
        return {
            "matricula": matricula,
            "mes": mes,
            "data_da_analise": analise.isoformat(),
            "quantidade_concedida": float(usadas),
            "limite_mensal": float(limite),
            "saldo_mensal": float(limite - usadas),
            "prestacoes_pendentes": pendentes,
            "possui_prestacao_vencida": any(p["vencida"] for p in pendentes),
        }

    def calcular_diarias(
        self,
        grupo: str,
        destino_uf: str,
        data_pedido: str,
        data_partida: str,
        data_retorno: str,
    ) -> dict:
        """Use após obter grupo no cadastro e somente com todas as datas expressas.

        grupo: A, B ou C devolvido pelo cadastro; destino_uf: sigla de dois
        caracteres do pedido; datas: AAAA-MM-DD, sem estimar retorno ausente.
        Retorna pernoites, quantidade, valor unitário e total em reais,
        antecedência em dias corridos e indicação de atendimento ao mínimo.
        Uma diária por pernoite mais meia no retorno; sem pernoite, meia.
        Não julga urgência. Datas inválidas ou invertidas produzem ValueError.
        """
        pedido, partida, retorno = map(
            data_iso, (data_pedido, data_partida, data_retorno)
        )
        if retorno < partida or partida < pedido:
            raise ValueError("Cronologia inválida no pedido.")
        ufs = {
            "AC",
            "AL",
            "AP",
            "AM",
            "BA",
            "CE",
            "DF",
            "ES",
            "GO",
            "MA",
            "MT",
            "MS",
            "MG",
            "PA",
            "PB",
            "PR",
            "PE",
            "PI",
            "RJ",
            "RN",
            "RS",
            "RO",
            "RR",
            "SC",
            "SP",
            "SE",
            "TO",
        }
        if destino_uf not in ufs or grupo not in self.tabela["valores"]:
            raise ValueError("Grupo ou UF não reconhecido.")
        classe = (
            "interior_mt"
            if destino_uf == "MT"
            else "distrito_federal"
            if destino_uf == "DF"
            else "outra_uf"
        )
        pernoites = (retorno - partida).days
        quantidade = Decimal(pernoites) + Decimal("0.5")
        unitario = Decimal(str(self.tabela["valores"][grupo][classe]))
        total = (quantidade * unitario).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        antecedencia = (partida - pedido).days
        return {
            "grupo": grupo,
            "classe_destino": classe,
            "pernoites": pernoites,
            "quantidade_diarias": float(quantidade),
            "valor_unitario": float(unitario),
            "valor_total": float(total),
            "antecedencia_dias": antecedencia,
            "antecedencia_minima_dias": self.tabela["antecedencia_minima_dias"],
            "antecedencia_atendida": antecedencia
            >= self.tabela["antecedencia_minima_dias"],
        }

    def consultar_saldo_diarias(self, unidade: str, valor: float) -> dict:
        """Use depois do cálculo para conferir saldo da unidade de lotação.

        unidade: sigla exata devolvida pelo cadastro, como CFF; valor: total
        em reais da ferramenta de cálculo, com ponto decimal, como 980.0.
        Retorna unidade, saldo, valor consultado, suficiente e diferença.
        Não reserva nem debita recursos; concessão depende do ordenador.
        Unidade inexistente ou valor negativo/não finito produz ValueError.
        """
        if unidade not in self.unidades:
            raise ValueError("Unidade não localizada.")
        total = Decimal(str(valor))
        if not total.is_finite() or total < 0:
            raise ValueError("Valor inválido.")
        saldo = Decimal(str(self.unidades[unidade]["saldo_diarias"]))
        return {
            "unidade": unidade,
            "saldo_disponivel": float(saldo),
            "valor_consultado": float(total),
            "suficiente": saldo >= total,
            "diferenca": float(saldo - total),
        }
