# Backtest Ovelha — documento de transferência para o novo site

Data: 19/10/2026. Origem: `Lubra-Lucas/Ovecchia`, branch `claude/gallant-ride-pdbcvn`, commit `3373d0065a0e5712ad4f9e968f1be6869dcad1bd`.

## Objetivo e conteúdo da entrega

Reaproveitar o laboratório de backtest e a apresentação dos trades em HTML no novo repositório, preservando a identidade visual, a lógica de risco/retorno em R e a separação entre cálculo e gráfico. Este documento pode ser entregue ao agente que desenvolverá o novo site.

O arquivo complementar `BACKTEST_ORIGINAL.zip` contém toda a pasta `backtest/` desse commit, incluindo estratégias, simuladores, exportadores, dois visualizadores HTML, indicador Pine, documentação e resultados arquivados. Inclui também os manifests e lockfile Python da origem, para referência de dependências. `MANIFEST_BACKTEST.json` identifica os arquivos por SHA-256. Não contém o aplicativo Streamlit, bot Telegram, suas credenciais, dados baixados ou JSONs gerados.

O apêndice deste documento transcreve integralmente os sete arquivos do caminho principal de cálculo e publicação. O ZIP preserva também os estudos especializados e o visualizador FVG.

Esta entrega é documentação e cópia de código existente. Não implementa uma nova estratégia, não publica um site e não comprova rentabilidade. Os estudos históricos não foram executados novamente para produzir esta entrega.

## 1. Arquitetura existente

```text
Histórico oficial Binance (ZIP mensal + SHA-256; API para mês atual)
    ↓ dados_binance.py
Candles OHLCV normalizados e cache local
    ↓ verificar_dados.py
Estratégia / indicadores em Python
    ↓ estrategia.py, smc.py, recuo.py ou duplo_rompimento.py
Simulação de entradas e saídas / estudos comparativos
    ↓ motor.py ou simulador específico da estratégia
Métricas, trades e resultados arquivados
    ↓ exportar_visualizador.py ou exportar_fvg_viz.py
HTML + JSONs estáticos
    ↓ servidor HTTP / hospedagem estática
Navegador: Lightweight Charts 4.2.0
```

O laboratório é independente de `app.py` e `telegram_bot.py`. O navegador exibe resultados pré-calculados e calcula alguns elementos de apresentação; não executa todo o backtest. Não há necessidade de servidor Python em produção para hospedar o relatório já gerado.

Não existe hoje um único motor universal. `motor.py` atende à Ovelha V3 (viradas de estado); FVG, recuo e duplo rompimento possuem regras e simuladores específicos. Não ligar uma estratégia nova ao motor de viradas sem verificar se seu modelo de execução é compatível.

## 2. Arquivos a preservar

| Arquivo ou pasta | Papel |
|---|---|
| `backtest/README.md` | Visão geral e comandos de operação |
| `backtest/ESTUDOS.md` | Memória dos experimentos, correções e conclusões; ler primeiro |
| `dados_binance.py` | Download oficial, checksum, normalização temporal, descarte de candle aberto |
| `verificar_dados.py` | Relatório de integridade e comparação de fontes |
| `estrategia.py` | SMA, ATR e sinais da Ovelha V3 |
| `motor.py` | Execução, trades, curva de capital e resumo da Ovelha V3 |
| `rodar_grade.py` | Configuração da grade, custos e diretório de saída |
| `teste_aleatorio.py`, `multi_ativos.py`, `experimento_saidas.py` | Referências e estudos comparativos |
| `exportar_visualizador.py` + `visualizador/index.html` | Exportação e apresentação geral dos trades |
| `smc.py`, `estudo_stop_protegido.py`, `exportar_fvg_viz.py` + `visualizador_fvg/index.html` | Cadeia específica de FVG e visualização de estrutura |
| `recuo.py`, `duplo_rompimento.py`, `estudo_*.py` | Outras hipóteses e estudos; manter para rastreabilidade |
| `tradingview/` | Indicador Pine e comparação com a implementação Python; opcional para o site |
| `resultados/` | Resultados históricos já arquivados; não são resultados de uma nova execução |
| `cache/`, `saida/` | Diretórios gerados, ignorados pelo Git e ausentes desta cópia |

## 3. Regras de execução a preservar

- Para sinais decididos no fechamento: entrada na abertura seguinte; usar apenas informações disponíveis no instante da decisão.
- Testar ausência de repaint por recorte do histórico: acrescentar candles não pode alterar sinais passados já confirmados.
- Pivôs de N candles à direita só podem ser usados depois desses N candles; não retroagir a disponibilidade do pivô à sua data visual.
- Stop e alvo no mesmo candle: stop tem prioridade. OHLC não revela a sequência intrabar.
- Gap além do stop: saída na abertura, permitindo perda maior que 1R.
- No motor V3, stop móvel usa níveis conhecidos no fechamento anterior e anda apenas a favor.
- O último trade pode permanecer aberto, marcado no último fechamento; separar de trades fechados nas estatísticas.
- Aplicar custos nas duas pontas; informar os custos realmente usados pelo experimento.
- No FVG, a entrada é limitada, não a regra de abertura seguinte. O avaliador usa a convenção conservadora de contar somente stop no candle de entrada. Preservar e explicar essa diferença.
- O primeiro FVG da pernada é o primeiro executado no tempo. Selecionar depois pela ordem de formação, entre os que acabaram executando, introduziu viés e foi corrigido.

Essas são regras metodológicas e comportamentos dos caminhos indicados, não uma certificação de todos os scripts. Novas estratégias devem ter testes próprios de execução, gaps, empate stop/alvo, confirmação de pivôs e fim de histórico.

## 4. Cálculo de R: contrato e diferenças existentes

Considere `d = +1` para compra e `d = -1` para venda:

```text
risco_preco = d × (entrada − stop_inicial)     # precisa ser positivo
risco_pct   = risco_preco / entrada
ret_bruto   = d × (saida / entrada − 1)
R_bruto     = ret_bruto / risco_pct
            = d × (saida − entrada) / risco_preco
alvo_XR     = entrada + d × X × risco_preco
```

Exemplo: compra em 100, stop em 98, saída em 104. Risco = 2; resultado = +2R bruto. O R é fixado pelo stop inicial; mover o stop não redefine a unidade de risco.

No `motor.py` original:

```python
retorno = (1 + ret_bruto) * (1 - custo_lado) ** 2 - 1
retorno_r = ret_bruto / risco_pct
```

Portanto `retorno` é líquido segundo essa convenção de custo, mas `retorno_r` e `resultado_medio_r` são BRUTOS. Para apresentar R líquido coerente com esse motor, derivar `retorno / risco_pct` e rotular separadamente. Não apresentar o campo original como líquido.

`extrair_trades` tem custo padrão de 0,001 (0,10% por lado); `rodar_grade.py` passa explicitamente 0,0005 (0,05%). Não confiar no texto do cabeçalho do HTML para descobrir qual custo foi simulado.

O FVG usa outra convenção: 0,02% de entrada + 0,05% de saída; a página usa aproximação de custo em R, taxa total dividida por risco percentual. Outros estudos também podem usar aproximações. Não misturar valores sem registrar o modelo de custos.

MFE/MAE são excursões favorável/adversa a partir de máximas/mínimas, divididas pelo risco inicial. No candle de saída não há ordenação intrabar: os extremos completos podem incluir movimento posterior à execução; isso limita a interpretação dessas medidas.

“Chegou a 1R/2R/3R antes do stop” é um diagnóstico do caminho do preço, diferente do resultado efetivo do modo de saída escolhido. Não somar esses acertos como se fossem três operações independentes.

A curva de capital original compõe retornos de exposição ao ativo. Ela não implementa automaticamente risco fixo de 1% da conta por trade. Uma curva dimensionada por risco exige uma regra explícita de tamanho da posição.

## 5. Dados e contratos

### Candles Python

A coleta entrega `time` (UTC), `open_time` (milissegundos), `open`, `high`, `low`, `close`, `volume`, `quote_volume`, `trades`. O motor V3 requer também `estado`, `faixa_sup`, `faixa_inf`, `atr`, calculados pela estratégia. Manter ordem cronológica e índices posicionais consistentes com os índices exportados dos trades.

O ATR existente é média simples de 14 True Ranges (`rolling(14).mean()`), e não a suavização Wilder/RMA. As médias da V3 são simples. Não substituir por EMA/RMA na migração sem registrar a mudança: altera sinais e resultados.

A Binance fornece arquivos de 2025 em diante com timestamps em microssegundos; a coleta normaliza para milissegundos. Para os gráficos, os exportadores convertem para segundos Unix.

A origem é spot, embora os estudos simulem compras/vendas e usem hipóteses de taxa de futuros. Não representam execução completa em futuros, com funding, margem, liquidação ou empréstimo. Para ações, criar adaptador de dados, calendários e custos apropriados; não reaproveitar o coletor Binance como fonte de ações.

A coleta precisa de HTTPS para `data.binance.vision` e `data-api.binance.vision`, sem chave. O HTML atual usa `cdn.jsdelivr.net`, `fonts.googleapis.com` e `fonts.gstatic.com`. Conferir política de rede no ambiente de destino; não desativar TLS/checksums. O coletor confere downloads novos; não refaz a conferência de checksum de um ZIP já encontrado em cache. Usar cache de procedência conhecida ou verificar novamente antes de confiar nele.

### JSON do visualizador geral

`dados/<SIMBOLO>_<TIMEFRAME>.json` contém:

- Metadados: `simbolo`, `timeframe`, `custo_lado`, `casas`, `modos`, `motivos`, `buy_hold`.
- `candles`: listas `[tempo_segundos, open, high, low, close]`.
- `combos`: chaves como `100_1.0`, com `media`, `k`, `sinais`, `saidas`, `resumo`.
- Cada sinal: `[i_entrada, dir, entrada, stop_inicial, acertou_1R, acertou_2R, acertou_3R]`.
- Cada saída por modo: `[i_saida, preco_saida, retorno_liquido, mfe_R, mae_R, indice_motivo, aberto]`.

Os índices de sinais e saídas referem-se ao MESMO vetor `candles`; não filtrar candles depois de exportar sem remapear índices. O HTML recompõe o trade combinando sinal e saída pela posição na lista.

### JSON do visualizador FVG

