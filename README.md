# Trading Backtest

Laboratório de backtest e visualização de trades em HTML com Lightweight Charts.

## Comece por aqui

- [Arquitetura, cálculo de R e publicação](BACKTEST_ARQUITETURA_E_PUBLICACAO.md)
- [Como executar o laboratório](backtest/README.md)
- [Histórico dos estudos e correções](backtest/ESTUDOS.md)

## Origem

Importação da pasta `backtest/` de `Lubra-Lucas/Ovecchia`, branch
`claude/gallant-ride-pdbcvn`, commit `3373d0065a0e5712ad4f9e968f1be6869dcad1bd`.
Os hashes dos 71 arquivos originais estão em `MANIFEST_BACKTEST.json`.
O documento de arquitetura inclui o código dos sete arquivos do caminho principal.
Todos os arquivos do pacote original já estão extraídos neste repositório.

Os manifests Python da raiz também vieram da origem e incluem dependências do
aplicativo antigo; foram preservados para reprodução do ambiente original.
Streamlit e bot Telegram não foram importados como aplicações.

Esta importação preserva o código e os resultados históricos. Não publica o site
nem representa uma nova execução dos estudos. As instruções de geração e
publicação estática estão no documento de arquitetura. Dados de mercado e JSONs
gerados devem ser produzidos novamente; `cache/` e `saida/` não estão incluídos.
