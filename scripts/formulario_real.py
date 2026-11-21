"""Teste automatizado da interface com API real e banco isolado; não é revisão humana."""

import json
from unittest.mock import patch

import streamlit as st
from streamlit.testing.v1 import AppTest

from src.agente import Servico
from src.config import ESTADO, RAIZ, RESULTADOS
from src.rastreabilidade import capturar_versao, exigir_versao
from src.terminal import configurar_logs_terminal


def main():
    configurar_logs_terminal()
    versao = capturar_versao()
    servico = Servico(ESTADO / "formulario-real.db", paralelo=True)
    st.cache_resource.clear()
    with patch("src.agente.Servico", return_value=servico):
        app = AppTest.from_file(str(RAIZ / "app.py")).run(timeout=60)
        next(b for b in app.button if b.label == "Instruir pedido").click().run(timeout=180)
        r = app.session_state["resultado:DIA-2026-0101"]
        validado = r["status"] == "validado"
        registro = False
        if validado:
            campo = next(a for a in app.text_area if a.label == "Minuta do despacho — editável")
            campo.set_value(campo.value + "\n[Teste automatizado; sem revisão humana ou ato administrativo.]")
            next(b for b in app.button if b.label == "Registrar conferência").click().run(timeout=30)
            with servico.banco.conectar() as con:
                registro = con.execute(
                    "SELECT COUNT(*) FROM conferencias WHERE numero=?", ("DIA-2026-0101",)
                ).fetchone()[0] > 0
        exigir_versao(versao)
        resultado = {
            "configuracao": {**versao, "concluida": True},
            "natureza": "Teste automatizado Streamlit AppTest com API real; não é revisão humana",
            "modelo_substituido": False, "instrucao_validada": validado,
            "erros_interface": len(app.exception), "registro_teste_persistido": registro,
            "resultado": r,
        }
        RESULTADOS.mkdir(exist_ok=True)
        (RESULTADOS / "formulario_real.json").write_text(
            json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(json.dumps({k: v for k, v in resultado.items() if k not in ("resultado", "configuracao")}, ensure_ascii=True))
        if not validado or app.exception or not registro:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
