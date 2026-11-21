"""Ancoragem obrigatória de argumentos e de resultados, independente do prompt."""

import json
from dataclasses import dataclass, field

from .contratos import CRITERIOS, Instrucao, Verificacao
from .ferramentas import Acervo, data_iso
from .privacidade import sem_pii, tem_ordem_embutida, urgencia_documentada


class RecusaSegura(ValueError):
    pass


OBRIGATORIOS = (
    "numero",
    "data_pedido",
    "matricula",
    "nome",
    "destino_municipio",
    "destino_uf",
    "data_partida",
    "data_retorno",
    "transporte",
    "justificativa",
)


def problemas_dados(p: dict) -> list[str]:
    erros = [f"Informar {k}." for k in OBRIGATORIOS if not p.get(k)]
    for k in ("data_pedido", "data_partida", "data_retorno"):
        if p.get(k):
            try:
                data_iso(p[k])
            except (ValueError, TypeError):
                erros.append(f"Corrigir {k}: usar AAAA-MM-DD.")
    if not erros and (
        p["data_retorno"] < p["data_partida"] or p["data_partida"] < p["data_pedido"]
    ):
        erros.append("Corrigir cronologia das datas.")
    if p.get("destino_uf") and p["destino_uf"] not in {
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
    }:
        erros.append("Corrigir UF de destino.")
    return erros


@dataclass
class Contexto:
    pedido: dict
    acervo: Acervo
    consultas: list[dict] = field(default_factory=list)
    respostas: dict = field(default_factory=dict)
    recusado: bool = False

    def recusar(self, motivo: str):
        self.recusado = True
        # Motivo fixo, sem ecoar argumento possivelmente sensível/inventado.
        raise RecusaSegura(motivo)

    def executar(self, nome: str, args: dict) -> dict:
        p = self.pedido
        if self.recusado:
            self.recusar("Execução previamente recusada.")
        if len(self.consultas) >= 6:
            self.recusar("Teto de ferramentas excedido.")
        self.consultas.append({"ferramenta": nome, "argumentos": args})
        if nome in ("consultar_cadastro", "consultar_historico") and args.get(
            "matricula"
        ) != p.get("matricula"):
            self.recusar("Matrícula sem origem no pedido vigente.")
        if nome != "consultar_cadastro":
            cad = self.respostas.get("consultar_cadastro", {}).get("servidor")
            if not cad or cad["nome"] != p.get("nome") or problemas_dados(p):
                self.recusar("Mérito sem identidade e dados completos.")
        if nome == "consultar_historico" and args.get("data_partida") != p.get(
            "data_partida"
        ):
            self.recusar("Data de histórico sem origem.")
        if nome == "calcular_diarias":
            esperado = {
                k: p.get(k)
                for k in ("destino_uf", "data_pedido", "data_partida", "data_retorno")
            }
            esperado["grupo"] = cad["grupo_diaria"]
            if args != esperado:
                self.recusar("Cálculo com argumento sem origem.")
        if nome == "consultar_saldo_diarias":
            calc = self.respostas.get("calcular_diarias")
            if not calc or args != {
                "unidade": cad["unidade"],
                "valor": calc["valor_total"],
            }:
                self.recusar("Saldo sem vínculo com cadastro e cálculo.")
        try:
            resultado = getattr(self.acervo, nome)(**args)
        except Exception:
            self.recusar("Falha em consulta obrigatória.")
        if not sem_pii(resultado):
            self.recusar("Resposta de ferramenta contém dado não permitido.")
        self.respostas[nome] = resultado
        self.consultas[-1]["resultado"] = resultado
        return resultado


