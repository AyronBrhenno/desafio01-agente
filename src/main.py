import argparse
import json
from pathlib import Path

from .config import DADOS, ESTADO
from .ferramentas import ler_json


def main():
    parser = argparse.ArgumentParser(
        description="Desafio 01 — instrução de diárias hipotéticas"
    )
    sub = parser.add_subparsers(dest="comando", required=True)
    medir = sub.add_parser("medir")
    medir.add_argument("--rodadas", type=int, default=3)
    medir.add_argument("--paralelo", action="store_true")
    sub.add_parser("memoria")
    sub.add_parser("evidencias")
    sub.add_parser("relatorio")
    smoke = sub.add_parser("instruir")
    smoke.add_argument("numero")
    smoke.add_argument("--banco", type=Path, default=ESTADO / "agente.db")
    apagar = sub.add_parser("eliminar")
    apagar.add_argument("matricula")
    apagar.add_argument("nome")
    apagar.add_argument("--banco", type=Path, default=ESTADO / "agente.db")
    args = parser.parse_args()
    from .terminal import configurar_logs_terminal

    configurar_logs_terminal()
    if args.comando == "medir":
        from .avaliacao import medir

        if args.rodadas < 1:
            parser.error("rodadas deve ser positivo")
        resultado = medir(args.rodadas, args.paralelo)
    elif args.comando == "memoria":
        from .avaliacao import medir_memoria

        resultado = medir_memoria()
    elif args.comando == "evidencias":
        from .evidencias import executar

        resultado = executar()
    elif args.comando == "relatorio":
        from .relatorio import gerar

        resultado = gerar()
    elif args.comando == "instruir":
        from .agente import Servico

        pedido = next(
            (p for p in ler_json(DADOS / "pedidos.json") if p["numero"] == args.numero),
            None,
        )
        if pedido is None:
            parser.error("Número não localizado no acervo.")
        resultado = Servico(args.banco).instruir(pedido)
    elif args.comando == "eliminar":
        from .agente import Servico

        resultado = Servico(args.banco).eliminar(args.matricula, args.nome)
    print(json.dumps(resultado, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
