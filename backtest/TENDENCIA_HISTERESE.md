# BTCUSDT M5 — SMA20/60 com histerese de 1,5 ATR

Estudo solicitado em 19/10/2026. Uma única configuração, sem otimização.

- Dados: Binance spot oficial de setembro/2026, SHA-256 conferido pelo coletor existente.
- Aquecimento: 01 a 23/09. Operações: 24 a 30/09/2026 UTC, fim exclusivo em 01/10.
- Médias simples de 20 e 60 fechamentos. ATR = média simples de 14 True Ranges, seguindo `estrategia.py` da Ovelha V3.
- Cada média recebe um envelope de ±1,5 ATR. Compra quando o fechamento fica acima dos dois envelopes; venda quando fica abaixo dos dois. Exigir confirmação das duas médias foi a interpretação adotada para o conjunto 20/60. Não há exigência adicional de SMA20 cruzar SMA60.
- Entre esses limites, o estado anterior é mantido. O sinal se calcula no fechamento e só executa na abertura seguinte.
- Sem posição herdada do aquecimento: aguarda a primeira mudança de estado na janela. Depois fica posicionado, fecha e reverte na virada oposta.
- **Saída exclusivamente na virada: não existe stop de preço nem alvo fixo.**
- R bruto puro, sem taxas e slippage: `direção × (abertura de saída − abertura de entrada) / (1,5 ATR do sinal de entrada)`. A unidade de R fica fixa por operação.
- A linha vermelha de −1R é referência, sem ordem. A perda pode exceder −1R e o ganho pode superar +3R. O risco até a virada não é previamente limitado por essa referência.
- Ao fim, a última posição é marcada a mercado e fica fora das métricas fechadas. O drawdown da tabela é de resultados realizados, não inclui oscilação intratrade.
- Custos da auditoria líquida são preservados separadamente e não alteram o R bruto ou os gatilhos.

## Executar e conferir

```bash
python -m unittest discover -v
python backtest/tendencia_histerese.py
node tests/check_tendencia_browser.cjs
```

Saídas: `docs/tendencia-histerese/index.html` e `index.json`. O HTML inclui biblioteca e dados, sem CDN. O gráfico mostra SMA20/60 e quatro faixas alternáveis, candles azuis/pretos, níveis de referência, zoom, arraste, estado no cursor e explicação por operação.

## Resultado desta execução

38 trades fechados e um aberto. Resultado fechado −29,585772R bruto, acerto 34,21%, fator de lucro 0,464, drawdown realizado máximo 35,957387R. Posição aberta marcada em −0,297602R, separada do resultado fechado. Esses valores correspondem apenas a uma semana e não demonstram robustez.

A nova configuração reduziu a quantidade de operações frente ao cruzamento EMA9/21, mas perdeu no período. Não se modificaram parâmetros após observar o resultado.

## Publicação

Mesmo Site e endereço fixo: https://btc-cruzamento-medias-lubra.toastypig.chatgpt.site

Projeto `appgprj_6ad5b0935e788191b2a782e02033b925`. A página inicial passa a mostrar este estudo; `/cruzamento-original/` preserva o relatório EMA9/21 anterior. Atualizar o mesmo Site nas próximas publicações, sem criar outro endereço.
