# ShellCheck — alpha.2

Execução local em 2026-07-14 com ShellCheck 0.11.0 em todos os arquivos `*.sh` rastreados pelo Git, com severidade `warning`.

- Resultado atual: **falha**, 58 achados.
- SC1090: 49 fontes de configuração dinâmicas sem diretiva local explícita.
- SC2034: 9 atribuições aparentemente não utilizadas.
- SC2155: **0**; a atribuição de diretório agora preserva a falha de `dirname`.
- SC2164: **0**; o smoke test agora encerra se `cd` falhar.
- SC1010: **0** depois de cotar o argumento de estado `"done"` nos entrypoints V2.

Não há supressão global. O workflow `.github/workflows/shellcheck.yml` executa o mesmo gate sobre todos os scripts e bloqueia integração enquanto houver achados. Cada SC1090 só poderá ser suprimido por diretiva local com justificativa e arquivo conhecido, ou eliminado por carregamento de configuração verificável.

Este resultado é uma verificação estática local; não prova execução dos programas externos em Linux.