`dados/<ATIVO>/operacoes.json` descreve `campos`, `variantes`, `meses`, sessões e período; arquivos `<AAAA-MM>.json` carregam candles compactados por mês. Este é outro contrato e não é intercambiável com o JSON geral. O exportador pressupõe M1 contínuo e verifica diferenças de 60.000 ms. Não trocar apenas o rótulo para M5.

## 6. Temática visual a reaproveitar

Usar os HTMLs originais como referência concreta, sem recriar a interface a partir de memória:

- Controles no topo para ativo, parâmetros e modo de saída; faixa com métricas.
- Gráfico grande e ficha lateral do trade; disposição adaptada ao celular.
- Candles, médias, stop inicial/móvel, entrada e níveis 1R, 2R, 3R.
- Navegação anterior/próximo e setas do teclado; filtros de direção, ganhos/perdas e data.
- Últimos dez trades e distinção visual entre ganho/perda.
- Tema claro/escuro, tipografia IBM Plex Sans/Mono com alternativas do sistema.
- No FVG: zonas de risco/alvo, estrutura, sessões, filtros de FVG e linha pontilhada dos fechamentos.

A biblioteca é `lightweight-charts@4.2.0`, carregada via CDN. Não é um widget hospedado do TradingView e não é o Strategy Tester. Pine é uma integração separada e opcional.

O código original recalcula SMA/ATR e alguns números no navegador para desenhar. Na migração, testar paridade com Python; não duplicar regras de execução em JavaScript sem necessidade. Novas APIs da biblioteca podem exigir mudanças: preservar 4.2.0 primeiro e tratar atualização de versão separadamente. Ao publicar, preservar as licenças e verificar os requisitos de atribuição da biblioteca.

Não há grade de screening em tempo real nem ponto final pulsando nessa entrega. Essa é uma evolução separada do relatório histórico.

## 7. Reprodução do pacote e geração do site

Os comandos abaixo descrevem o caminho original, com criação explícita dos diretórios necessários. Exigem rede e download de histórico. Não foram executados novamente durante a preparação deste documento.

Extrair `BACKTEST_ORIGINAL.zip` na raiz do novo repositório, preservando sua estrutura. Os manifests Python da raiz são os da origem; revisar antes de copiar sobre manifests que já existam. Não sobrescrever arquivos do novo projeto cegamente. Python >= 3.11; a instalação anterior na origem usou Python 3.12.14 e uv 0.12.23.

Para reproduzir as dependências do snapshot em um diretório que aceite seus manifests:

```bash
uv sync --frozen --python python3.12
```

No ambiente Codex com cache padrão somente leitura, acrescentar `--cache-dir /workspace/.cache/uv`. As bibliotecas usadas pelo caminho principal são pandas, numpy, requests e matplotlib; o lockfile original contém também dependências do aplicativo antigo. Não executar `uv add` apenas para reproduzir o snapshot.

Dentro de `backtest/`, com o ambiente Python ativado:

```bash
mkdir -p cache saida
python -c "import dados_binance as d; d.carregar('BTCUSDT','1h').to_pickle('cache/BTCUSDT_1h.pkl')"
python -c "import pandas as pd, verificar_dados as v; v.verificar(pd.read_pickle('cache/BTCUSDT_1h.pkl'), '1h')"
python rodar_grade.py BTCUSDT 1h
python teste_aleatorio.py BTCUSDT 1h
python exportar_visualizador.py 1h BTCUSDT
mkdir -p saida/site/dados
cp visualizador/index.html saida/site/index.html
cp saida/visualizador/BTCUSDT_1h.json saida/site/dados/
python -m http.server --bind 127.0.0.1 --directory saida/site 8000
```

A verificação de dados imprime problemas e retorna buracos; status zero sozinho não prova integridade. Conferir os resultados e exigir ordem, unicidade, alinhamento, OHLC válido e investigação de lacunas.

Este exemplo gera somente BTC H1. O HTML original oferece cinco ativos em `ATIVOS`; para publicar BTC apenas, configurar essa lista para `['BTCUSDT']` numa cópia do HTML ou gerar todos os arquivos que a interface oferece. O `TF` do HTML original é fixo em `'1h'`. Exportar M5 não muda o HTML automaticamente.

Outro detalhe: a grade contém datas de corte por período (`2018–2021`, `2022–2026`). Com pouco histórico, alguns resumos podem falhar ou não ser adequados; esses scripts não são uma CLI genérica para qualquer janela. Para o novo estudo BTC M5, criar configuração explícita de período, parâmetros e resumo apropriado, sem fingir que o exemplo H1 é o estudo novo.

Para a página FVG original (fluxo especializado M1, não exigido no novo site):

```bash
python -c "import dados_binance as d; d.carregar('BTCUSDT','1m',desde=(2026,3)).to_pickle('cache/BTCUSDT_1m.pkl')"
python exportar_fvg_viz.py 2026-04-01 BTCUSDT
cp visualizador_fvg/index.html saida/visualizador_fvg/index.html
python -m http.server --bind 127.0.0.1 --directory saida/visualizador_fvg 8001
```

Também ajustar a lista de ativos dessa cópia do HTML se gerar somente BTC. Os caminhos de comando partem de `backtest/`, não da raiz.

## 8. Publicação do relatório HTML

A unidade de publicação é a pasta gerada inteira, não somente `index.html`:

```text
site/
  index.html
  dados/
    BTCUSDT_1h.json
```

Ou, para FVG:

```text
site/
  index.html
  dados/
    BTCUSDT/
      operacoes.json
      2026-04.json
      ...demais meses declarados em operacoes.json
```

Servir HTML e JSON pela mesma origem HTTP/HTTPS, mantendo caminhos relativos. Abrir o HTML diretamente como arquivo local pode impedir `fetch`. A pasta pode ser publicada em uma hospedagem estática; não é obrigatório instalar Streamlit, manter Python ativo ou utilizar EC2.

Publicar uma versão completa e consistente: gerar resultados, conferir os arquivos, preparar um artefato e então atualizar a hospedagem. Evitar misturar HTML de uma versão com JSON de outra. Usar pasta/versionamento de execução e invalidar cache quando atualizar os nomes fixos dos JSONs. O ZIP inclui hashes dos fontes; para uma execução nova, registrar também período dos dados, parâmetros, taxas, seed e commit usado.

Na origem NÃO foi encontrada publicação automática desse laboratório. `.github/workflows/deploy.yml` atende ao aplicativo antigo: push na main → SSH para EC2 Windows → atualização do checkout → reinício dos serviços web/bot. Não copiar esse workflow, seus secrets nem seus comandos de reset para o novo site.

Uma automação futura pode: preparar dependências → validar dados e testes → executar estudo/exportador → verificar HTML/JSON → publicar o artefato estático. Isso é uma proposta de integração, não um pipeline já implementado ou verificado. Escolher a hospedagem no novo repositório; não há URL pública confirmada nesta entrega.

## 9. Critérios de aceite no novo repositório

1. Preservar a rastreabilidade da cópia e dos resultados existentes; resultados arquivados não se tornam uma nova validação.
2. Testar não repaint e conhecimento temporal de sinais/pivôs; validar gaps, prioridade do stop, instante da entrada e trades abertos.
3. Guardar dados brutos e gerados fora do controle de versão quando apropriado; publicar somente o artefato necessário.
4. Rejeitar risco inválido/zero e tratar explicitamente ausência de trades, janelas curtas e dados insuficientes. O motor legado não tem tratamento completo desses casos.
5. Informar ativo, timeframe, período, estratégia, parâmetros, custo e modelo de execução junto aos resultados.
6. Separar R bruto e líquido; conferir um trade manualmente em cada direção e comparar Python, JSON e ficha HTML.
7. Conferir a curva de capital pelo produto dos retornos e por cálculo independente. A duração no motor original é contagem de barras, embora um resumo use o nome `duracao_media_h`; converter para horas com o timeframe, em vez de assumir que cada barra é uma hora.
8. Recalcular referências aleatórias com seed registrada. O HTML geral contém valores ALEATORIO fixos para estudos H1 anteriores; não os apresentar como se fossem resultados de uma nova estratégia/M5.
9. Testar no navegador o carregamento de cada ativo, navegação, filtros, níveis, redimensionamento e consistência das métricas. HTTP 200 sozinho não valida o gráfico.
10. Após publicação, conferir a versão realmente servida, requests JSON, console e integridade visual; não confundir geração local com publicação.

Não apresentar os resultados como execução real de mercado: slippage, spread, funding, liquidez e calendário precisam de modelo explícito quando relevantes. O código preservado é uma base de pesquisa, não uma certificação de simulação completa.

## 10. Histórico que o novo projeto deve conhecer

Ler `ESTUDOS.md` integralmente. Na seção 12 está a correção do viés do primeiro FVG, que inflava resultados; na 13, o estudo de stop protegido. A estratégia FVG foi arquivada por decisão do usuário, pois a interpretação de pernadas/fractais ainda não estava fechada. A seção 15 trata do recuo na tendência com saída na média de 5: acerto elevado, mas sem vantagem convincente sobre a referência aleatória.

A proposta recente de falha de rompimento BTC M5 foi discutida nesta conversa, mas não foi implementada nem testada. A proposta de screening de ações com linha pontilhada e ponto pulsando também não está implementada. Não atribuir resultados dos estudos antigos a essas propostas.

## 11. Texto de orientação para o agente do novo repositório

> Use este documento e o ZIP original como referência de migração. Comece por backtest/ESTUDOS.md e backtest/README.md. Preserve a separação dados → sinais → simulação → métricas → JSON → HTML. Reaproveite a temática dos visualizadores com Lightweight Charts 4.2.0 e mantenha as regras de execução temporal. Diferencie R bruto de líquido. Não copie o aplicativo Streamlit, bot ou o deploy EC2. Primeiro reproduza um conjunto de trades e confira no gráfico; depois adapte a interface ao novo site. Marque claramente o que é legado, o que mudou e o que foi de fato executado. Cada tarefa Codex já usa um ambiente isolado: use o checkout existente e não crie worktree sem solicitação explícita. A publicação estática precisa incluir os JSONs e ser validada após o deploy.

## Apêndice — código original do caminho principal

Os arquivos abaixo foram extraídos sem alteração do commit indicado. Para todos os outros arquivos, incluindo o caminho FVG completo, usar o ZIP e o manifesto. Qualquer adaptação deve ser feita no novo repositório e identificada como mudança posterior.

### `backtest/dados_binance.py`

