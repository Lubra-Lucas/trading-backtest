# Bitcoin M5 — EMA 9 × EMA 21

Regras definidas antes de observar resultados. Janela: **24 a 30/09/2026 UTC**, fim exclusivo em 01/10. Aquecimento: 01–23/09. O módulo novo é independente de `motor.py` e não altera os estudos anteriores.

## Executar

Da raiz do repositório:

```bash
.venv/bin/python -m unittest discover -v
.venv/bin/python backtest/cruzamento_medias.py
```

Saída padrão: `backtest/saida/cruzamento_medias/index.html`, um HTML autossuficiente, e `index.json` para auditoria. O arquivo pode ser aberto diretamente ou hospedado estaticamente. Não depende de CDN, fontes remotas ou servidor de cálculo.

O comando baixa exclusivamente o ZIP oficial de setembro/2026 e seu `.CHECKSUM` em `data.binance.vision`. Compara SHA-256 antes de usar/gravar o cache, normaliza microssegundos, exige o mês completo e rejeita buracos, duplicados, timestamps desalinhados e OHLC inválido. Faz a verificação de checksum novamente ao reutilizar o ZIP. Mantém TLS e não solicita chave de API. O download da API de candles não é necessário para esse período encerrado.

**Estado na implementação:** o proxy retornou `403 Forbidden` ao tentar obter o checksum da Binance. Nenhum resultado de mercado foi calculado. Nessa situação, o comando termina com código 2 e gera um HTML identificado como pendente, com regras e sem estatísticas ou trades. Um relatório pendente foi gravado em `/workspace/shared/downloads/btc_5m_cruzamento.html`. Os fixtures sintéticos de validação do navegador ficam apenas em `/tmp`, fora do artefato entregue.

Após aplicar as permissões de rede nas configurações do ambiente, repetir:

```bash
.venv/bin/python backtest/cruzamento_medias.py \
  --output /workspace/shared/downloads/btc_5m_cruzamento.html
```

## Execução ao vivo e simulação

1. Ao fechar cada candle M5, atualizar EMA 9, EMA 21 e ATR Wilder(14). EMA usa `adjust=False`, inicializada no primeiro fechamento do histórico; ATR inicia com a média dos primeiros 14 True Ranges e depois suaviza com alpha 1/14. Usar o mesmo histórico de aquecimento no ao vivo para paridade.
2. EMA9 anterior <= EMA21 anterior e EMA9 atual > EMA21 atual: compra. Relação inversa: venda. Não há sinal pelo simples fato de uma média estar acima da outra.
3. Executar a mercado na abertura seguinte. No ao vivo isso corresponde a enviar após confirmar o fechamento, sem presumir preenchimento exato. Uma posição por vez.
4. A partir do preenchimento efetivo, definir stop a **1,5 ATR** do candle do sinal; `1R = distância inicial entre entrada e stop`. Stop fixo durante toda a operação.
5. Ordem de alvo em **2R**, sem parciais. 1R e 3R aparecem no gráfico somente como referências.
6. Saída integral no stop, no alvo ou na abertura após cruzamento contrário. Pode reverter no cruzamento contrário. Após stop/alvo, esperar um novo cruzamento.
7. Stop e alvo passam a valer no candle da entrada. Para ambiguidade intrabar, considerar stop antes do alvo. Gaps de stop executam na abertura; alvo com gap favorável usa conservadoramente o preço do alvo. No mesmo instante de abertura, proteção em gap é processada antes da reversão pendente.
8. Taxa por preenchimento: **0,05%** do financeiro. Slippage adverso: **0,01%**, inclusive alvo (modelado como ordem acionada a mercado). Uma saída de stop pode resultar em menos de -1R líquido e um alvo em menos de +2R líquido.
9. Posição remanescente ao fim é marcada, não fechada artificialmente. Não entra em acerto, expectativa, drawdown ou soma de R dos trades fechados. Sua marcação desconta a taxa de entrada; não cobra saída inexistente.

`R líquido = [direção × (saída executada − entrada executada) − taxa × (entrada executada + saída executada)] / distância inicial de stop`.

Candles são **spot**, inclusive nas vendas simuladas. Ao vivo uma venda descoberta precisaria de margem ou derivativos; funding, empréstimo, diferenças de mercado, tamanhos mínimos, impacto variável e latência não foram modelados. A soma de R não é o retorno percentual de uma carteira; não existe promessa de preenchimento idêntico ao simulado.

