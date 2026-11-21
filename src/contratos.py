from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Criterio = Literal[
    "cadastro",
    "dados_completos",
    "antecedencia",
    "prestacao_contas",
    "limite_mensal",
    "saldo_orcamentario",
]
CRITERIOS = [
    "cadastro",
    "dados_completos",
    "antecedencia",
    "prestacao_contas",
    "limite_mensal",
    "saldo_orcamentario",
]
Recomendacao = Literal["apto_para_autorizacao", "diligencia", "nao_recomendado"]


class Estrito(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Verificacao(Estrito):
    criterio: Criterio
    situacao: Literal["atende", "nao_atende", "nao_verificado"]
    detalhe: str = Field(min_length=1)


class Instrucao(Estrito):
    numero_pedido: str
    matricula: str
    quantidade_diarias: float | None = Field(default=None, ge=0)
    valor_total: float | None = Field(default=None, ge=0)
    verificacoes: list[Verificacao]
    recomendacao: Recomendacao
    exige_autorizacao_superior: bool
    pendencias: list[str]
    alertas: list[str]
    minuta_despacho: str = Field(min_length=1)

    @model_validator(mode="after")
    def seis_criterios(self):
        criterios = [v.criterio for v in self.verificacoes]
        if len(criterios) != 6 or set(criterios) != set(CRITERIOS):
            raise ValueError("É obrigatória uma verificação única por critério.")
        if self.recomendacao == "diligencia" and (
            self.quantidade_diarias is not None or self.valor_total is not None
        ):
            raise ValueError("Diligência não admite cálculo de mérito.")
        return self
