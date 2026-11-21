"""Formulário local de conferência. Executar: streamlit run app.py."""
import json
import os
import streamlit as st
from src.agente import Servico
from src.config import DADOS, MENSAGEM_MANUAL
from src.ferramentas import ler_json
from src.privacidade import sanitizar

st.set_page_config(page_title="Conferência de diárias · SEMA", page_icon="📋", layout="wide")
st.markdown("""<style>
    .stApp {background:#f5f7fb} h1,h2,h3 {color:#123b4b}
    div[data-testid="stMetric"] {background:white;border-radius:12px;padding:18px;border:1px solid #dce5eb}
    .block-container {max-width:1200px;padding-top:2.2rem}
</style>""", unsafe_allow_html=True)

ROTULOS = {"apto_para_autorizacao": "Apto para autorização",
           "nao_recomendado": "Não recomendado", "diligencia": "Diligência"}
CRITERIOS = {"cadastro": "Identidade no cadastro", "dados_completos": "Dados obrigatórios",
             "antecedencia": "Antecedência e urgência", "prestacao_contas": "Prestação de contas",
             "limite_mensal": "Limite mensal", "saldo_orcamentario": "Saldo orçamentário"}
SITUACOES = {"atende": "Atende", "nao_atende": "Não atende", "nao_verificado": "Não verificado"}


@st.cache_resource
def obter_servico():
    return Servico(paralelo=True)


def salvar_resultado(numero, r):
    st.session_state[f"resultado:{numero}"] = r
    st.session_state.pop(f"despacho:{numero}", None)


st.caption("SEMA-MT · EXERCÍCIO COM DADOS E NORMA HIPOTÉTICOS")
st.title("Conferência de pedidos de diárias")
st.write("Confira a instrução, ajuste a minuta e registre o encaminhamento. A decisão da despesa cabe ao ordenador.")
servico = obter_servico()
pedidos = {p["numero"]: sanitizar(p) for p in ler_json(DADOS / "pedidos.json")}
with st.sidebar:
    st.subheader("Pedido em análise")
    numero = st.selectbox("Número do pedido", list(pedidos))
    st.caption("Data de análise do acervo: 09/10/2026")
    st.caption("Sessão individual por pedido. Histórico limitado às duas últimas execuções.")
    if not os.getenv("OPENAI_API_KEY", "").strip():
        st.warning("Configure sua chave no arquivo .env para executar a instrução.")

