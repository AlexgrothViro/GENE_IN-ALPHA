# Estado do congelamento 1.1

O snapshot local não contém metadata Git canônica e já declara `2.0.0-alpha.1`. Portanto, ele não pode ser rotulado retroativamente como `v1.1-validation` sem comprometer a rastreabilidade.

O utilitário `scripts/91_freeze_validation_snapshot.py` está disponível para ser executado somente sobre a árvore canônica que ainda declare versão 1.1. Ele recusa uma versão diferente, exclui dados/resultados/logs e produz manifesto atômico SHA-256. Tag e branch continuam pendentes até a localização do repositório Git canônico.

Não inicializar Git neste snapshot e não forçar `--expected-version` para contornar a verificação.
