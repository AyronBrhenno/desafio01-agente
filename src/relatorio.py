"""Relatório reprodutível: resume arquivos, sem executar nem simular modelo."""

import statistics

from .config import RAIZ, RESULTADOS
from .ferramentas import ler_json
from .rastreabilidade import exigir_versao


def gerar():
    linhas = [
        "# Relatório de execução",
        "",
        "Acervo e norma hipotéticos. Data de análise fixa: **09/10/2026**.",
        "",
        "## Método e limites",
        "",
        "Cada configuração executa três rodadas dos 12 pedidos e das duas complementações, com banco novo por rodada. "
        "Acerto exato exige recomendação, quantidade, valor, autorização superior e conjunto dos critérios não atendidos iguais ao gabarito. "
        "Recusa segura é contabilizada como falha de cobertura, nunca como acerto. O gabarito é aberto somente pelo avaliador, após a execução; não é ferramenta ou contexto do agente.",
        "",
        "A medição avalia o sistema composto: modelo Agno, consultas, barreira e renderização fundamentada pelo código. "
        "O modelo propõe valores/estados; o código confronta todos com consultas desta execução e rejeita divergências. "
        "Detalhes, alertas, pendências e minuta são renderizados a partir das evidências validadas, sem propagar afirmações livres do modelo. "
        "Não se trata de medir o modelo isolado. Nenhuma taxa nesta amostra equivale a garantia fora do acervo.",
        "",
        "Tokens e duração são medidos; custo é uma **estimativa** com uso da API e tarifa pública de `tarifas.json`, incluindo desconto de cache retornado. "
        "Não é fatura e não inclui condições comerciais não discriminadas no uso.",
        "",
        "## Resultados finais",
        "",
        "| Configuração | Casos | Acertos exatos | Recusas | Erros liberados | Entrada | Saída | Chamadas médias | Mediana (s) | P95 (s) | Custo estimado (USD) |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    medidas = {}
    for nome in ("sequencial", "paralelo"):
        arq = RESULTADOS / f"medicao_{nome}.json"
        if not arq.exists():
            linhas += [f"| {nome} | pendente | | | | | | | | | |"]
            continue
        obj = ler_json(arq)
        exigir_versao(obj.get("configuracao", {}))
        if obj["configuracao"].get("concluida") is not True:
            raise RuntimeError(f"Medição incompleta: {arq.name}")
        medidas[nome] = obj
        r = obj["resumo"]
        custo = (
            "não disponível"
            if r["custo_estimado_usd"] is None
            else f"{r['custo_estimado_usd']:.6f}"
        )
        linhas += [
            f"| {nome} | {r['casos']} | {r['acertos_exatos']} | {r['recusas_seguras']} | {r['erros_liberados']} | {r['tokens_entrada']} | {r['tokens_saida']} | {r['chamadas_modelo_media']:.2f} | {r['segundos_mediana']:.2f} | {r['segundos_p95']:.2f} | {custo} |"
        ]
    linhas += [
        "",
        "As configurações foram executadas em processos independentes, com uso compartilhado da rede/provedor. "
        "A comparação é observacional: não isola carga do provedor nem efeito de cache. Chamadas paralelas autorizam o modelo a agrupar consultas; "
        "não significam quatro consultas simultâneas, pois cadastro e saldo têm dependências.",
        "",
        "## Estimativa anterior confrontada",
        "",
    ]
    if "sequencial" in medidas and "paralelo" in medidas:
        seq, par = medidas["sequencial"]["resumo"], medidas["paralelo"]["resumo"]
        linhas += [
            f"**Escolha do formulário: paralelo habilitado**, histórico de duas execuções e teto de seis ferramentas. "
            f"A configuração paralela acertou {par['acertos_exatos']}/{par['casos']}, contra {seq['acertos_exatos']}/{seq['casos']} na sequencial, "
            f"com redução de {(1 - par['segundos_mediana'] / seq['segundos_mediana']) * 100:.1f}% na mediana e "
            f"{(1 - par['tokens_entrada'] / seq['tokens_entrada']) * 100:.1f}% nos tokens de entrada. "
            f"A sequencial teve {seq['recusas_seguras']} recusa(s) segura(s) e {seq['erros_liberados']} saída(s) incorreta(s) liberada(s). "
            "O cadastro continua obrigatório no início de cada execução e o saldo só pode usar o cálculo confirmado.",
            "",
        ]
    for nome, obj in medidas.items():
        completos = [
            l["resultado"]["metricas"]
            for l in obj["linhas"]
            if l["tipo"] == "pedidos"
            and l["resultado"]["status"] == "validado"
            and l["resultado"]["instrucao"]["recomendacao"] != "diligencia"
        ]
        if completos:
            media = statistics.mean(m["tokens_entrada"] for m in completos)
            primeira = statistics.mean(m["chamadas"][0]["entrada"] for m in completos)
            passos = statistics.mean(m["chamadas_modelo"] for m in completos)
            estimado = 8960 if nome == "paralelo" else 11500
            linhas += [
                f"- {nome}: primeira chamada média {primeira:.1f} tokens; soma média de entrada {media:.1f}; "
                f"{passos:.2f} chamadas. Estimativa prévia {estimado}: desvio {(media / estimado - 1) * 100:+.2f}%. "
                f"Para 300 pedidos: {media * 300:,.0f} tokens de entrada, antes das complementações."
            ]
    linhas += [
        "",
        "Não se iguala crescimento do contexto à soma de entrada cobrada por todas as chamadas. "
        "As probabilidades 0,95ⁿ e 0,99ⁿ de `desenho.md` são hipóteses didáticas; os acertos e recusas observados acima são a evidência empírica.",
        "",
        "## Memória: custo por turno",
        "",
        "| Memória | Pedido | 1ª chamada de instrução do 1º turno | Entrada total do 1º turno | 1ª chamada de instrução do complemento | Entrada total do complemento | Custo do complemento (USD) | Pedido certo | Acerto |",
        "|---|---|---:|---:|---:|---:|---:|---|---|",
    ]
    arq_mem = RESULTADOS / "memoria.json"
    if arq_mem.exists():
        memoria = ler_json(arq_mem)
        exigir_versao(memoria.get("configuracao", {}))
        if memoria["configuracao"].get("concluida") is not True:
            raise RuntimeError("Medição de memória incompleta")
        for l in memoria["linhas"]:
            a, b = l["primeiro_turno"]["metricas"], l["complementacao"]["metricas"]
            primeira_a = next(
                (c["entrada"] for c in a["chamadas"] if c["finalidade"] == "instrucao"),
                "—",
            )
            primeira = next(
                (c["entrada"] for c in b["chamadas"] if c["finalidade"] == "instrucao"),
                "—",
            )
            custo = "—" if b["custo_usd"] is None else f"{b['custo_usd']:.6f}"
            linhas += [
                f"| {l['modo']} | {l['numero']} | {primeira_a} | {a['tokens_entrada']} | {primeira} | {b['tokens_entrada']} | {custo} | {l['aplicada_ao_pedido_certo']} | {l['avaliacao']['acerto_exato']} |"
            ]
    linhas += [
        "",
        "No experimento sem memória, o modelo recebe somente a complementação; o pedido completo não é reinjetado silenciosamente. "
        "O estado canônico local serve à barreira de argumentos, independentemente de o modelo recordar o caso. "
        "No modo usuário, as métricas discriminam chamadas de instrução e chamadas adicionais do MemoryManager; o custo dessas chamadas também é incluído.",
        "",
        "## Falhas e correções",
        "",
        "Esta rodada começou com os diretórios de estado e resultados vazios. O acervo e o gabarito foram preservados e conferidos antes das chamadas. "
        "Os experimentos atuais foram executados novamente. Cada arquivo registra o SHA-256 agregado dos fontes, um manifesto por arquivo "
        "de código/dados/configuração e a conclusão da execução. A conferência de hashes identifica evidências de outra versão. "
        "Documentação, resultados, bancos e segredos não integram o hash do experimento. A entrega é compactada manualmente, sem incluir o .env.",
        "",
        "Quatro falhas controladas sem API estão em `resultados/falhas_controladas.json`: matrícula inventada na consulta, retorno não informado, "
        "valor adulterado e status de API em erro. Todas devem bloquear o conteúdo e emitir a mensagem padrão. "
        "O teste de status conserva uma instrução aparentemente válida junto de ERROR para provar que conteúdo não se sobrepõe ao status.",
        "",
        "As proteções recusam situações como cadastro omitido na diligência, "
        "completude marcada como não verificada após divergência de nome, exceção urgente com antecedência ainda marcada como não atendida "
        "e tentativa de usar cadastro antigo após complementação. Esses cenários são tratados como recusa segura. "
        "A versão final força uma nova consulta de cadastro no início de cada execução e explicita os estados esperados nas instruções. "
        "As recusas não foram corrigidas relaxando a checagem de identidade, de datas ou de valores.",
        "",
        "O MemoryManager pode copiar o modelo ao criar memórias. "
        "A contagem usa um coletor por execução compartilhado entre essas cópias; "
        "as métricas incluem chamadas de instrução e de memória, sem tratar ausência de uso como custo zero.",
        "",
        "A ordem embutida da justificativa é testada nos casos reais: a capacitação com autorização verbal continua não recomendada. "
        "O incêndio em curso pode ser apto, sempre condicionado à autorização expressa e escrita. "
        "A classificação conservadora de urgência no código reconhece um conjunto limitado de relatos expressos; casos novos ou ambíguos podem ir à análise manual.",
        "",
        "## Privacidade e eliminação",
        "",
        "CPF com máscara brasileira e dados de conta/agência são removidos antes de gravar o pedido ou chamar Agno; o PIIDetectionGuardrail é uma segunda defesa, "
        "com padrões norte-americanos desativados. Cadastro retorna apenas campos funcionais. Matrículas, datas e números de pedido permanecem íntegros.",
        "",
        "O teste com APIs reais do SQLite, sem modelo, está em `eliminacao_fixture.json`. "
        "A busca da matrícula correta de Carla isoladamente encontra zero sessões: a solicitação foi gravada sob matrícula de outra pessoa. "
        "A varredura por nome em todas as tabelas localiza a cópia e remove sessões, runs, memórias, conferências e estado associado. "
        "Uma sessão de outra titular é preservada. Os recibos `eliminacao_real_*.json` verificam também os bancos preenchidos pelos experimentos reais de memória.",
        "",
        "A cópia de trabalho é retida por até 30 dias de inatividade; a limpeza ocorre na abertura do serviço. "
        "Arquivos originais do exercício e exportações de avaliação não são o banco eliminado. "
        "O registro oficial da despesa tem finalidade e guarda próprias, conforme o enunciado. "
        "Não há promessa de eliminação da infraestrutura do provedor; `store=False` evita armazenamento opcional da resposta.",
        "",
        "## Conferência humana e formulário",
        "",
        "A conferência permanece antes do encaminhamento ao ordenador: a amostra é pequena, o processo tem detecção tardia e a despesa depende de autoridade competente. "
        "O formulário mostra critérios, evidências, alertas, pendências e argumentos usados; a minuta é editável. "
        "Sugestão e encaminhamento humano são armazenados lado a lado, com motivo obrigatório quando divergirem. "
        "Essa comparação permitirá medir discordância com uso real; não há taxa de discordância inventada neste relatório.",
        "",
        "Os testes Streamlit AppTest verificam renderização, bloqueio do conteúdo recusado e exigência do motivo. "
        "A suíte utiliza respostas controladas, sem API. Além dela, `resultados/formulario_real.json` registra um teste do formulário com API real "
        "e registro persistido identificado como teste, sem substituir o modelo. Nenhum desses testes representa avaliação por usuários ou ato administrativo. "
        "O arquivo `resultados/testes.txt` registra a execução da suíte.",
        "",
        "## Fontes técnicas",
        "",
        "- [Agno: PIIDetectionGuardrail](https://docs.agno.com/reference/hooks/pii-guardrail)",
        "- [Agno: hooks e checagem de status antes de exibir](https://docs.agno.com/hooks/overview)",
        "- [Agno: persistência SQLite](https://docs.agno.com/database/providers/sqlite/usage/sqlite-for-agent)",
        "- [OpenAI: GPT-5.6 Luna e tarifa pública](https://developers.openai.com/api/docs/models/gpt-5.6-luna)",
        "",
        "As assinaturas utilizadas foram conferidas no Agno **3.0.9** instalado localmente.",
    ]
    caminho = RAIZ / "relatorio.md"
    caminho.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    return {"relatorio": str(caminho), "configuracoes_encontradas": list(medidas)}
