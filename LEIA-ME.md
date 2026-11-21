# Desafio 01 — Instrução de pedidos de diárias

Solução em Python com **um agente Agno 3.0.9**, quatro ferramentas, contrato
Pydantic, SQLite e formulário Streamlit. Dados e IN SEMA 07/2026 são hipotéticos.
A análise usa **09/10/2026**, data do acervo, mesmo quando o programa roda depois.

## Ordem dos comandos na primeira execução (Windows / PowerShell)

O roteiro completo prepara o ambiente, executa as avaliações e abre a interface.
Execute uma etapa por vez e aguarde o comando terminar antes de passar à próxima.
Para apenas usar o formulário, faça as etapas **1, 2 e 9**; as demais produzem
os testes e as medições do desafio.

### 1. Entrar na pasta, criar e ativar o ambiente virtual

Ajuste o caminho abaixo se o projeto estiver em outra pasta. Crie o ambiente
somente na primeira preparação; se a pasta .venv já existir, basta ativá-lo.

```powershell
cd D:\desafio01-agente
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Com o ambiente ativo, o terminal costuma mostrar (.venv), e python passa a usar
o Python desse ambiente. Ao abrir outro terminal, entre na pasta do projeto e
execute novamente a ativação. Para desativá-lo ao terminar, use deactivate.
O projeto requer Python 3.10 ou superior; o ambiente testado usou Python 3.14.6.

### 2. Instalar as dependências e configurar o ambiente

```powershell
python -m pip install -r requirements.txt
if (-not (Test-Path -LiteralPath .env)) {
    Copy-Item -LiteralPath .env.example -Destination .env
}
```

Abra o .env no editor e configure OPENAI_API_KEY antes de executar as análises
com IA. Se ele já estiver configurado, preserve os valores existentes. Nunca
cole a chave no chat nem a inclua no código. Os arquivos em dados/ e o
gabarito.json já acompanham o projeto: mantenha esse conjunto como referência,
sem regenerá-lo entre as avaliações.

### 3. Executar os testes locais, sem chamadas à API

```powershell
python -m pytest -q
```

Confira o sucesso da suíte antes das medições. Os auxiliares de validação e de teste real do formulário foram restaurados em scripts/.

### 4. Gerar as evidências locais das ferramentas e das falhas provocadas

```powershell
python -m src.main evidencias
```

Não chama o modelo. Grava em resultados/ as cinco consultas às ferramentas,
as quatro falhas controladas e o teste de eliminação no SQLite. O resumo
distingue consultas_testadas de falhas_bloqueadas; uma falha bloqueada
corresponde à proteção funcionando.

**As etapas 5, 6 e 7 fazem chamadas reais à API e geram cobrança.** Execute-as
com a chave já configurada, mantendo código, acervo e gabarito iguais durante
todas as medições. Elas sobrescrevem os respectivos JSONs de resultados.

### 5. Medir o agente com chamadas sequenciais de ferramentas

```powershell
python -m src.main medir --rodadas 3
```

Executa três rodadas dos 12 pedidos e das duas complementações: 42 análises,
comparadas com o gabarito. Salva resultados/medicao_sequencial.json.

### 6. Medir o agente permitindo agrupar ferramentas independentes

```powershell
python -m src.main medir --rodadas 3 --paralelo
```

Executa as mesmas 42 análises, permitindo ao modelo solicitar ferramentas
independentes na mesma resposta. Salva resultados/medicao_paralelo.json.

### 7. Medir a memória e o custo por turno

```powershell
python -m src.main memoria
```

Compara as duas complementações sem memória, com histórico da sessão e com
histórico mais memórias do usuário. Salva resultados/memoria.json e os recibos
eliminacao_real_*.json. Essa etapa fornece as seis linhas da tabela de memória.
Recusas são registradas como falhas de cobertura, sem contar como acertos.

### 8. Gerar o relatório depois de concluir as medições

```powershell
python -m src.main relatorio
```

Lê os resultados das etapas 5, 6 e 7 e atualiza relatorio.md, incluindo
a tabela de memória e custo por turno. É uma operação local: não chama a API
nem refaz as análises. Os arquivos precisam corresponder à versão atual
dos fontes; divergências de hashes impedem gerar o relatório.

### 9. Abrir o formulário Streamlit

```powershell
python -m streamlit run app.py
```

Acesse http://127.0.0.1:8501 no navegador. O terminal ficará ocupado pelo
servidor; pressione Ctrl+C para encerrá-lo. Para executar outros comandos
enquanto ele estiver aberto, use outro terminal com o ambiente ativado.
As análises acionadas pelo formulário também usam a API e geram cobrança.
O servidor fica restrito à máquina local e a telemetria do Streamlit é desativada.

O comando instruir permite analisar um pedido pelo terminal, como alternativa
ao formulário; não é necessário executá-lo para preencher as medições:

```powershell
python -m src.main instruir DIA-2026-0101
```

### Validar o formulário real e a entrega

Depois das duas medições e do experimento de memória, execute o teste real do
formulário (usa a API), gere o relatório e faça a validação local:

```powershell
python -m scripts.formulario_real
python -m src.main relatorio
python -m scripts.validar_entrega
```

O registro produzido pelo teste do formulário é automatizado, em banco próprio,
identificado como teste. Não representa decisão de um conferente humano.

### Ajustes anteriores à nova avaliação — 21/11/2026

A suíte inicialmente falhou por ausência dos dois scripts auxiliares. Eles foram
restaurados sem reintroduzir empacotamento. O relatório passou a recusar medições
incompletas, coberto por duas regressões, e a descrever a rodada atual sem afirmar
que arquivos históricos apagados continuam disponíveis. Nenhum gabarito ou dado
de entrada foi adaptado a respostas do modelo.

### Preparar o ZIP manualmente

A entrega é compactada manualmente pelo responsável. Crie uma cópia da pasta
do projeto para montar o ZIP e retire dela o arquivo `.env` e a pasta `.venv/`.
Mantenha o `.env` original na sua máquina para continuar executando o sistema;
somente a cópia destinada ao envio deve ficar sem as credenciais.

Inclua código, testes, acervo fictício, gabarito, dependências, documentação e
os resultados que deseja apresentar. Mantenha `.env.example` como modelo de
configuração, sem chave. Também deixe fora do ZIP os bancos de trabalho em
`estado/` e os caches `__pycache__/` e `.pytest_cache/`.

Antes de enviar, abra o ZIP e confira se o `.env` e o ambiente virtual ficaram
de fora. O `.gitignore` controla o Git, mas não filtra o ZIP criado pelo
compactador do Windows.

Em 21/11/2026, o comando de empacotamento foi removido: a criação e o envio do
ZIP ficam a cargo do responsável.

O modelo padrão é `gpt-5.6-luna`; é possível definir `OPENAI_MODEL` no `.env`.
Tarifas públicas consultadas em 21/11/2026 estão em `tarifas.json`; um modelo sem
tarifa configurada produz custo desconhecido. Variáveis de preço no `.env`
substituem a tarifa pública quando as três estiverem preenchidas. Valores são
USD por milhão de tokens, com ponto decimal. O custo é estimado, não uma fatura.

O ambiente de desenvolvimento utilizou Python 3.14.6. `requirements.txt`
concentra as versões fixadas do ambiente testado, incluindo greenlet.
Em 21/11/2026, o arquivo separado de versões testadas foi consolidado nele.
As evidências anteriores permanecem vinculadas à versão original dos arquivos;
a conferência de hashes exige novas execuções para certificar esta versão.

## Testar e reproduzir as evidências

Os comandos abaixo pressupõem o ambiente virtual ativado e o terminal na raiz
do projeto. Os testes e as verificações locais não chamam a API:

```powershell
python -m pytest -q
python -m src.main evidencias
```

Para comparar a execução do agente com o gabarito e atualizar o relatório,
execute os três comandos a seguir, na ordem apresentada. As duas medições
precisam da chave já configurada no `.env` e fazem chamadas reais à API, com
cobrança. A geração do relatório é local e não faz novas chamadas ao modelo.

### 1. Medir com uma ferramenta por solicitação do modelo

```powershell
python -m src.main medir --rodadas 3
```

Executa a configuração sequencial: o modelo solicita uma ferramenta por vez e
recebe seu resultado antes de solicitar a próxima. `--rodadas 3` repete três
vezes os 12 pedidos e as duas complementações, totalizando **42 análises**.
Esse número é de casos avaliados; cada análise pode exigir várias chamadas ao modelo.

O avaliador compara cada resposta com `gabarito.json`: recomendação, quantidade
de diárias, valor total, exigência de autorização superior e conjunto dos
critérios não atendidos. O gabarito permanece separado do contexto do agente.
O comando mostra o andamento e o resumo no terminal e grava os resultados em
`resultados/medicao_sequencial.json`.

### 2. Medir permitindo agrupar solicitações de ferramentas

```powershell
python -m src.main medir --rodadas 3 --paralelo
```

Repete os mesmos casos e a mesma comparação com o gabarito, também com
**42 análises**. A diferença é permitir que o modelo solicite ferramentas
independentes na mesma resposta. Por exemplo, depois do cadastro confirmado,
pode solicitar histórico e cálculo juntos. A consulta de saldo continua
dependendo do valor calculado. Os pedidos continuam sendo processados um após
o outro; o agrupamento ocorre dentro da análise de cada pedido.

O comando grava `resultados/medicao_paralelo.json`. Comparar as duas medições
permite avaliar acertos, recusas, quantidade de chamadas, tokens, duração e
custo estimado. O ganho de desempenho depende das solicitações do modelo.

Cada medição cria um banco novo por rodada em `estado/` e sobrescreve o JSON
da sua configuração em `resultados/`. Preserve uma cópia dos resultados
anteriores se quiser comparar execuções. Dentro de cada item de `linhas`,
`avaliacao.acerto_exato` informa o acerto e `avaliacao.divergencias` lista os
campos diferentes do gabarito. Para repetir a avaliação, mantenha o acervo e
o gabarito existentes; esses comandos não os regeneram.

### 3. Gerar o relatório das medições salvas

```powershell
python -m src.main relatorio
```

Lê os arquivos `resultados/medicao_sequencial.json` e
`resultados/medicao_paralelo.json` e monta as tabelas e comparações em
`relatorio.md`, sobrescrevendo o relatório anterior. Também inclui o experimento
de memória se `resultados/memoria.json` estiver disponível. Não executa o agente
nem refaz as medições: resume os resultados salvos e verifica se correspondem
à versão atual dos arquivos. Medições ausentes aparecem como pendentes;
arquivos com hashes divergentes impedem a geração.

Outros comandos que fazem chamadas reais à API, com cobrança:

```powershell
python -m src.main instruir DIA-2026-0101
python -m src.main memoria
```

A experiência de memória envia **apenas a complementação** no segundo turno.
Se quiser atualizar também essa parte do relatório, execute `memoria` antes
de `relatorio`. As medições desta rodada ficam nos arquivos atuais de
`resultados/`, acompanhadas de seus hashes e da indicação de conclusão.

### Mensagens de recusa no terminal

Nos comandos da CLI, recusas de segurança aparecem como avisos curtos. Os avisos
repetidos da mesma análise são resumidos, sem imprimir os argumentos da consulta
nem o traceback da recusa. Por exemplo:

~~~text
AVISO Consulta bloqueada: a matrícula está ausente ou difere do pedido.
AVISO Limite de chamadas ao modelo atingido. O caso segue para análise manual.
~~~

Esses casos continuam como analise_manual e recusa segura nos resultados,
sem contar como acerto. A apresentação não altera ferramentas, limites,
chamadas ao modelo ou critérios de validação. Erros inesperados registrados
pelo Agno mantêm o diagnóstico técnico.

Alteração de apresentação em 21/11/2026, verificada por testes controlados sem
API em tests/test_terminal.py. Os resultados anteriores foram preservados;
como os fontes mudaram, novas execuções são necessárias para certificar seus
hashes com esta versão.

As evidências atuais registram o SHA-256 dos fontes e um manifesto por arquivo
de código, dados e configuração. O relatório confere esses hashes e recusa
evidências feitas com arquivos diferentes dos atuais. Se alterar os fontes,
repita as medições e a experiência de memória antes de gerar o relatório.
Documentação, resultados, bancos e `.env` não entram no hash do experimento.
Essas conferências são independentes da criação manual do ZIP.
A rodada completa de 21/11/2026 está registrada em `resultados/execucao_completa.json`.
A nota técnica e a matriz dos critérios ficam em `resultados/avaliacao_final.json`.

`gabarito.json` é lido exclusivamente por `src/avaliacao.py`; nunca integra o
prompt, as ferramentas ou o banco do agente. `gerar_dados.py` é o material
original fornecido pelo exercício e não é importado pela aplicação. Os testes das
ferramentas são executáveis sem modelo e preservam suas saídas em `resultados/`.

## Usar o formulário

1. Selecione um pedido e confira os campos. O CPF e os dados bancários já aparecem
   mascarados na cópia de trabalho.
2. Clique em **Instruir pedido**. O indicador mostra o andamento e o resultado só
   aparece depois da barreira. Erros mostram a mensagem padrão de análise manual.
3. Leia as seis verificações, alertas, pendências e argumentos das consultas.
4. Edite a minuta e registre o encaminhamento humano. Se divergir da sugestão,
   informe o motivo obrigatório. O registro não efetua concessão ou pagamento.
5. Em diligência, envie a complementação na mesma sessão. As correções expressas
   suportadas são data de retorno e matrícula. Correções ambíguas vão à análise
   manual; outras alterações podem ser feitas no formulário do pedido e reenviadas.

O parser de complementações é restrito e determinístico: não busca datas ou nomes
prováveis. Após correção expressa de matrícula, o vínculo da sessão é corrigido
para que `run` receba sempre o `user_id` vigente, mantendo o número do pedido.

## Decisões técnicas e respostas ao enunciado

### 1. Paralelismo, teto e memória: o que foi escolhido e por quê?

O formulário utiliza **chamadas paralelas habilitadas**, teto de **6 chamadas
de ferramentas** e histórico de **2 execuções** por pedido. Cadastro precede
histórico/cálculo, e saldo depende do valor calculado. O modelo tem teto adicional
de **8 chamadas de instrução**, até **12 chamadas totais** no experimento com
memórias do usuário. O limite de ferramentas sozinho não limita o número de
chamadas ao modelo. Não há repetição automática após erro de API.

As quatro consultas comuns requerem 5 passos sequenciais ou aproximadamente 4
quando o modelo agrupa histórico e cálculo. Dois turnos de histórico cobrem a
diligência e sua correção sem carregar indefinidamente sessões antigas. Um lock
permite reutilizar o mesmo agente em cache sem misturar o contexto dos pedidos.

A configuração paralela acertou **42/42 casos** nas três rodadas finais, com
3,76 chamadas ao modelo por caso em média e mediana de 6,92 segundos. Histórico e
cálculo podem ser agrupados depois do cadastro; o saldo continua dependente do
valor calculado. Os números completos, os três experimentos de memória e a
comparação com paralelo desligado estão em `relatorio.md`. O ganho de tempo não
elimina a ordem das dependências nem a conferência humana.

### 2. Como impedir instrução fundamentada em dado inventado?

Cada ferramenta passa pela barreira em `src/barreira.py`. A matrícula e as datas
devem corresponder ao pedido vigente; o grupo e a unidade devem vir do cadastro
consultado nesta execução; o valor usado na consulta de saldo deve ser exatamente
o total calculado. Divergência de identidade ou falta de campo impede mérito.
Uma tentativa inválida marca toda a execução como recusada, mesmo que o modelo
tente se corrigir depois. Cada execução é iniciada por nova consulta de cadastro.

Depois do modelo, o código verifica **status COMPLETED**, valida o Pydantic e
confronta identificação, valores, recomendação, autorização superior e estados
dos seis critérios com as evidências. Os fundamentos e a minuta exibidos são
montados pelo código a partir dessas consultas. O texto livre do modelo não
introduz fatos na instrução exibida. Nenhum conteúdo parcial ou recusado chega à
tela; a resposta pública de erro não contém instrução nem consultas recusadas.

Urgência tem uma barreira conservadora de evidência textual, sem ler os rótulos
do gerador. Incêndio em curso com focos ativos é aceito como exceção; capacitação
agendada, autorização verbal e ordens dirigidas ao sistema não dispensam regras.
Relatos novos podem ser recusados com segurança. A autorização escrita continua
pendente da autoridade competente, mesmo quando o pedido é apto.

### 3. Quais dados são guardados, por quanto tempo e como eliminar?

O banco local `estado/agente.db` contém nome, matrícula, campos do pedido já
mascarados, consultas, respostas, instruções e conferências humanas. CPF e dados
bancários não são guardados. O modo padrão usa histórico de sessão; memórias de
usuário são ativadas somente no experimento próprio. O provedor recebe a cópia
minimizada; `store=False` desativa o armazenamento opcional da resposta.

Retenção da cópia: **30 dias após a última atualização**. A limpeza por
inatividade acontece quando o serviço é aberto; sem executar o programa, não há
processo externo que apague arquivos automaticamente. O histórico injetado no
modelo é limitado a duas execuções, independentemente da retenção física.

Na aba **Eliminar cópias de trabalho**, informe matrícula correta e nome completo.
A rotina apaga sessões e runs, lista e apaga memórias com
`delete_user_memories`, varre todas as tabelas por matrícula/nome e procura também
referências às sessões encontradas. Isso alcança a sessão de Carla gravada sob a
matrícula de outro servidor. Depois compacta o SQLite e retorna contagens de
resíduos por tabela. Não há cache de sessões no agente.

Também é possível executar:

```powershell
python -m src.main eliminar 207418 "Carla Regina Souza"
```

Essa rotina atinge o banco indicado, não os arquivos originais do acervo, os
JSONs exportados de avaliação, backups externos ou registros do provedor.
O banco é uma cópia de trabalho, distinta do processo oficial de despesa.
Os dados e os CPFs dos arquivos originais são fictícios, conforme o enunciado.

### 4. Onde fica a conferência humana e como justificá-la?

O enunciado anuncia quatro perguntas, mas enumera três. Registramos aqui também
a decisão exigida pelas etapas: a conferência acontece após a barreira e antes
do encaminhamento ao ordenador. O campo editável da minuta e o registro da
decisão, com motivo de divergência, tornam essa etapa observável. Não há botão
de pagamento ou de autorização automática. Os números que fundamentam a
decisão e os limites da amostra estão no relatório.

## Organização da entrega

| Arquivo/pasta | Finalidade |
|---|---|
| `desenho.md` | Processo, PEAS, confiabilidade, passos, custo e autonomia |
| `src/ferramentas.py` | Quatro ferramentas com docstrings e aritmética |
| `src/agente.py` | Agno, limites, privacidade, status e métricas |
| `src/barreira.py` | Ancoragem e validação antes da exibição |
| `src/memoria.py` | Estado persistente, correção de sessão e eliminação |
| `src/avaliacao.py` | Gabarito, três rodadas e comparação de memória |
| `src/rastreabilidade.py` | Hash dos fontes, manifesto e detecção de mudanças |
| `app.py` | Formulário Streamlit de conferência |
| `tests/` | Testes sem chamadas ao modelo |
| `resultados/` | Evidências locais, API e eliminação |
| `relatorio.md` | Resultados, falhas, limites e decisão de conferência |

O banco não contém autenticação ou autorização de operadores: o formulário é
local, destinado ao exercício e a um conferente autorizado. Uma implantação
multiusuário exigiria controle de acesso e concorrência sobre concessões reais;

## Validação completa de 21/11/2026

Foram aprovados 36 testes locais e 84/84 análises reais nas duas configurações.
As seis condições de memória foram medidas, as quatro falhas provocadas foram
bloqueadas e os seis recibos de eliminação não apontaram resíduos dos titulares.
A auditoria dos 11 bancos e a conferência de hashes passaram. O teste real da
interface foi identificado como automatizado, sem representar decisão humana.
O servidor temporário respondeu ao health check e foi encerrado. Dados e
gabarito mantiveram os hashes iniciais. O ambiente virtual existente foi usado;
não foi feita uma instalação em máquina limpa. Nota técnica estimada: 9,5/10.
