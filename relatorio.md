# Relatório de execução

Acervo e norma hipotéticos. Data de análise fixa: **09/10/2026**.

## Método e limites

Cada configuração executa três rodadas dos 12 pedidos e das duas complementações, com banco novo por rodada. Acerto exato exige recomendação, quantidade, valor, autorização superior e conjunto dos critérios não atendidos iguais ao gabarito. Recusa segura é contabilizada como falha de cobertura, nunca como acerto. O gabarito é carregado somente pelo avaliador e comparado após cada execução; não é ferramenta ou contexto do agente.

A medição avalia o sistema composto: modelo Agno, consultas, barreira e renderização fundamentada pelo código. O modelo propõe valores/estados; o código confronta todos com consultas desta execução e rejeita divergências. Detalhes, alertas, pendências e minuta são renderizados a partir das evidências validadas, sem propagar afirmações livres do modelo. Não se trata de medir o modelo isolado. Nenhuma taxa nesta amostra equivale a garantia fora do acervo.

Tokens e duração são medidos; custo é uma **estimativa** com uso da API e tarifa pública de `tarifas.json`, incluindo desconto de cache retornado. Não é fatura e não inclui condições comerciais não discriminadas no uso.

## Resultados finais

| Configuração | Casos | Acertos exatos | Recusas | Erros liberados | Entrada | Saída | Chamadas médias | Mediana (s) | P95 (s) | Custo estimado (USD) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| sequencial | 42 | 42 | 0 | 0 | 499203 | 26108 | 4.57 | 7.95 | 9.04 | 0.044560 |
| paralelo | 42 | 42 | 0 | 0 | 409274 | 25987 | 3.76 | 6.92 | 8.02 | 0.043249 |

As configurações foram executadas em processos independentes, com uso compartilhado da rede/provedor. A comparação é observacional: não isola carga do provedor nem efeito de cache. Chamadas paralelas autorizam o modelo a agrupar consultas; não significam quatro consultas simultâneas, pois cadastro e saldo têm dependências.

## Estimativa anterior confrontada

**Escolha do formulário: paralelo habilitado**, histórico de duas execuções e teto de seis ferramentas. A configuração paralela acertou 42/42, contra 42/42 na sequencial, com redução de 12.9% na mediana e 18.0% nos tokens de entrada. A sequencial teve 0 recusa(s) segura(s) e 0 saída(s) incorreta(s) liberada(s). O cadastro continua obrigatório no início de cada execução e o saldo só pode usar o cálculo confirmado.

- sequencial: primeira chamada média 2273.0 tokens; soma média de entrada 12626.1; 5.00 chamadas. Estimativa prévia 11500: desvio +9.79%. Para 300 pedidos: 3,787,830 tokens de entrada, antes das complementações.
- paralelo: primeira chamada média 2273.0 tokens; soma média de entrada 10252.9; 4.07 chamadas. Estimativa prévia 8960: desvio +14.43%. Para 300 pedidos: 3,075,860 tokens de entrada, antes das complementações.

Não se iguala crescimento do contexto à soma de entrada cobrada por todas as chamadas. As probabilidades 0,95ⁿ e 0,99ⁿ de `desenho.md` são hipóteses didáticas; os acertos e recusas observados acima são a evidência empírica.

## Memória: custo por turno

| Memória | Pedido | 1ª chamada de instrução do 1º turno | Entrada total do 1º turno | 1ª chamada de instrução do complemento | Entrada total do complemento | Custo do complemento (USD) | Pedido certo | Acerto |
|---|---|---:|---:|---:|---:|---:|---|---|
| sem | DIA-2026-0111 | 2257 | 4614 | 2172 | 21323 | 0.002087 | False | False |
| sem | DIA-2026-0112 | 2257 | 4616 | 2175 | 4450 | 0.000763 | False | False |
| historico | DIA-2026-0111 | 2257 | 4614 | 2831 | 15390 | 0.001239 | True | True |
| historico | DIA-2026-0112 | 2257 | 4616 | 2841 | 15440 | 0.001256 | True | True |
| usuario | DIA-2026-0111 | 2283 | 6956 | 2923 | 18199 | 0.002144 | True | True |
| usuario | DIA-2026-0112 | 2283 | 5763 | 2858 | 16538 | 0.001492 | True | True |

No experimento sem memória, o modelo recebe somente a complementação; o pedido completo não é reinjetado silenciosamente. O estado canônico local serve à barreira de argumentos, independentemente de o modelo recordar o caso. No modo usuário, as métricas discriminam chamadas de instrução e chamadas adicionais do MemoryManager; o custo dessas chamadas também é incluído.

## Falhas e correções