def instrucao_fundamentada(ctx: Contexto) -> Instrucao:
    """Constrói a referência de validação só com evidências desta execução."""
    p, r = ctx.pedido, ctx.respostas
    if ctx.recusado or "consultar_cadastro" not in r:
        raise RecusaSegura("Cadastro não consultado com segurança.")
    cad = r["consultar_cadastro"]["servidor"]
    identidade = bool(cad and cad["nome"] == p.get("nome"))
    incompleto = problemas_dados(p)
    situacoes = {k: "nao_verificado" for k in CRITERIOS}
    detalhes = {k: "Sem análise de mérito: art. 9º." for k in CRITERIOS}
    situacoes["cadastro"] = "atende" if identidade else "nao_atende"
    detalhes["cadastro"] = json.dumps(r["consultar_cadastro"], ensure_ascii=False)
    situacoes["dados_completos"] = "nao_atende" if incompleto else "atende"
    detalhes["dados_completos"] = (
        "; ".join(incompleto) or "Campos obrigatórios e cronologia conferidos."
    )
    pendencias = list(incompleto)
    alertas = []
    if "[DADO_" in p.get("justificativa", ""):
        alertas.append(
            "Dados pessoais foram mascarados antes do envio e da persistência."
        )
    if tem_ordem_embutida(p.get("justificativa", "")):
        alertas.append(
            "Ordem embutida na justificativa desconsiderada; autorização verbal não substitui autorização escrita."
        )
    qtd = valor = None
    superior = False
    if not identidade or incompleto:
        if not identidade:
            pendencias.append(
                "Confirmar nome e matrícula com o solicitante, sem correção presumida (art. 9º)."
            )
        recomendacao = "diligencia"
    else:
        if not all(
            k in r
            for k in (
                "consultar_historico",
                "calcular_diarias",
                "consultar_saldo_diarias",
            )
        ):
            raise RecusaSegura("Faltam consultas obrigatórias.")
        h, c, s = (
            r[k]
            for k in (
                "consultar_historico",
                "calcular_diarias",
                "consultar_saldo_diarias",
            )
        )
        qtd, valor = c["quantidade_diarias"], c["valor_total"]
        urgente = not c["antecedencia_atendida"] and urgencia_documentada(
            p["justificativa"]
        )
        situacoes.update(
            {
                "antecedencia": "atende"
                if c["antecedencia_atendida"] or urgente
                else "nao_atende",
                "prestacao_contas": "nao_atende"
                if h["possui_prestacao_vencida"]
                else "atende",
                "limite_mensal": "atende" if qtd <= h["saldo_mensal"] else "nao_atende",
                "saldo_orcamentario": "atende" if s["suficiente"] else "nao_atende",
            }
        )
        detalhes.update(
            {
                "antecedencia": json.dumps(c, ensure_ascii=False)
                + (
                    " Exceção de urgência: art. 5º, §§ 1º e 2º."
                    if urgente
                    else " Art. 5º."
                ),
                "prestacao_contas": json.dumps(h, ensure_ascii=False) + " Art. 7º.",
                "limite_mensal": f"Concedidas {h['quantidade_concedida']}; pedido {qtd}; limite {h['limite_mensal']} no mês {h['mes']}. Art. 6º.",
                "saldo_orcamentario": json.dumps(s, ensure_ascii=False) + " Art. 8º.",
            }
        )
        for criterio, mensagem in {
            "antecedencia": "Antecedência inferior ao mínimo, sem urgência comprovada (art. 5º).",
            "prestacao_contas": "Regularizar prestação de contas vencida (art. 7º).",
            "limite_mensal": "Adequar quantidade ao limite mensal (art. 6º).",
            "saldo_orcamentario": "Obter disponibilidade orçamentária na unidade (art. 8º).",
        }.items():
            if situacoes[criterio] == "nao_atende":
                pendencias.append(mensagem)
        recomendacao = (
            "nao_recomendado"
            if "nao_atende" in situacoes.values()
            else "apto_para_autorizacao"
        )
        superior = urgente and recomendacao == "apto_para_autorizacao"
        if urgente:
            alertas.append(
                "Urgência exige autorização expressa e escrita do Secretário Adjunto, registrada no processo; a concessão não está autorizada."
            )
    verificacoes = [
        Verificacao(criterio=k, situacao=situacoes[k], detalhe=detalhes[k])
        for k in CRITERIOS
    ]
    minuta = f"Pedido {p['numero']}, matrícula {p['matricula']}. "
    if recomendacao == "diligencia":
        minuta += (
            "Devolver em diligência, sem análise de mérito (art. 9º). "
            + " ".join(pendencias)
        )
    else:
        minuta += f"Instrução: {qtd} diárias, total de R$ {valor:.2f}. "
        minuta += (
            "Apto para submissão ao ordenador. "
            if recomendacao == "apto_para_autorizacao"
            else "Concessão não recomendada. " + " ".join(pendencias) + " "
        )
        if superior:
            minuta += "Condicionar à autorização expressa e escrita do Secretário Adjunto (art. 5º, § 2º). "
    minuta += (
        "Submeter à conferência humana e à decisão do ordenador de despesa (art. 10)."
    )
    return Instrucao(
        numero_pedido=p["numero"],
        matricula=p["matricula"],
        quantidade_diarias=qtd,
        valor_total=valor,
        verificacoes=verificacoes,
        recomendacao=recomendacao,
        exige_autorizacao_superior=superior,
        pendencias=pendencias,
        alertas=alertas,
        minuta_despacho=minuta,
    )


def liberar(ctx: Contexto, resposta) -> Instrucao:
    """Recusa divergências; renderiza texto fundamentado por templates do código.

    Texto livre gerado pelo modelo não é uma fonte de evidência. O formulário
    recebe valores e estados conferidos, mais fundamentos montados das consultas.
    """
    status = getattr(resposta, "status", None)
    if getattr(status, "value", status) != "COMPLETED":
        # A enumeração instalada é verificada nos testes de integração.
        if str(getattr(status, "value", status)).lower() != "completed":
            raise RecusaSegura("Execução sem status completed.")
    conteudo = resposta.content
    if isinstance(conteudo, str):
        conteudo = Instrucao.model_validate_json(conteudo)
    elif not isinstance(conteudo, Instrucao):
        conteudo = Instrucao.model_validate(conteudo)
    esperado = instrucao_fundamentada(ctx)
    for campo in (
        "numero_pedido",
        "matricula",
        "quantidade_diarias",
        "valor_total",
        "recomendacao",
        "exige_autorizacao_superior",
    ):
        if getattr(conteudo, campo) != getattr(esperado, campo):
            raise RecusaSegura("Saída diverge das evidências desta execução.")
    if {v.criterio: v.situacao for v in conteudo.verificacoes} != {
        v.criterio: v.situacao for v in esperado.verificacoes
    }:
        raise RecusaSegura("Verificação diverge das evidências.")
    if not sem_pii(conteudo.model_dump()):
        raise RecusaSegura("Saída contém dado pessoal não permitido.")
    return esperado