SHA-256: `e889648f5ad54546695ba9d3aebd2705d840dec27be5cfc314f6b9eceb18c4af`

````python
"""
Coleta de candles (klines) do spot da Binance a partir de fontes oficiais e públicas.

Fontes:
  - data.binance.vision      -> arquivos mensais oficiais (ZIP + checksum SHA-256)
  - data-api.binance.vision  -> API pública, usada só para o mês corrente

Nenhuma chave de API é necessária.
"""

import hashlib
import io
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

ARQUIVOS_URL = "https://data.binance.vision/data/spot/monthly/klines"
API_URL = "https://data-api.binance.vision/api/v3/klines"
CACHE_DIR = Path(__file__).parent / "cache"

COLUNAS = [
    "open_time", "open", "high", "low", "close", "volume",
    "close_time", "quote_volume", "trades", "taker_buy_base", "taker_buy_quote", "ignore",
]

# Duração exata de cada timeframe (em milissegundos)
TIMEFRAMES_MS = {
    "1m": 60_000,
    "5m": 300_000,
    "15m": 900_000,
    "1h": 3_600_000,
    "4h": 14_400_000,
    "1d": 86_400_000,
}


def _get(url, params=None, tentativas=4):
    """GET com novas tentativas em caso de falha de rede (2s, 4s, 8s)."""
    for i in range(tentativas):
        try:
            r = requests.get(url, params=params, timeout=60)
            if r.status_code == 404:
                return None
            r.raise_for_status()
            return r
        except requests.RequestException:
            if i == tentativas - 1:
                raise
            time.sleep(2 ** (i + 1))