Esta rodada começou com os diretórios de estado e resultados vazios. O acervo e o gabarito foram preservados e conferidos antes das chamadas. Os experimentos atuais foram executados novamente. Cada arquivo registra o SHA-256 agregado dos fontes, um manifesto por arquivo de código/dados/configuração e a conclusão da execução. A conferência de hashes identifica evidências de outra versão. Documentação, resultados, bancos e segredos não integram o hash do experimento. A entrega é compactada manualmente, sem incluir o .env.

Quatro falhas controladas sem API estão em `resultados/falhas_controladas.json`: matrícula inventada na consulta, retorno não informado, valor adulterado e status de API em erro. Todas devem bloquear o conteúdo e emitir a mensagem padrão. O teste de status conserva uma instrução aparentemente válida junto de ERROR para provar que conteúdo não se sobrepõe ao status.

As proteções recusam situações como cadastro omitido na diligência, completude marcada como não verificada após divergência de nome, exceção urgente com antecedência ainda marcada como não atendida e tentativa de usar cadastro antigo após complementação. Esses cenários são tratados como recusa segura. A versão final força uma nova consulta de cadastro no início de cada execução e explicita os estados esperados nas instruções. As recusas não foram corrigidas relaxando a checagem de identidade, de datas ou de valores.

O MemoryManager pode copiar o modelo ao criar memórias. A contagem usa um coletor por execução compartilhado entre essas cópias; as métricas incluem chamadas de instrução e de memória, sem tratar ausência de uso como custo zero.

A ordem embutida da justificativa é testada nos casos reais: a capacitação com autorização verbal continua não recomendada. O incêndio em curso pode ser apto, sempre condicionado à autorização expressa e escrita. A classificação conservadora de urgência no código reconhece um conjunto limitado de relatos expressos; casos novos ou ambíguos podem ir à análise manual.

## Privacidade e eliminação

CPF com máscara brasileira e dados de conta/agência são removidos antes de gravar o pedido ou chamar Agno; o PIIDetectionGuardrail é uma segunda defesa, com padrões norte-americanos desativados. Cadastro retorna apenas campos funcionais. Matrículas, datas e números de pedido permanecem íntegros.

O teste com APIs reais do SQLite, sem modelo, está em `eliminacao_fixture.json`. A busca da matrícula correta de Carla isoladamente encontra zero sessões: a solicitação foi gravada sob matrícula de outra pessoa. A varredura por nome em todas as tabelas localiza a cópia e remove sessões, runs, memórias, conferências e estado associado. Uma sessão de outra titular é preservada. Os recibos `eliminacao_real_*.json` verificam também os bancos preenchidos pelos experimentos reais de memória.

A cópia de trabalho é retida por até 30 dias de inatividade; a limpeza ocorre na abertura do serviço. Arquivos originais do exercício e exportações de avaliação não são o banco eliminado. O registro oficial da despesa tem finalidade e guarda próprias, conforme o enunciado. Não há promessa de eliminação da infraestrutura do provedor; `store=False` evita armazenamento opcional da resposta.

## Conferência humana e formulário

A conferência permanece antes do encaminhamento ao ordenador: a amostra é pequena, o processo tem detecção tardia e a despesa depende de autoridade competente. O formulário mostra critérios, evidências, alertas, pendências e argumentos usados; a minuta é editável. Sugestão e encaminhamento humano são armazenados lado a lado, com motivo obrigatório quando divergirem. Essa comparação permitirá medir discordância com uso real; não há taxa de discordância inventada neste relatório.

Os testes Streamlit AppTest verificam renderização, bloqueio do conteúdo recusado e exigência do motivo. A suíte utiliza respostas controladas, sem API. Além dela, `resultados/formulario_real.json` registra um teste do formulário com API real e registro persistido identificado como teste, sem substituir o modelo. Nenhum desses testes representa avaliação por usuários ou ato administrativo. O arquivo `resultados/testes.txt` registra a execução da suíte.

## Fontes técnicas

- [Agno: PIIDetectionGuardrail](https://docs.agno.com/reference/hooks/pii-guardrail)
- [Agno: hooks e checagem de status antes de exibir](https://docs.agno.com/hooks/overview)
- [Agno: persistência SQLite](https://docs.agno.com/database/providers/sqlite/usage/sqlite-for-agent)
- [OpenAI: GPT-5.6 Luna e tarifa pública](https://developers.openai.com/api/docs/models/gpt-5.6-luna)

As assinaturas utilizadas foram conferidas no Agno **3.0.9** instalado localmente.

Consumo total da rodada: 407 chamadas ao modelo, 1053633 tokens de entrada e 60326 de saída. Custo estimado total: US$ 0.10387416, segundo as tarifas configuradas.