tab_pedido, tab_eliminar = st.tabs(["Instrução e conferência", "Eliminar cópias de trabalho"])
with tab_pedido:
    p = pedidos[numero]
    with st.expander("Pedido protocolado", expanded=True):
        with st.form(f"pedido:{numero}"):
            a, b, c = st.columns(3)
            matricula = a.text_input("Matrícula", p["matricula"])
            nome = b.text_input("Nome completo", p["nome"])
            data_pedido = c.text_input("Data do pedido (AAAA-MM-DD)", p["data_pedido"])
            a, b, c = st.columns(3)
            municipio = a.text_input("Município de destino", p["destino_municipio"])
            uf = b.text_input("UF", p["destino_uf"], max_chars=2)
            transporte = c.text_input("Transporte", p["transporte"])
            a, b = st.columns(2)
            partida = a.text_input("Partida (AAAA-MM-DD)", p["data_partida"])
            retorno = b.text_input("Retorno (AAAA-MM-DD)", p["data_retorno"] or "")
            justificativa = st.text_area("Justificativa", p["justificativa"], height=115)
            enviar = st.form_submit_button("Instruir pedido", type="primary")
        if enviar:
            pedido = dict(numero=numero, matricula=matricula.strip(), nome=nome.strip(),
                          data_pedido=data_pedido.strip(), destino_municipio=municipio.strip(),
                          destino_uf=uf.strip().upper(), transporte=transporte.strip(),
                          data_partida=partida.strip(), data_retorno=retorno.strip() or None,
                          justificativa=justificativa.strip())
            with st.status("Consultando dados e preparando a instrução…", expanded=True) as progresso:
                st.write("Conferindo cadastro, histórico, cálculo e saldo conforme a completude do pedido.")
                r = servico.instruir(pedido)
                salvar_resultado(numero, r)
                progresso.update(label="Instrução validada" if r["status"] == "validado" else "Análise manual necessária",
                                 state="complete" if r["status"] == "validado" else "error", expanded=False)
    r = st.session_state.get(f"resultado:{numero}")
    if r:
        if r["status"] != "validado":
            st.error(MENSAGEM_MANUAL)
        else:
            i = r["instrucao"]
            st.subheader(ROTULOS[i["recomendacao"]])
            a, b, c = st.columns(3)
            a.metric("Quantidade de diárias", "—" if i["quantidade_diarias"] is None else str(i["quantidade_diarias"]).replace(".", ","))
            b.metric("Valor total", "—" if i["valor_total"] is None else f"R$ {i['valor_total']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            c.metric("Autorização superior escrita", "Exigida" if i["exige_autorizacao_superior"] else "Sem exigência adicional")
            for alerta in i["alertas"]:
                st.warning(alerta)
            for v in i["verificacoes"]:
                with st.expander(f"{CRITERIOS[v['criterio']]} · {SITUACOES[v['situacao']]}"):
                    st.text(v["detalhe"])
            if i["pendencias"]:
                st.subheader("Pendências")
                for pendencia in i["pendencias"]:
                    st.write(f"• {pendencia}")
            with st.expander("Consultas e argumentos utilizados"):
                for consulta in r["consultas"]:
                    st.write(consulta["ferramenta"])
                    st.json(consulta["argumentos"])
            st.subheader("Registro da conferência humana")
            with st.form(f"conferencia:{numero}"):
                despacho = st.text_area("Minuta do despacho — editável", i["minuta_despacho"], height=180, key=f"despacho:{numero}")
                decisao = st.selectbox("Encaminhamento decidido pelo conferente", list(ROTULOS),
                                      index=list(ROTULOS).index(i["recomendacao"]), format_func=ROTULOS.get)
                motivo = st.text_area("Motivo da divergência (obrigatório se mudar o encaminhamento)")
                registrar = st.form_submit_button("Registrar conferência")
            if registrar:
                try:
                    servico.banco.conferir(numero, i["recomendacao"], decisao, motivo, despacho)
                    st.success("Conferência registrada. Encaminhe o processo ao responsável pela decisão.")
                except ValueError as erro:
                    st.error(str(erro))
            st.download_button("Baixar instrução validada", json.dumps(i, ensure_ascii=False, indent=2),
                               file_name=f"{numero}-instrucao.json", mime="application/json")
            if i["recomendacao"] == "diligencia":
                st.subheader("Complementação do solicitante")
                with st.form(f"complementar:{numero}"):
                    texto = st.text_area("Correção expressa da matrícula ou data de retorno", help="Exemplo: O retorno está previsto para 2026-11-20.")
                    complementar = st.form_submit_button("Reanalisar na mesma sessão")
                if complementar:
                    with st.spinner("Recuperando a sessão e verificando a complementação…"):
                        novo = servico.instruir(numero=numero, complementacao=texto)
                        salvar_resultado(numero, novo)
                    st.rerun()
        with st.expander("Consumo desta execução"):
            m = r["metricas"]
            st.write(f"Entrada: {m['tokens_entrada']} tokens · Saída: {m['tokens_saida']} tokens · Tempo: {m['segundos']:.2f} s")
            if m["custo_usd"] is not None:
                st.caption(f"Custo estimado pela tarifa pública: US$ {m['custo_usd']:.6f}")

with tab_eliminar:
    st.subheader("Eliminar dados do banco do agente")
    st.write("A eliminação alcança sessões, execuções, memórias e registros de conferência desta cópia de trabalho. O acervo original do exercício permanece disponível.")
    st.caption("Retenção local: até 30 dias após a última atualização; a limpeza ocorre ao abrir o serviço. Esta aplicação é local e deve ser operada por um conferente autorizado.")
    if "recibo_eliminacao" in st.session_state:
        recibo_anterior = st.session_state["recibo_eliminacao"]
        if recibo_anterior["eliminacao_verificada"]:
            st.success("Eliminação verificada.")
        else:
            st.error("Ainda existem resíduos; análise manual necessária.")
        st.json(recibo_anterior)
    with st.form("eliminacao"):
        mat = st.text_input("Matrícula correta do titular")
        nome_titular = st.text_input("Nome completo do titular")
        confirmado = st.checkbox("Solicito eliminar as cópias de trabalho deste titular")
        eliminar = st.form_submit_button("Eliminar e verificar o banco")
    if eliminar:
        if not confirmado:
            st.error("Marque a solicitação de eliminação.")
        else:
            try:
                recibo = servico.eliminar(mat.strip(), nome_titular.strip())
                for chave in list(st.session_state):
                    if chave.startswith(("resultado:", "despacho:", "conferencia:", "complementar:")):
                        del st.session_state[chave]
                st.session_state["recibo_eliminacao"] = recibo
                st.rerun()
            except ValueError:
                st.error("Informe a matrícula de seis dígitos e o nome completo do titular.")