def _para_ms(serie):
    """A Binance passou a usar microssegundos nos arquivos de 2025 em diante; normaliza tudo para ms."""
    serie = serie.astype("int64")
    return serie.where(serie < 10**14, serie // 1000)


def _ler_csv(conteudo):
    df = pd.read_csv(io.BytesIO(conteudo), header=None, names=COLUNAS)
    # Alguns arquivos trazem cabeçalho; nesse caso a primeira linha não é numérica
    if not str(df.iloc[0, 0]).isdigit():
        df = df.iloc[1:]
    return df


def baixar_mes(simbolo, timeframe, ano, mes):
    """
    Baixa um arquivo mensal oficial, confere o SHA-256 e guarda em cache.
    Retorna (DataFrame, status) onde status é 'ok', 'cache' ou 'inexistente'.
    """
    nome = f"{simbolo}-{timeframe}-{ano}-{mes:02d}.zip"
    destino = CACHE_DIR / simbolo / timeframe / nome
    if destino.exists():
        with zipfile.ZipFile(destino) as z:
            return _ler_csv(z.read(z.namelist()[0])), "cache"

    url = f"{ARQUIVOS_URL}/{simbolo}/{timeframe}/{nome}"
    resp_checksum = _get(url + ".CHECKSUM")
    if resp_checksum is None:
        return None, "inexistente"
    checksum_oficial = resp_checksum.text.split()[0].strip().lower()

    conteudo = _get(url).content
    checksum_calculado = hashlib.sha256(conteudo).hexdigest()
    if checksum_calculado != checksum_oficial:
        raise ValueError(f"Checksum não confere em {nome}: {checksum_calculado} != {checksum_oficial}")

    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(conteudo)
    with zipfile.ZipFile(io.BytesIO(conteudo)) as z:
        return _ler_csv(z.read(z.namelist()[0])), "ok"


def baixar_api(simbolo, timeframe, inicio_ms, fim_ms=None):
    """Baixa candles pela API pública, paginando de 1000 em 1000."""
    linhas = []
    cursor = inicio_ms
    while True:
        params = {"symbol": simbolo, "interval": timeframe, "startTime": cursor, "limit": 1000}
        if fim_ms is not None:
            params["endTime"] = fim_ms
        lote = _get(API_URL, params).json()
        if not lote:
            break
        linhas.extend(lote)
        if len(lote) < 1000:
            break
        cursor = lote[-1][0] + TIMEFRAMES_MS[timeframe]
    return pd.DataFrame(linhas, columns=COLUNAS)


def _meses(inicio, fim):
    ano, mes = inicio
    while (ano, mes) <= fim:
        yield ano, mes
        mes += 1
        if mes > 12:
            ano, mes = ano + 1, 1


def carregar(simbolo, timeframe, desde=(2017, 8), verbose=True):
    """
    Monta o histórico completo: arquivos mensais oficiais até o mês anterior
    e a API pública para o mês corrente. Só devolve candles já fechados.
    """
    agora = datetime.now(timezone.utc)
    mes_anterior = (agora.year, agora.month - 1) if agora.month > 1 else (agora.year - 1, 12)

    partes, relatorio = [], []
    for ano, mes in _meses(desde, mes_anterior):
        df_mes, status = baixar_mes(simbolo, timeframe, ano, mes)
        relatorio.append((f"{ano}-{mes:02d}", status, 0 if df_mes is None else len(df_mes)))
        if df_mes is not None:
            partes.append(df_mes)

    inicio_mes_atual = int(datetime(agora.year, agora.month, 1, tzinfo=timezone.utc).timestamp() * 1000)
    df_api = baixar_api(simbolo, timeframe, inicio_mes_atual)
    relatorio.append((f"{agora.year}-{agora.month:02d} (API)", "ok", len(df_api)))
    partes.append(df_api)

    df = pd.concat(partes, ignore_index=True)
    df["open_time"] = _para_ms(df["open_time"])
    df["close_time"] = _para_ms(df["close_time"])
    for c in ["open", "high", "low", "close", "volume", "quote_volume"]:
        df[c] = df[c].astype(float)
    df["trades"] = df["trades"].astype("int64")

    # Descarta o candle ainda em formação
    agora_ms = int(time.time() * 1000)
    df = df[df["close_time"] < agora_ms]

    df["time"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    df = df[["time", "open_time", "open", "high", "low", "close", "volume", "quote_volume", "trades"]]

    if verbose:
        for periodo, status, n in relatorio:
            print(f"  {periodo:<16} {status:<12} {n:>7} candles")
    return df.reset_index(drop=True)

````

### `backtest/verificar_dados.py`

SHA-256: `611e7a585b6a8bc2b1270ddccc900c92d53b8b0898adeaffec1cdac19862ffca`

````python
"""
Verificações de integridade de uma série de candles.
Não corrige nada: só aponta problemas para decidirmos o que fazer.
"""

import pandas as pd

from dados_binance import TIMEFRAMES_MS


def verificar(df, timeframe, salto_suspeito=0.15):
    passo = TIMEFRAMES_MS[timeframe]
    print(f"Candles: {len(df)}  |  {df['time'].iloc[0]}  ->  {df['time'].iloc[-1]}")

    # 1. Ordem e duplicados
    print(f"\n[1] Ordem cronológica: {'OK' if df['open_time'].is_monotonic_increasing else 'FORA DE ORDEM'}")
    dup = df['open_time'].duplicated().sum()
    print(f"[2] Duplicados: {dup}")

    # 2. Alinhamento ao timeframe (ex.: H1 sempre começando em hh:00)
    desalinhados = (df['open_time'] % passo != 0).sum() if timeframe != "1d" else (df['open_time'] % 86_400_000 != 0).sum()
    print(f"[3] Candles desalinhados do timeframe: {desalinhados}")

    # 3. Buracos
    diffs = df['open_time'].diff().iloc[1:]
    buracos = df.loc[diffs[diffs != passo].index]
    esperados = (df['open_time'].iloc[-1] - df['open_time'].iloc[0]) // passo + 1
    print(f"[4] Candles esperados: {esperados}  recebidos: {len(df)}  faltando: {esperados - len(df)}")
    if len(buracos):
        print(f"    {len(buracos)} buraco(s):")
        for idx in buracos.index:
            antes = df['time'].iloc[idx - 1]
            depois = df['time'].iloc[idx]
            faltam = int(diffs.loc[idx] // passo) - 1
            print(f"      {antes}  ->  {depois}   ({faltam} candles faltando)")

    # 4. Coerência OHLC
    ohlc_ruim = df[(df['high'] < df[['open', 'close', 'low']].max(axis=1)) |
                   (df['low'] > df[['open', 'close', 'high']].min(axis=1))]
    print(f"\n[5] Candles com OHLC incoerente (máx < abertura/fech. ou mín > abertura/fech.): {len(ohlc_ruim)}")
    nao_positivos = (df[['open', 'high', 'low', 'close']] <= 0).any(axis=1).sum()
    print(f"[6] Preços zero ou negativos: {nao_positivos}")
    vol_zero = (df['volume'] == 0).sum()
    print(f"[7] Candles com volume zero: {vol_zero}")
    if vol_zero:
        print(df.loc[df['volume'] == 0, ['time', 'open', 'high', 'low', 'close', 'trades']].head(10).to_string(index=False))

    # 5. Saltos anormais entre fechamento anterior e abertura seguinte, e candles gigantes
    gap_abertura = (df['open'] / df['close'].shift(1) - 1).abs()
    amplitude = df['high'] / df['low'] - 1
    print(f"\n[8] Saltos fechamento->abertura > {salto_suspeito:.0%}: {(gap_abertura > salto_suspeito).sum()}")
    print("    Maiores saltos fechamento->abertura:")
    for idx in gap_abertura.nlargest(5).index:
        print(f"      {df['time'].iloc[idx]}  {gap_abertura.iloc[idx]:.2%}  (fech. ant. {df['close'].iloc[idx-1]:.2f} -> abert. {df['open'].iloc[idx]:.2f})")
    print("    Maiores amplitudes (máx/mín) num candle:")
    for idx in amplitude.nlargest(5).index:
        r = df.iloc[idx]
        print(f"      {r['time']}  {amplitude.iloc[idx]:.2%}  (mín {r['low']:.2f}  máx {r['high']:.2f})")
    return buracos


def agregar(df, regra):
    """Reamostra candles para um timeframe maior (ex.: '1D', '4h')."""
    return df.set_index('time').resample(regra, label='left', closed='left').agg(
        {'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'}
    ).dropna()


def comparar(a, b, nome_a, nome_b, tol=1e-9):
    """Compara duas séries OHLCV candle a candle, nos horários em comum."""
    a = a.set_index('time') if 'time' in a.columns else a
    b = b.set_index('time') if 'time' in b.columns else b
    comum = a.index.intersection(b.index)
    print(f"\nComparando {nome_a} x {nome_b}: {len(comum)} candles em comum")
    for c in ['open', 'high', 'low', 'close', 'volume']:
        dif_rel = ((a.loc[comum, c] - b.loc[comum, c]).abs() / b.loc[comum, c].abs().clip(lower=1e-12))
        n_dif = (dif_rel > tol).sum()
        print(f"  {c:<7} divergentes: {n_dif:>5}   maior diferença relativa: {dif_rel.max():.2e}")
    return comum

````

### `backtest/estrategia.py`

SHA-256: `cb7c0b758314891e5a4615cdb8d2d9e0f43bf78f1d8e9b0991b566067410ed81`

````python
"""
Ovelha V3: média móvel + faixa de ATR com histerese.

  close > média + k·ATR  -> COMPRA (+1)
  close < média - k·ATR  -> VENDA  (-1)
  dentro da faixa        -> mantém o estado anterior

O estado é decidido no fechamento do candle e só usa dados até aquele candle.
"""

import numpy as np
import pandas as pd


def calcular_atr(df, periodo=14):
    fech_ant = df['close'].shift(1)
    tr = pd.concat([
        df['high'] - df['low'],
        (df['high'] - fech_ant).abs(),
        (df['low'] - fech_ant).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(periodo).mean()


def calcular_sinais(df, periodo_media=100, k=1.0, periodo_atr=14):
    """Devolve uma cópia do df com as colunas media, atr, faixa_sup, faixa_inf e estado (+1, -1 ou 0 antes do 1º sinal)."""
    out = df.copy()
    out['media'] = out['close'].rolling(periodo_media).mean()
    out['atr'] = calcular_atr(out, periodo_atr)
    out['faixa_sup'] = out['media'] + k * out['atr']
    out['faixa_inf'] = out['media'] - k * out['atr']

    gatilho = pd.Series(np.nan, index=out.index)
    gatilho[out['close'] > out['faixa_sup']] = 1
    gatilho[out['close'] < out['faixa_inf']] = -1
    out['estado'] = gatilho.ffill().fillna(0).astype(int)
    return out

````

### `backtest/motor.py`

SHA-256: `d2bad907cf1b39e4539fb5b4408afc068d303d3f40d24f1b71698d84e9729d52`

````python
"""
Motor de backtest da Ovelha V3.

Regras de honestidade:
  - o estado do candle i (fechamento) só é executado na ABERTURA do candle i+1
  - stops e alvos são ordens que só passam a valer a partir do candle de entrada;
    se o candle abrir além do stop, a saída é na abertura (gap), nunca no preço do stop
  - se stop e alvo forem tocados no mesmo candle, conta como stop (postura conservadora)
  - custo por lado aplicado em toda entrada e saída
  - o último trade, se ainda aberto, é marcado no último fechamento e sinalizado como aberto

Modos de saída:
  - 'virada'      sai só quando o sinal vira (sempre posicionado)
  - 'stop_movel'  stop começa na faixa oposta e só anda a favor; tocado, fica fora até a próxima virada
  - 'alvo'        sai no alvo (alvo_r × R) ou no stop inicial; se nenhum for tocado, sai na virada
"""

import numpy as np
import pandas as pd

ALVOS_R = (1, 2, 3)


def _primeiro(mascara):
    """Índice do primeiro True, ou infinito se não houver."""
    return int(np.argmax(mascara)) if mascara.any() else np.inf


def extrair_trades(df, custo_lado=0.001, saida='virada', alvo_r=None, stop_atr=None):
    """
    df precisa ter: time, open, high, low, close, estado, faixa_sup, faixa_inf, atr.
    stop_atr: se informado, o stop inicial fica a stop_atr × ATR da entrada (em vez da faixa oposta).
    """
    estado = df['estado'].to_numpy()
    abertura = df['open'].to_numpy()
    maxima = df['high'].to_numpy()
    minima = df['low'].to_numpy()
    fech = df['close'].to_numpy()
    tempo = df['time'].to_numpy()
    f_sup = df['faixa_sup'].to_numpy()
    f_inf = df['faixa_inf'].to_numpy()
    atr = df['atr'].to_numpy()
    n = len(df)

    # índices dos candles em que o estado mudou (sinal no fechamento)
    viradas = [i for i in range(1, n) if estado[i] != 0 and estado[i] != estado[i - 1]]

    trades = []
    for j, i_sinal in enumerate(viradas):
        e = i_sinal + 1                       # candle de entrada (abertura)
        if e >= n:
            break                             # sinal no último candle: ainda não executado
        d = int(estado[i_sinal])
        entrada = abertura[e]
        faixa_oposta = f_inf if d == 1 else f_sup
        if stop_atr is None:
            stop_inicial = faixa_oposta[i_sinal]
        else:
            stop_inicial = entrada - d * stop_atr * atr[i_sinal]
        risco = d * (entrada - stop_inicial) / entrada        # R como fração do preço

        # fim natural do sinal: abertura do candle seguinte à próxima virada
        if j + 1 < len(viradas) and viradas[j + 1] + 1 < n:
            fim, aberto_natural = viradas[j + 1] + 1, False
            ultimo = fim - 1
        else:
            fim, aberto_natural = n - 1, True
            ultimo = n - 1
        mx, mn, ab = maxima[e:ultimo + 1], minima[e:ultimo + 1], abertura[e:ultimo + 1]

        # ---- assertividade do sinal: chegou a XR antes de tocar o stop inicial? ----
        toque_stop = _primeiro(mn <= stop_inicial) if d == 1 else _primeiro(mx >= stop_inicial)
        acertos = {}
        for x in ALVOS_R:
            preco_alvo = entrada * (1 + d * x * risco)
            toque = _primeiro(mx >= preco_alvo) if d == 1 else _primeiro(mn <= preco_alvo)
            acertos[x] = toque < toque_stop

        # ---- saída conforme o modo ----
        i_saida = fim
        preco_saida = fech[n - 1] if aberto_natural else abertura[fim]
        motivo = 'em aberto' if aberto_natural else 'virada'

        if saida == 'stop_movel':
            # stop vigente no candle e+t = nível conhecido no fechamento anterior (só anda a favor)
            niveis = np.r_[stop_inicial, faixa_oposta[e:ultimo]]
            stop_vig = np.maximum.accumulate(niveis) if d == 1 else np.minimum.accumulate(niveis)
            t = _primeiro(mn <= stop_vig) if d == 1 else _primeiro(mx >= stop_vig)
            if t != np.inf:
                i_saida = e + t
                preco_saida = min(ab[t], stop_vig[t]) if d == 1 else max(ab[t], stop_vig[t])
                motivo = 'stop móvel'
        elif saida == 'alvo':
            preco_alvo = entrada * (1 + d * alvo_r * risco)
            t_alvo = _primeiro(mx >= preco_alvo) if d == 1 else _primeiro(mn <= preco_alvo)
            if toque_stop != np.inf and toque_stop <= t_alvo:
                t = toque_stop
                i_saida = e + t
                preco_saida = min(ab[t], stop_inicial) if d == 1 else max(ab[t], stop_inicial)
                motivo = 'stop'
            elif t_alvo != np.inf:
                t = t_alvo
                i_saida = e + t
                preco_saida = max(ab[t], preco_alvo) if d == 1 else min(ab[t], preco_alvo)
                motivo = f'alvo {alvo_r}R'

        aberto = motivo == 'em aberto'
        saiu_no_candle = motivo not in ('virada', 'em aberto')
        fim_janela = i_saida if saiu_no_candle else (ultimo if aberto else i_saida - 1)
        jmx, jmn = maxima[e:fim_janela + 1], minima[e:fim_janela + 1]
        if d == 1:
            mfe, mae = jmx.max() / entrada - 1, jmn.min() / entrada - 1
        else:
            mfe, mae = 1 - jmn.min() / entrada, 1 - jmx.max() / entrada

        ret_bruto = d * (preco_saida / entrada - 1)
        ret = (1 + ret_bruto) * (1 - custo_lado) ** 2 - 1
        trades.append({
            'direcao': 'COMPRA' if d == 1 else 'VENDA',
            'dir': d,
            'i_sinal': int(i_sinal), 'i_entrada': int(e), 'i_saida': int(i_saida),
            'tempo_entrada': pd.Timestamp(tempo[e]), 'tempo_saida': pd.Timestamp(tempo[i_saida]),
            'preco_entrada': float(entrada), 'preco_saida': float(preco_saida),
            'stop_inicial': float(stop_inicial),
            'risco_pct': float(risco),
            'retorno_bruto': float(ret_bruto),
            'retorno': float(ret),
            'retorno_r': float(ret_bruto / risco) if risco > 0 else np.nan,
            'mfe_pct': float(mfe), 'mae_pct': float(mae),
            'mfe_r': float(mfe / risco) if risco > 0 else np.nan,
            'mae_r': float(mae / risco) if risco > 0 else np.nan,
            'duracao': int(i_saida - e),
            'acerto_1r': acertos[1], 'acerto_2r': acertos[2], 'acerto_3r': acertos[3],
            'motivo': motivo,
            'aberto': aberto,
        })
    return pd.DataFrame(trades)


def curva_capital(df, trades, custo_lado=0.001):
    """Capital marcado no fechamento de cada candle (começa em 1.0). Fora de posição, fica parado."""
    fech = df['close'].to_numpy()
    eq = np.ones(len(df))
    capital = 1.0
    ultimo_i = 0
    for t in trades.itertuples():
        e, s = t.i_entrada, t.i_saida
        eq[ultimo_i:e] = capital
        base = capital * (1 - custo_lado)
        # dentro do trade: marcação a mercado nos fechamentos
        eq[e:s] = base * (1 + t.dir * (fech[e:s] / t.preco_entrada - 1))
        capital = capital * (1 + t.retorno)
        ultimo_i = s
    eq[ultimo_i:] = capital
    return pd.Series(eq, index=df['time'])


def drawdown_max(eq):
    return float((eq / eq.cummax() - 1).min())


def resumo(trades, eq):
    fechados = trades[~trades['aberto']]
    anos = (eq.index[-1] - eq.index[0]).days / 365.25
    ganhos = fechados.loc[fechados['retorno'] > 0, 'retorno'].sum()
    perdas = -fechados.loc[fechados['retorno'] <= 0, 'retorno'].sum()
    sinais = trades.iloc[:-1] if len(trades) and trades['aberto'].iloc[-1] else trades
    return {
        'retorno_total': eq.iloc[-1] - 1,
        'retorno_anual': eq.iloc[-1] ** (1 / anos) - 1,
        'dd_max': drawdown_max(eq),
        'trades': len(fechados),
        'acerto': (fechados['retorno'] > 0).mean(),
        'profit_factor': ganhos / perdas if perdas > 0 else np.inf,
        'duracao_media_h': fechados['duracao'].mean(),
        'resultado_medio_r': fechados['retorno_r'].mean(),
        'acerto_1r': sinais['acerto_1r'].mean(),
        'acerto_2r': sinais['acerto_2r'].mean(),
        'acerto_3r': sinais['acerto_3r'].mean(),
        'risco_mediano': fechados['risco_pct'].median(),
        'mfe_mediano': fechados['mfe_pct'].median(),
        'mae_mediano': fechados['mae_pct'].median(),
    }

````

### `backtest/rodar_grade.py`

SHA-256: `de63ed06780a6a1907afa26ba9f710fda84b57e49107afe0e35a614eb0d6cf9c`

````python
"""
Roda a grade de parâmetros da Ovelha V3 num ativo/timeframe e salva os resultados.

Uso: python rodar_grade.py BTCUSDT 1h
"""

import sys
from pathlib import Path

import pandas as pd

import estrategia as est
import motor as m

MEDIAS = [50, 100, 200]
KS = [0.5, 1.0, 1.5, 2.0]
INICIO = '2018-03-01'
CUSTO_LADO = 0.0005  # futuros da Binance (taker)
SAIDA = Path(__file__).parent / 'saida'


def buy_and_hold(df):
    eq = pd.Series((df['close'] / df['open'].iloc[0]).to_numpy(), index=df['time'])
    anos = (eq.index[-1] - eq.index[0]).days / 365.25
    return {'retorno_total': eq.iloc[-1] - 1, 'retorno_anual': eq.iloc[-1] ** (1 / anos) - 1,
            'dd_max': m.drawdown_max(eq)}


def retorno_periodo(eq, ini, fim):
    p = eq[(eq.index >= ini) & (eq.index < fim)]
    return p.iloc[-1] / p.iloc[0] - 1


def main(simbolo='BTCUSDT', timeframe='1h'):
    df = pd.read_pickle(Path(__file__).parent / 'cache' / f'{simbolo}_{timeframe}.pkl')
    df = df[df['time'] >= INICIO].reset_index(drop=True)
    SAIDA.mkdir(exist_ok=True)

    linhas = []
    for media in MEDIAS:
        for k in KS:
            s = est.calcular_sinais(df, media, k)
            t = m.extrair_trades(s, CUSTO_LADO)
            eq = m.curva_capital(s, t, CUSTO_LADO)
            r = m.resumo(t, eq)
            r.update({'media': media, 'k': k,
                      'ret_2018_2021': retorno_periodo(eq, '2018-03-01', '2022-01-01'),
                      'ret_2022_2026': retorno_periodo(eq, '2022-01-01', '2100-01-01')})
            for d in ['COMPRA', 'VENDA']:
                td = t[(t['direcao'] == d) & ~t['aberto']]
                r[f'ret_{d.lower()}s'] = (1 + td['retorno']).prod() - 1
                r[f'acerto_{d.lower()}s'] = (td['retorno'] > 0).mean()
            linhas.append(r)

    res = pd.DataFrame(linhas)
    res.to_csv(SAIDA / f'grade_{simbolo}_{timeframe}.csv', index=False)
    bh = buy_and_hold(df)
    return res, bh


if __name__ == '__main__':
    res, bh = main(*sys.argv[1:3])
    pd.set_option('display.width', 250)
    pct = lambda x: f'{x:+.0%}'
    print('Buy & hold:', {k: pct(v) for k, v in bh.items()})
    print(res[['media', 'k', 'retorno_total', 'retorno_anual', 'dd_max', 'trades', 'acerto', 'profit_factor',
               'duracao_media_h', 'ret_2018_2021', 'ret_2022_2026', 'ret_compras', 'ret_vendas']].to_string(
        index=False, formatters={c: pct for c in ['retorno_total', 'retorno_anual', 'dd_max', 'acerto',
                                                  'ret_2018_2021', 'ret_2022_2026', 'ret_compras', 'ret_vendas']}
        | {'profit_factor': '{:.2f}'.format, 'duracao_media_h': '{:.0f}'.format}))
    print()
    print(res[['media', 'k', 'acerto_1r', 'acerto_2r', 'acerto_3r', 'resultado_medio_r', 'risco_mediano', 'mfe_mediano',
               'mae_mediano']].to_string(index=False, formatters={c: '{:.0%}'.format for c in
                                                                  ['acerto_1r', 'acerto_2r', 'acerto_3r']}
                                         | {'resultado_medio_r': '{:+.2f}R'.format}
                                         | {c: '{:.2%}'.format for c in ['risco_mediano', 'mfe_mediano', 'mae_mediano']}))

````

### `backtest/exportar_visualizador.py`

SHA-256: `6eda94cb90c3fd02d45ff89745a8f0431589b201a1a9172db46ac1394ee85ae7`

````python
"""
Exporta os dados do visualizador de trades: um JSON por ativo, com candles, as 12 combinações
e os trades de cada modo de saída. Os sinais (entradas) são os mesmos em todos os modos;
só a saída muda.

Uso: python exportar_visualizador.py 1h BTCUSDT ETHUSDT SOLUSDT ADAUSDT ETHBTC
"""

import json
import sys
from pathlib import Path

import pandas as pd

import estrategia as est
import motor as m
from rodar_grade import CUSTO_LADO, INICIO, KS, MEDIAS, SAIDA, buy_and_hold

MODOS = {
    'virada': ('Virada do sinal', {'saida': 'virada'}),
    'stop_movel': ('Stop móvel', {'saida': 'stop_movel'}),
    'alvo1': ('Alvo 1R', {'saida': 'alvo', 'alvo_r': 1}),
    'alvo2': ('Alvo 2R', {'saida': 'alvo', 'alvo_r': 2}),
    'alvo3': ('Alvo 3R', {'saida': 'alvo', 'alvo_r': 3}),
}
MOTIVOS = ['virada', 'em aberto', 'stop móvel', 'stop', 'alvo 1R', 'alvo 2R', 'alvo 3R']
CAMPOS_RESUMO = ['retorno_total', 'retorno_anual', 'dd_max', 'trades', 'acerto', 'profit_factor',
                 'duracao_media_h', 'resultado_medio_r', 'acerto_1r', 'acerto_2r', 'acerto_3r']


def _num(v):
    return None if pd.isna(v) or v in (float('inf'), float('-inf')) else round(float(v), 5)


def exportar(simbolo, timeframe):
    df = pd.read_pickle(Path(__file__).parent / 'cache' / f'{simbolo}_{timeframe}.pkl')
    df = df[df['time'] >= INICIO].reset_index(drop=True)
    casas = 2 if df['close'].median() > 10 else 6
    candles = [[int(r.open_time // 1000), round(r.open, casas), round(r.high, casas), round(r.low, casas),
                round(r.close, casas)] for r in df.itertuples()]

    combos = {}
    for mm in MEDIAS:
        for k in KS:
            s = est.calcular_sinais(df, mm, k)
            base = None
            saidas, resumos = {}, {}
            for chave, (_, kw) in MODOS.items():
                t = m.extrair_trades(s, CUSTO_LADO, **kw)
                r = m.resumo(t, m.curva_capital(s, t, CUSTO_LADO))
                fech = t[~t['aberto']]
                r['ret_compras'] = (1 + fech.loc[fech['dir'] == 1, 'retorno']).prod() - 1
                r['ret_vendas'] = (1 + fech.loc[fech['dir'] == -1, 'retorno']).prod() - 1
                resumos[chave] = {c: _num(r[c]) for c in CAMPOS_RESUMO + ['ret_compras', 'ret_vendas']}
                # s, preço de saída, retorno líquido, mfe_r, mae_r, motivo, aberto
                saidas[chave] = [[int(x.i_saida), round(x.preco_saida, casas), round(x.retorno, 5),
                                  round(x.mfe_r, 2), round(x.mae_r, 2), MOTIVOS.index(x.motivo), int(x.aberto)]
                                 for x in t.itertuples()]
                if base is None:
                    # e, dir, entrada, stop inicial, acertou 1R, 2R, 3R antes do stop
                    base = [[int(x.i_entrada), int(x.dir), round(x.preco_entrada, casas),
                             round(x.stop_inicial, casas), int(x.acerto_1r), int(x.acerto_2r), int(x.acerto_3r)]
                            for x in t.itertuples()]
            combos[f'{mm}_{k}'] = {'media': mm, 'k': k, 'sinais': base, 'saidas': saidas, 'resumo': resumos}

    dados = {'simbolo': simbolo, 'timeframe': timeframe, 'custo_lado': CUSTO_LADO, 'casas': casas,
             'modos': {c: v[0] for c, v in MODOS.items()}, 'motivos': MOTIVOS,
             'buy_hold': {k: float(v) for k, v in buy_and_hold(df).items()},
             'candles': candles, 'combos': combos}
    destino = SAIDA / 'visualizador' / f'{simbolo}_{timeframe}.json'
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(dados, separators=(',', ':')))
    return destino


if __name__ == '__main__':
    tf = sys.argv[1]
    for ativo in sys.argv[2:]:
        d = exportar(ativo, tf)
        print(f'{d}  {d.stat().st_size / 1e6:.1f} MB')

````

### `backtest/visualizador/index.html`

SHA-256: `ec49baee9ee83237358c0330423e54fcfdee543b1fc02aac2f59861f390d90dc`

````html
<title>Ovelha V3 Trades</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&display=swap">
<style>
/* Layout: mesa de operação — barra de controles, faixa de métricas, gráfico grande e ficha do trade ao lado (empilha no celular) */
:root {
  --bg: #f6f7f9;
  --surface: #ffffff;
  --ink: #111827;
  --ink-2: #4b5563;
  --ink-3: #8a93a3;
  --line: #e3e6eb;
  --compra: #2563eb;
  --venda: #dc2626;
  --alvo: #15803d;
  --stop: #111827;
  --ganho: #15803d;
  --perda: #dc2626;
  --font-ui: "IBM Plex Sans", system-ui, -apple-system, "Segoe UI", sans-serif;
  --font-num: "IBM Plex Mono", ui-monospace, "SFMono-Regular", Menlo, monospace;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #0f1218; --surface: #161a22; --ink: #e8ebf0; --ink-2: #b0b7c3; --ink-3: #7b8494; --line: #262c37;
    --compra: #5b8def; --venda: #f05252; --alvo: #22b8a6; --stop: #e8ebf0; --ganho: #22b8a6; --perda: #f05252;
    color-scheme: dark;
  }
}
:root[data-theme="dark"] {
  --bg: #0f1218; --surface: #161a22; --ink: #e8ebf0; --ink-2: #b0b7c3; --ink-3: #7b8494; --line: #262c37;
  --compra: #5b8def; --venda: #f05252; --alvo: #22b8a6; --stop: #e8ebf0; --ganho: #22b8a6; --perda: #f05252;
  color-scheme: dark;
}
* { box-sizing: border-box; }
[hidden] { display: none !important; }
body {
  background: var(--bg); color: var(--ink); font-family: var(--font-ui); font-size: 14px;
  padding-left: max(16px, env(safe-area-inset-left, 0px));
  padding-right: max(16px, env(safe-area-inset-right, 0px));
  padding-block: 16px 32px;
}
.wrap { max-width: 1400px; margin: 0 auto; display: grid; gap: 14px; }
header { display: flex; flex-wrap: wrap; align-items: baseline; gap: 6px 14px; }
h1 { font-size: 20px; font-weight: 600; margin: 0; letter-spacing: -0.01em; }
.sub { color: var(--ink-2); font-size: 13px; }
.num { font-family: var(--font-num); font-variant-numeric: tabular-nums; }

.controles { display: flex; flex-wrap: wrap; gap: 10px 22px; align-items: center; }
.grupo { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.rotulo { font-size: 11px; text-transform: uppercase; letter-spacing: 0.08em; color: var(--ink-3); }
.seg { display: inline-flex; flex-wrap: wrap; border: 1px solid var(--line); border-radius: 6px; overflow: hidden; background: var(--surface); }
.seg button {
  border: 0; background: transparent; color: var(--ink-2); font: inherit; font-family: var(--font-num);
  padding: 6px 11px; cursor: pointer; border-right: 1px solid var(--line);
}
.seg button:last-child { border-right: 0; }
.seg button[aria-pressed="true"] { background: var(--ink); color: var(--surface); }
.seg.texto button { font-family: var(--font-ui); }
button:focus-visible, select:focus-visible, input:focus-visible { outline: 2px solid var(--compra); outline-offset: 2px; }

.metricas {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  background: var(--surface); border: 1px solid var(--line); border-radius: 8px;
}
.metrica { padding: 10px 14px; border-right: 1px solid var(--line); border-bottom: 1px solid var(--line); min-width: 0; margin: 0 -1px -1px 0; }
.metrica .v { font-family: var(--font-num); font-size: 17px; font-weight: 500; margin-top: 3px; }
.metrica .c { font-size: 11.5px; color: var(--ink-3); margin-top: 2px; }
.metrica.destaque { background: color-mix(in srgb, var(--alvo) 7%, var(--surface)); }

.principal { display: grid; grid-template-columns: minmax(0, 1fr) 320px; gap: 14px; }
@media (max-width: 900px) { .principal { grid-template-columns: minmax(0, 1fr); } }
.painel { background: var(--surface); border: 1px solid var(--line); border-radius: 8px; min-width: 0; }
#grafico { height: min(62vh, 560px); min-height: 340px; position: relative; }
.legenda { display: flex; flex-wrap: wrap; gap: 6px 16px; padding: 10px 14px; border-top: 1px solid var(--line); font-size: 12px; color: var(--ink-2); }
.legenda span { display: inline-flex; align-items: center; gap: 6px; }
.tra { width: 18px; border-top: 2px dashed currentColor; display: inline-block; }
.sol { width: 18px; border-top: 2px solid currentColor; display: inline-block; }
.pon { width: 18px; border-top: 2px dotted currentColor; display: inline-block; }

.ficha { padding: 14px; display: grid; gap: 14px; align-content: start; }
.nav { display: grid; grid-template-columns: auto 1fr auto; gap: 8px; align-items: center; }
.nav button {
  font: inherit; border: 1px solid var(--line); background: var(--surface); color: var(--ink);
  border-radius: 6px; padding: 7px 12px; cursor: pointer;
}
.nav button:hover { border-color: var(--ink-3); }
.nav .pos { text-align: center; font-family: var(--font-num); font-size: 13px; color: var(--ink-2); }
.filtros { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
select, input[type="date"] {
  font: inherit; font-size: 13px; color: var(--ink); background: var(--surface);
  border: 1px solid var(--line); border-radius: 6px; padding: 6px 8px;
}
.pill { display: inline-block; font-size: 12px; font-weight: 600; letter-spacing: 0.06em; padding: 3px 9px; border-radius: 4px; color: #fff; }
.pill.compra { background: var(--compra); }
.pill.venda { background: var(--venda); }
.pill.neutra { background: transparent; color: var(--ink-2); border: 1px solid var(--line); font-weight: 500; letter-spacing: 0.02em; }
.cab { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.resultado { font-family: var(--font-num); font-size: 26px; font-weight: 500; }
.pos-v { color: var(--ganho); } .neg-v { color: var(--perda); }
dl { margin: 0; display: grid; grid-template-columns: auto 1fr; gap: 6px 12px; font-size: 13px; }
dt { color: var(--ink-3); }
dd { margin: 0; text-align: right; font-family: var(--font-num); font-variant-numeric: tabular-nums; }
.sep { border-top: 1px solid var(--line); }
.chips { display: flex; gap: 6px; }
.chip { font-family: var(--font-num); font-size: 12px; padding: 3px 8px; border-radius: 4px; border: 1px solid var(--line); color: var(--ink-3); }
.chip.sim { border-color: var(--ganho); color: var(--ganho); }
.chip.nao { border-color: var(--line); color: var(--ink-3); text-decoration: line-through; }
.ultimos { display: flex; gap: 4px; flex-wrap: wrap; }
.ultimos button {
  width: 26px; height: 26px; border-radius: 4px; border: 1px solid var(--line); cursor: pointer;
  font-family: var(--font-num); font-size: 11px; background: var(--surface); color: var(--ink-2);
}
.ultimos button.g { border-color: var(--ganho); color: var(--ganho); }
.ultimos button.p { border-color: var(--perda); color: var(--perda); }
.ultimos button[aria-current="true"] { background: var(--ink); color: var(--surface); border-color: var(--ink); }
.nota { font-size: 12px; color: var(--ink-3); line-height: 1.5; max-width: 90ch; margin: 0; }
.aviso { position: absolute; inset: 0; display: grid; place-items: center; color: var(--ink-2); background: var(--surface); z-index: 5; }
</style>

<div class="wrap">
  <header>
    <h1>Ovelha V3 · <span id="ativo">BTCUSDT H1</span></h1>
    <span class="sub">Média + faixa de ATR com histerese · execução na abertura do candle seguinte · custo <span id="custo">0,05%</span> por lado</span>
  </header>

  <div class="controles">
    <div class="grupo"><span class="rotulo">Ativo</span><div class="seg" id="seg-ativo"></div></div>
    <div class="grupo"><span class="rotulo">Saída</span><div class="seg texto" id="seg-modo"></div></div>
    <div class="grupo"><span class="rotulo">Média</span><div class="seg" id="seg-media"></div></div>
    <div class="grupo"><span class="rotulo">k (largura da faixa)</span><div class="seg" id="seg-k"></div></div>
  </div>

  <div class="metricas" id="metricas"></div>

  <div class="principal">
    <div class="painel">
      <div id="grafico"><div class="aviso" id="aviso">Carregando candles…</div></div>
      <div class="legenda">
        <span style="color:var(--compra)"><span class="tra"></span>Entrada compra</span>
        <span style="color:var(--venda)"><span class="tra"></span>Entrada venda</span>
        <span style="color:var(--stop)"><span class="tra"></span>Stop inicial</span>
        <span style="color:var(--stop)" id="leg-movel"><span class="sol"></span>Stop móvel</span>
        <span style="color:var(--alvo)"><span class="tra"></span>1R · 2R · 3R</span>
        <span style="color:var(--ink-3)"><span class="sol"></span>Média</span>
        <span style="color:var(--ink-3)"><span class="pon"></span>Faixas ± k·ATR</span>
      </div>
    </div>

    <aside class="painel ficha" aria-live="polite">
      <div class="nav">
        <button id="ant" aria-label="Trade anterior">←</button>
        <div class="pos" id="posicao">–</div>
        <button id="prox" aria-label="Próximo trade">→</button>
      </div>
      <div class="filtros">
        <select id="filtro" aria-label="Filtrar trades">
          <option value="todos">Todos os trades</option>
          <option value="compras">Só compras</option>
          <option value="vendas">Só vendas</option>
          <option value="ganhos">Só ganhos</option>
          <option value="perdas">Só perdas</option>
        </select>
        <input type="date" id="data" aria-label="Ir para a data">
      </div>
      <div class="cab" id="cab"></div>
      <div class="resultado" id="resultado"></div>
      <div>
        <div class="rotulo" style="margin-bottom:6px">Chegou antes do stop inicial</div>
        <div class="chips" id="chips"></div>
      </div>
      <dl id="detalhes"></dl>
      <div class="sep"></div>
      <div>
        <div class="rotulo" style="margin-bottom:6px">Últimos 10 trades fechados</div>
        <div class="ultimos" id="ultimos"></div>
        <p class="nota" id="ultimos-resumo" style="margin-top:6px"></p>
      </div>
    </aside>
  </div>

  <p class="nota" id="nota-modo"></p>
  <p class="nota">
    R é a distância entre a entrada e o stop inicial (a faixa oposta no candle do sinal). "Chegou a XR antes do stop" usa máximas e mínimas
    dos candles, só dentro da vida do sinal, e conta como não quando alvo e stop são tocados no mesmo candle. A referência "aleatório" usa entradas
    sorteadas com o mesmo risco, direção e janela de tempo: é o número a vencer. Use ← e → no teclado para navegar.
  </p>
</div>

<script src="https://cdn.jsdelivr.net/npm/lightweight-charts@4.2.0/dist/lightweight-charts.standalone.production.js"></script>
<script>
(async function () {
  const LC = LightweightCharts;
  const ATIVOS = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'ADAUSDT', 'ETHBTC'];
  const TF = '1h';
  // acerto de entradas aleatórias com o mesmo risco, direção e janela do sinal (mediana das 12 combinações; experimento_saidas.py)
  const ALEATORIO = {"BTCUSDT": [0.378, 0.201, 0.117], "ETHUSDT": [0.386, 0.207, 0.124], "SOLUSDT": [0.382, 0.203, 0.125], "ADAUSDT": [0.394, 0.211, 0.128], "ETHBTC": [0.382, 0.206, 0.127]};
  const NOTAS_MODO = {
    virada: 'Saída na virada do sinal: a estratégia fica sempre posicionada e só troca de lado quando o preço fecha além da faixa oposta.',
    stop_movel: 'Stop móvel: o stop começa na faixa oposta e só anda a favor (sobe na compra, desce na venda). Se for tocado, a estratégia fica fora até a próxima virada do sinal.',
    alvo1: 'Alvo 1R: sai no alvo de 1R ou no stop inicial, o que vier primeiro. Se nenhum for tocado, sai na virada do sinal.',
    alvo2: 'Alvo 2R: sai no alvo de 2R ou no stop inicial, o que vier primeiro. Se nenhum for tocado, sai na virada do sinal.',
    alvo3: 'Alvo 3R: sai no alvo de 3R ou no stop inicial, o que vier primeiro. Se nenhum for tocado, sai na virada do sinal.',
  };
  const cache = {};
  const estado = { ativo: 'BTCUSDT', modo: 'virada', media: 100, k: 1, dados: null, combo: null, trades: [], lista: [], pos: 0 };
  let C = [], n = 0, atr = [], media = [], casas = 2;

  const nf = (d) => ({ minimumFractionDigits: d, maximumFractionDigits: d });
  const pct = (x, d = 0) => x == null ? '–' : (x >= 0 ? '+' : '') + (x * 100).toLocaleString('pt-BR', nf(d)) + '%';
  const pctSem = (x, d = 0) => x == null ? '–' : (x * 100).toLocaleString('pt-BR', nf(d)) + '%';
  const preco = x => x.toLocaleString('pt-BR', nf(casas));
  const rr = x => x == null ? '–' : (x >= 0 ? '+' : '') + x.toLocaleString('pt-BR', nf(2)) + 'R';
  const dataHora = t => new Date(t * 1000).toLocaleString('pt-BR', { timeZone: 'UTC', day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' }) + ' UTC';
  const cor = nome => getComputedStyle(document.documentElement).getPropertyValue(nome).trim();
  const aviso = document.getElementById('aviso');

  // ---------- gráfico ----------
  const chart = LC.createChart(document.getElementById('grafico'), {
    autoSize: true,
    timeScale: { timeVisible: true, secondsVisible: false, rightOffset: 12 },
    crosshair: { mode: LC.CrosshairMode.Normal },
    localization: { locale: 'pt-BR', priceFormatter: p => preco(p) },
  });
  const semRotulo = { priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false };
  const velas = chart.addCandlestickSeries({ priceLineVisible: false, lastValueVisible: false });
  const linhaMedia = chart.addLineSeries({ lineWidth: 1.5, ...semRotulo });
  const faixaSup = chart.addLineSeries({ lineWidth: 1, lineStyle: LC.LineStyle.Dotted, ...semRotulo });
  const faixaInf = chart.addLineSeries({ lineWidth: 1, lineStyle: LC.LineStyle.Dotted, ...semRotulo });
  const stopMovel = chart.addLineSeries({ title: 'Stop móvel', lineWidth: 2, lineType: LC.LineType.WithSteps, priceLineVisible: false, lastValueVisible: true, crosshairMarkerVisible: false });
  const niveis = ['Entrada', 'Stop', '1R', '2R', '3R'].map(titulo => chart.addLineSeries({
    title: titulo, lineStyle: LC.LineStyle.Dashed, priceLineVisible: false, lastValueVisible: true, crosshairMarkerVisible: false,
  }));

  function aplicarTema() {
    const ink2 = cor('--ink-2'), ink3 = cor('--ink-3'), line = cor('--line'), surf = cor('--surface');
    chart.applyOptions({
      layout: { background: { type: 'solid', color: surf }, textColor: ink2, fontFamily: 'IBM Plex Mono, ui-monospace, monospace', fontSize: 11 },
      grid: { vertLines: { color: line }, horzLines: { color: line } },
      rightPriceScale: { borderColor: line }, timeScale: { borderColor: line },
    });
    velas.applyOptions({ upColor: surf, downColor: ink3, borderUpColor: ink3, borderDownColor: ink3, wickUpColor: ink3, wickDownColor: ink3 });
    linhaMedia.applyOptions({ color: ink2 });
    faixaSup.applyOptions({ color: ink3 });
    faixaInf.applyOptions({ color: ink3 });
    stopMovel.applyOptions({ color: cor('--stop') });
    niveis[1].applyOptions({ color: cor('--stop'), lineWidth: 1 });
    niveis[2].applyOptions({ color: cor('--alvo'), lineWidth: 2 });
    niveis[3].applyOptions({ color: cor('--alvo'), lineWidth: 1 });
    niveis[4].applyOptions({ color: cor('--alvo'), lineWidth: 1 });
    if (estado.combo) { desenharMarcadores(); mostrarTrade(); }
  }

  // ---------- indicadores (mesmas fórmulas do Python) ----------
  function calcularAtr() {
    const tr = C.map((c, i) => i === 0 ? c[2] - c[3] : Math.max(c[2] - c[3], Math.abs(c[2] - C[i - 1][4]), Math.abs(c[3] - C[i - 1][4])));
    const out = new Array(n).fill(NaN); let soma = 0;
    for (let i = 0; i < n; i++) { soma += tr[i]; if (i >= 14) soma -= tr[i - 14]; if (i >= 13) out[i] = soma / 14; }
    return out;
  }
  function sma(p) {
    const out = new Array(n).fill(NaN); let soma = 0;
    for (let i = 0; i < n; i++) { soma += C[i][4]; if (i >= p) soma -= C[i - p][4]; if (i >= p - 1) out[i] = soma / p; }
    return out;
  }
  const serie = arr => arr.map((v, i) => Number.isNaN(v) ? { time: C[i][0] } : { time: C[i][0], value: v });
  const faixa = (i, lado) => media[i] + lado * estado.k * atr[i];

  // ---------- controles segmentados ----------
  function botoesSeg(id, valores, chave, fmt, aoMudar) {
    const box = document.getElementById(id);
    box.innerHTML = '';
    valores.forEach(v => {
      const b = document.createElement('button');
      b.textContent = fmt(v);
      b.setAttribute('aria-pressed', String(estado[chave] === v));
      b.onclick = () => { estado[chave] = v; botoesSeg(id, valores, chave, fmt, aoMudar); aoMudar(); };
      box.appendChild(b);
    });
  }

  async function carregarAtivo() {
    aviso.hidden = false;
    aviso.textContent = `Carregando ${estado.ativo}…`;
    if (!cache[estado.ativo]) cache[estado.ativo] = await (await fetch(`dados/${estado.ativo}_${TF}.json`)).json();
    const d = estado.dados = cache[estado.ativo];
    C = d.candles; n = C.length; casas = d.casas;
    chart.applyOptions({ localization: { locale: 'pt-BR', priceFormatter: p => preco(p) } });
    velas.applyOptions({ priceFormat: { type: 'price', precision: casas, minMove: 1 / 10 ** casas } });
    velas.setData(C.map(c => ({ time: c[0], open: c[1], high: c[2], low: c[3], close: c[4] })));
    atr = calcularAtr();
    document.getElementById('ativo').textContent = `${d.simbolo} ${d.timeframe.toUpperCase()}`;
    document.getElementById('custo').textContent = (d.custo_lado * 100).toLocaleString('pt-BR') + '%';
    const campo = document.getElementById('data');
    campo.min = new Date(C[0][0] * 1000).toISOString().slice(0, 10);
    campo.max = new Date(C[n - 1][0] * 1000).toISOString().slice(0, 10);
    aviso.hidden = true;
    carregarCombo(true, true);
  }

  // trade combinado: sinal (entrada) + saída do modo escolhido
  function montarTrades() {
    const cb = estado.combo, sd = cb.saidas[estado.modo];
    return cb.sinais.map((g, i) => {
      const [e, dir, entrada, stop, a1, a2, a3] = g;
      const [s, saida, ret, mfe, mae, motivo, aberto] = sd[i];
      const risco = dir * (entrada - stop);
      return { i, e, dir, entrada, stop, risco, acertos: [a1, a2, a3], s, saida, ret, mfe, mae,
               retR: dir * (saida - entrada) / risco, motivo: estado.dados.motivos[motivo], aberto: !!aberto };
    });
  }

  function carregarCombo(manterData, novoAtivo) {
    const tAnterior = estado.trades.length && estado.lista.length ? C[Math.min(estado.trades[estado.lista[estado.pos]].e, n - 1)][0] : null;
    const d = estado.dados;
    estado.combo = d.combos[`${estado.media}_${estado.k.toFixed(1)}`];
    estado.trades = montarTrades();
    media = sma(estado.media);
    linhaMedia.setData(serie(media));
    faixaSup.setData(serie(media.map((v, i) => v + estado.k * atr[i])));
    faixaInf.setData(serie(media.map((v, i) => v - estado.k * atr[i])));
    filtrar();
    estado.pos = estado.lista.length - 1;
    if (manterData && tAnterior != null && !novoAtivo) irPara(tAnterior, false);
    document.getElementById('leg-movel').hidden = estado.modo !== 'stop_movel';
    document.getElementById('nota-modo').textContent = NOTAS_MODO[estado.modo];
    metricas();
    ultimos();
    desenharMarcadores();
    mostrarTrade();
  }

  function metricas() {
    const r = estado.combo.resumo[estado.modo], bh = estado.dados.buy_hold;
    const itens = [
      ['Retorno total', pct(r.retorno_total), `buy & hold ${pct(bh.retorno_total)}`, r.retorno_total, ''],
      ['Retorno anual', pct(r.retorno_anual), `buy & hold ${pct(bh.retorno_anual)}`, r.retorno_anual, ''],
      ['Drawdown máx.', pct(r.dd_max), `buy & hold ${pct(bh.dd_max)}`, null, ''],
      ['Acerto antes do stop', `${pctSem(r.acerto_1r)} · ${pctSem(r.acerto_2r)} · ${pctSem(r.acerto_3r)}`, `1R · 2R · 3R · aleatório ${ALEATORIO[estado.ativo].map(x => Math.round(x * 100)).join(' · ')}%`, null, 'destaque'],
      ['Trades', r.trades.toLocaleString('pt-BR'), `duração média ${Math.round(r.duracao_media_h)} h`, null, ''],
      ['Trades com lucro', pctSem(r.acerto), `profit factor ${r.profit_factor == null ? '–' : r.profit_factor.toFixed(2).replace('.', ',')}`, null, ''],
      ['Resultado médio', rr(r.resultado_medio_r), 'por trade, antes dos custos', r.resultado_medio_r, ''],
      ['Compras · vendas', `${pct(r.ret_compras)} · ${pct(r.ret_vendas)}`, 'retorno acumulado de cada lado', null, ''],
    ];
    document.getElementById('metricas').innerHTML = itens.map(([t, v, c, s, cls]) =>
      `<div class="metrica ${cls}"><div class="rotulo">${t}</div><div class="v ${s == null ? '' : s >= 0 ? 'pos-v' : 'neg-v'}">${v}</div><div class="c">${c}</div></div>`).join('');
  }

  function desenharMarcadores() {
    const atual = estado.lista[estado.pos];
    const corCompra = cor('--compra'), corVenda = cor('--venda');
    const mk = estado.trades.map(t => ({
      time: C[t.e][0], position: t.dir === 1 ? 'belowBar' : 'aboveBar', color: t.dir === 1 ? corCompra : corVenda,
      shape: t.dir === 1 ? 'arrowUp' : 'arrowDown', size: t.i === atual ? 2 : 1,
    }));
    if (atual != null) {
      const t = estado.trades[atual];
      mk.push({ time: C[t.s][0], position: t.dir === 1 ? 'aboveBar' : 'belowBar', color: cor('--ink'), shape: 'circle', text: t.aberto ? 'agora' : 'saída' });
    }
    mk.sort((a, b) => a.time - b.time);
    velas.setMarkers(mk);
  }

  function filtrar() {
    const f = document.getElementById('filtro').value;
    estado.lista = estado.trades.filter(t =>
      f === 'todos' || (f === 'compras' && t.dir === 1) || (f === 'vendas' && t.dir === -1)
      || (f === 'ganhos' && t.ret > 0) || (f === 'perdas' && t.ret <= 0)).map(t => t.i);
  }

  function irPara(tempo, redesenhar = true) {
    let melhor = 0;
    estado.lista.forEach((idx, p) => { if (C[estado.trades[idx].e][0] <= tempo) melhor = p; });
    estado.pos = melhor;
    if (redesenhar) { desenharMarcadores(); mostrarTrade(); }
  }

  function mostrarTrade() {
    const vazio = !estado.lista.length;
    if (vazio) {
      niveis.forEach(s => s.setData([])); stopMovel.setData([]);
      document.getElementById('posicao').textContent = 'nenhum trade';
      ['cab', 'resultado', 'detalhes', 'chips'].forEach(id => document.getElementById(id).innerHTML = '');
      return;
    }
    const t = estado.trades[estado.lista[estado.pos]];
    const valores = [t.entrada, t.stop, t.entrada + t.dir * t.risco, t.entrada + 2 * t.dir * t.risco, t.entrada + 3 * t.dir * t.risco];
    const t0 = C[t.e][0], t1 = C[Math.max(t.s, t.e)][0];
    niveis[0].applyOptions({ color: cor(t.dir === 1 ? '--compra' : '--venda'), lineWidth: 2 });
    niveis.forEach((sr, i) => sr.setData(t1 > t0 ? [{ time: t0, value: valores[i] }, { time: t1, value: valores[i] }] : [{ time: t0, value: valores[i] }]));

    // stop móvel: nível vigente em cada candle = melhor entre o stop inicial e as faixas opostas já fechadas
    if (estado.modo === 'stop_movel') {
      const pts = []; let nivel = t.stop;
      for (let i = t.e; i <= Math.max(t.s, t.e); i++) {
        if (i > t.e) { const f = faixa(i - 1, -t.dir); if (!Number.isNaN(f)) nivel = t.dir === 1 ? Math.max(nivel, f) : Math.min(nivel, f); }
        pts.push({ time: C[i][0], value: nivel });
      }
      stopMovel.setData(pts);
    } else stopMovel.setData([]);

    chart.timeScale().setVisibleLogicalRange({ from: Math.max(t.e - 40, 0), to: Math.min(t.s + 15, n - 1) + 6 });

    document.getElementById('posicao').textContent = `trade ${(t.i + 1).toLocaleString('pt-BR')} de ${estado.trades.length.toLocaleString('pt-BR')}`
      + (estado.lista.length !== estado.trades.length ? ` · ${estado.pos + 1}/${estado.lista.length} no filtro` : '');
    document.getElementById('cab').innerHTML =
      `<span class="pill ${t.dir === 1 ? 'compra' : 'venda'}">${t.dir === 1 ? 'COMPRA' : 'VENDA'}</span>` +
      `<span class="pill neutra">${t.aberto ? 'em aberto' : 'saída: ' + t.motivo}</span>` +
      `<span class="sub num">${dataHora(t0)}</span>`;
    document.getElementById('resultado').innerHTML =
      `<span class="${t.ret >= 0 ? 'pos-v' : 'neg-v'}">${pct(t.ret, 2)}</span> <span class="sub num">${rr(t.retR)}</span>`;
    document.getElementById('chips').innerHTML = t.acertos.map((a, i) =>
      `<span class="chip ${a ? 'sim' : 'nao'}" aria-label="${i + 1}R ${a ? 'atingido' : 'não atingido'} antes do stop">${i + 1}R ${a ? '✓' : '✗'}</span>`).join('');
    const linhas = [
      ['Entrada', preco(t.entrada)],
      ['Stop inicial', preco(t.stop)],
      ['R (risco)', `${preco(t.risco)} · ${pctSem(t.risco / t.entrada, 2)}`],
      ['1R · 2R · 3R', `${preco(valores[2])}`], ['', preco(valores[3])], ['', preco(valores[4])],
      [t.aberto ? 'Preço atual' : 'Saída', preco(t.saida)],
      ['Duração', `${t.s - t.e} candles`],
      ['Máx. a favor', rr(t.mfe)],
      ['Máx. contra', rr(t.mae)],
    ];
    document.getElementById('detalhes').innerHTML = linhas.map(([a, b]) => `<dt>${a}</dt><dd>${b}</dd>`).join('');
    document.querySelectorAll('#ultimos button').forEach(b => b.setAttribute('aria-current', String(Number(b.dataset.i) === t.i)));
  }

  function ultimos() {
    const fechados = estado.trades.filter(t => !t.aberto).slice(-10);
    const box = document.getElementById('ultimos');
    box.innerHTML = '';
    fechados.forEach(t => {
      const b = document.createElement('button');
      b.className = t.ret > 0 ? 'g' : 'p';
      b.textContent = t.dir === 1 ? 'C' : 'V';
      b.dataset.i = t.i;
      b.title = `${t.dir === 1 ? 'Compra' : 'Venda'} ${dataHora(C[t.e][0])} · ${pct(t.ret, 2)}`;
      b.setAttribute('aria-label', b.title);
      b.onclick = () => { document.getElementById('filtro').value = 'todos'; filtrar(); estado.pos = estado.lista.indexOf(t.i); desenharMarcadores(); mostrarTrade(); };
      box.appendChild(b);
    });
    const pos = fechados.filter(t => t.ret > 0).length;
    const a1 = fechados.filter(t => t.acertos[0]).length;
    const soma = fechados.reduce((a, t) => a * (1 + t.ret), 1) - 1;
    document.getElementById('ultimos-resumo').textContent =
      `${pos} de ${fechados.length} com lucro · ${a1} chegaram a 1R antes do stop · resultado somado ${pct(soma, 1)}. C = compra, V = venda; borda verde = ganho, vermelha = perda.`;
  }

  // ---------- eventos ----------
  const mover = d => { if (!estado.lista.length) return; estado.pos = Math.min(Math.max(estado.pos + d, 0), estado.lista.length - 1); desenharMarcadores(); mostrarTrade(); };
  document.getElementById('ant').onclick = () => mover(-1);
  document.getElementById('prox').onclick = () => mover(1);
  document.addEventListener('keydown', ev => {
    if (ev.target.matches('input, select')) return;
    if (ev.key === 'ArrowLeft') mover(-1);
    if (ev.key === 'ArrowRight') mover(1);
  });
  document.getElementById('filtro').onchange = () => {
    const atual = estado.trades[estado.lista[estado.pos]];
    const tempo = atual ? C[atual.e][0] : C[n - 1][0];
    filtrar(); estado.pos = Math.max(estado.lista.length - 1, 0); irPara(tempo);
  };
  const campoData = document.getElementById('data');
  campoData.onchange = () => { if (campoData.value) irPara(Date.parse(campoData.value + 'T23:59:59Z') / 1000); };

  const NOMES_MODO = { virada: 'Virada', stop_movel: 'Stop móvel', alvo1: 'Alvo 1R', alvo2: 'Alvo 2R', alvo3: 'Alvo 3R' };
  botoesSeg('seg-ativo', ATIVOS, 'ativo', v => v.replace('USDT', ''), () => carregarAtivo().catch(falha));
  botoesSeg('seg-modo', Object.keys(NOMES_MODO), 'modo', v => NOMES_MODO[v], () => carregarCombo(true));
  botoesSeg('seg-media', [50, 100, 200], 'media', v => String(v), () => carregarCombo(true));
  botoesSeg('seg-k', [0.5, 1, 1.5, 2], 'k', v => v.toLocaleString('pt-BR', nf(1)), () => carregarCombo(true));
  aplicarTema();
  matchMedia('(prefers-color-scheme: dark)').addEventListener('change', aplicarTema);
  new MutationObserver(aplicarTema).observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
  await carregarAtivo();

  function falha(err) { aviso.hidden = false; aviso.textContent = `Não foi possível carregar os dados: ${err.message}`; }
})().catch(err => {
  const a = document.getElementById('aviso');
  a.hidden = false; a.textContent = `Não foi possível carregar os dados: ${err.message}`;
});
</script>

````
