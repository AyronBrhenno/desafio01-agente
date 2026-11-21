# Desenho do processo — antes da implementação

Data do projeto: 21/11/2026. Data de análise do acervo: **09/10/2026**,
fixada em `dados/tabela_diarias.json`; não usar o relógio para julgar os casos.
Todos os dados e a norma são hipotéticos.

## Processo atual

1. Receber o formulário e conferir os campos obrigatórios.
2. Confrontar nome e matrícula com o cadastro; devolver divergências em diligência.
3. Consultar histórico, prestações e quantidade concedida no mês da partida.
4. Calcular antecedência, pernoites, quantidade e valor pela tabela.
5. Comparar o valor com o saldo da unidade e fundamentar cada critério.
6. Preparar recomendação e minuta; conferir e encaminhar ao ordenador.
7. Retomar o mesmo processo quando houver complementação.

## Processo com agente

1. Mascarar CPF e dados bancários antes de enviar ou persistir qualquer entrada.
2. Abrir sessão pelo número do pedido, com matrícula do solicitante como user_id.
3. Consultar cadastro, depois histórico e cálculo, depois saldo: quatro ferramentas.
4. Receber uma instrução Pydantic com seis verificações e minuta.
5. Recusar no código argumentos não ancorados no pedido/complementação e
   resultados que contrariem ferramentas ou extrapolem evidências numéricas.
6. Exibir somente a instrução aceita; o conferente edita a minuta e registra sua
   decisão com motivo de divergência. O ordenador conserva a decisão de despesa.
7. Na diligência, recuperar o pedido da sessão e aplicar somente correções
   expressas. Não preencher campos por aproximação de nomes/matrículas.

## PEAS

| Elemento | Especificação verificável |
|---|---|
| Desempenho | Acerto exato de recomendação, quantidade, valor, autorização superior e critérios não atendidos nos 12 pedidos e 2 complementações; taxa de recusa segura, tokens, duração e custo em três rodadas. Nenhum CPF/conta no contexto ou banco; nenhuma consulta com argumento inventado. |
| Ambiente | Acervo local imutável, IN hipotética 07/2026, provedor OpenAI, SQLite de trabalho e conferente humano. Gabarito acessível exclusivamente ao avaliador. |
| Atuadores | Quatro consultas somente leitura, objeto de instrução, minuta, registro da conferência e eliminação das cópias no banco do agente. Sem pagamentos ou deferimento automático. |
| Sensores | Pedido, complementação, respostas das ferramentas, histórico restrito à sessão e status/uso retornados pela API. |

## Contas prévias

Volume adotado: **300 pedidos/mês** (hipótese de planejamento).
Um passo é uma chamada ao modelo, não uma chamada de ferramenta. Sem paralelo:
quatro ferramentas e resposta final, aproximadamente **5 passos**. Com paralelo,
histórico e cálculo independentes após cadastro: aproximadamente **4 passos**.
O teto inicial é 6 chamadas de ferramentas, com orçamento adicional de 8 chamadas
ao modelo para conter repetições; esses números serão confrontados com a medição.

| Passos | Confiabilidade a 95% por passo | A 99% por passo |
|---:|---:|---:|
| 4 | 0,95⁴ = 81,45% | 0,99⁴ = 96,06% |
| 5 | 0,95⁵ = 77,38% | 0,99⁵ = 95,10% |
| 8 | 0,95⁸ = 66,34% | 0,99⁸ = 92,27% |

Independência e probabilidade constante são simplificações, não garantia empírica.
Usando a referência didática de 2.060 tokens na primeira chamada e acréscimo de
120 por passo, cinco chamadas consomem **2.060 + 2.180 + 2.300 + 2.420 + 2.540 =
11.500 tokens de entrada**, não apenas os 2.540 da última chamada. Quatro chamadas
somam 8.960. Faixa com incrementos de 90–150: 11.200–11.800 para cinco chamadas.
O esquema e as barreiras podem aumentar o contexto real: a estimativa deve ser
comparada aos tokens efetivamente retornados, incluindo complementações.

Sem uma tarifa verificada não se inventa custo: por pedido,
`(tokens_entrada_sem_cache × tarifa_entrada + tokens_cache × tarifa_cache +
tokens_saida × tarifa_saida) / 1.000.000`. Multiplicar por 300 para projeção mensal.
Tarifas em USD por milhão serão fornecidas por configuração; ausência produz
custo nulo/desconhecido, nunca zero apresentado como medido.

## Autonomia e conferência

Pagamento indevido tem reversão trabalhosa e detecção tardia em auditoria. Logo,
o agente instrui, o humano confere **antes do encaminhamento**, e o ordenador
autoriza. Erros de API ou evidência recusada vão para análise manual com mensagem
padrão. A comparação entre sugestão e decisão humana fica gravada no formulário.
A posição desse ponto será reavaliada com os erros observados, sem eliminar a
competência do ordenador (art. 10).