## Relatório

Gráfico por operação com candles M5, EMA9/21, ponto de entrada, saída/marcação e linhas do stop/1R/2R/3R. Seleção por tabela ou botões, contexto ampliável, tooltip de OHLC, layout adaptável e tema claro/escuro. Métricas usam apenas trades fechados e o arquivo registra a fonte, o SHA-256 e o instante de geração.

## Teste de interface

Com Playwright disponível ao Node e Chromium em `/usr/bin/chromium`:

```bash
node tests/check_cruzamento_browser.cjs
```

O teste cria fixtures sintéticos em pasta temporária, identifica-os no HTML como sintéticos, verifica estado pendente, visibilidade do gráfico, entrada/saída, níveis em R, navegação, zoom, tooltip e ausência de overflow no celular; limpa os fixtures ao terminar. Não baixa dados nem mede performance do Bitcoin.

## Publicação

Nenhum endereço público de hospedagem foi configurado ou verificado. A consulta à API do GitHub também retornou bloqueio de rede; `api.github.com` foi acrescentado ao rascunho de rede, preservando os domínios Binance. A configuração salva não aplica a permissão automaticamente. Após obter dados reais, conferir o HTML e então publicar o arquivo completo em uma hospedagem estática autorizada. Não apresentar o HTML pendente como backtest executado.


## Arquivos no repositório

- `docs/cruzamento-medias/index.html`: HTML pronto para abrir, com as regras e status pendente. Não contém trades reais nesta versão.
- `backtest/cruzamento_medias.html`: template do visualizador, preenchido pelo gerador Python.
- `backtest/cruzamento_medias.py`: indicadores, simulador, coleta e geração do relatório.

Para atualizar o HTML versionado em uma sessão com acesso aos arquivos históricos da Binance:

```bash
.venv/bin/python backtest/cruzamento_medias.py --output docs/cruzamento-medias/index.html
```

O coletor deste comando usa o arquivo mensal de `data.binance.vision`, não a API `data-api.binance.vision`. Acesso apenas à API requer adaptar a coleta, mantendo as regras e a integridade do período. Um commit do HTML no repositório não habilita automaticamente GitHub Pages.

## Publicação com dados reais

Endereço fixo: https://btc-cruzamento-medias-lubra.toastypig.chatgpt.site

Hospedagem privada pelo Sites, projeto `appgprj_6ad5b0935e788191b2a782e02033b925`. Para atualizar o mesmo endereço, gerar `python backtest/cruzamento_medias.py --output docs/cruzamento-medias/index.html`, verificar e publicar uma nova versão desse mesmo projeto. Não criar outro Site para futuras atualizações.

GitHub Pages não foi habilitado: a integração devolveu HTTP 403 `Resource not accessible by integration`. A pasta `docs/` também preserva o HTML e o JSON para eventual publicação pelo Pages após habilitação com uma conta autorizada.

O gráfico usa Lightweight Charts 4.2.0 incorporado ao HTML, sem CDN: fundo branco, candles de alta azuis e de baixa pretos, cores configuráveis, cursor OHLC, zoom e arraste. Os resultados de mercado mantêm as regras originais. O estado pendente descrito acima documenta a sessão anterior; a versão atual usa os dados reais e checksum validado.

## Leitura em R bruto

O relatório destaca `gross_r`: movimento direcional entre a entrada executada original e a saída de referência (antes do slippage da saída), dividido pela distância inicial de stop. Stop normal = −1R, alvo = +2R; gaps e cruzamentos contrários preservam seu resultado proporcional. A entrada e os níveis continuam os mesmos da simulação original; não se recalculam sinais ou operações para melhorar os resultados. `execution_gross_r` preserva o movimento com slippage de saída; `net_r` continua descontando também as taxas e aparece apenas na auditoria de custos. `summary` preserva as métricas líquidas; `gross_summary` alimenta os indicadores e a curva visíveis.

A ficha de cada operação explica o sinal EMA9/21, o gatilho de saída, risco em USDT por BTC, duração e eventuais ambiguidades de stop/alvo no mesmo candle. São explicações da execução, sem atribuições especulativas de causa do mercado. Entrada em azul com linha pontilhada forte, stop vermelho, alvos verdes pontilhados.
