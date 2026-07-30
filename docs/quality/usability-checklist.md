# Checklist Manual de Usabilidade do Dashboard Web (Gene-In)

Este checklist descreve as verificações de usabilidade que devem ser executadas manualmente no painel interativo (dashboard) do **Gene-In** para garantir a qualidade de navegação e tratamento amigável de erros.

---

## 1. Acesso Local e Responsividade
- [ ] **Inicialização do Servidor:** Executar `python3 scripts/ux_dashboard.py` no terminal e certificar-se de que o servidor web local inicializa sem erros na porta `8000` (vinculando a `127.0.0.1`).
- [ ] **Navegação Inicial:** Acessar [http://localhost:8000](http://localhost:8000) e verificar o carregamento completo do layout (hero banner, abas e cards).
- [ ] **Responsividade das Abas:** Clicar em cada aba ("Execução", "Análise Complementar", "Configuração", "Histórico") e confirmar que a transição é instantânea e o conteúdo correspondente é exibido.

---

## 2. Fluxo de Análise e Execução
- [ ] **Carregamento de Parâmetros:** Na aba "Execução", certificar-se de que os montadores suportados (Velvet, SPAdes, metaSPAdes) estão disponíveis para seleção e que as opções de banco viral e número de threads podem ser alteradas.
- [ ] **Monitoramento de Execução:** Disparar uma análise (modo demo ou amostra local) e validar que:
  - O terminal do dashboard exibe o log de progresso em tempo real.
  - A barra de carregamento ou indicação de processamento funciona.
- [ ] **Visualização de Resultados:** Confirmar que, após a conclusão da análise, a tabela interativa de hits é carregada exibindo as colunas de Query, Referência, Cobertura, Identidade Ajustada e a Classe de Evidência operacional (com destaque visual/cores para cada classe).

---

## 3. Tratamento de Erros e Exibição de Alertas
- [ ] **Arquivo Inválido/Inexistente:** Tentar iniciar uma análise especificando um caminho de arquivo de leituras inexistente ou inválido no painel de configuração e verificar se:
  - O dashboard exibe uma mensagem de erro em um banner visual amigável (vermelho/alerta).
  - O traceback bruto do Python **não** é exposto na tela principal do usuário.
- [ ] **Erro de Permissão (WSL Mount):** Se a pasta do projeto estiver localizada em um diretório montado do Windows (`/mnt/c/...`), certificar-se de que o dashboard renderiza o banner de aviso recomendando a movimentação da pasta para o sistema nativo do WSL.
- [ ] **Comando Abortado:** Iniciar uma montagem pesada e fechar o navegador/reiniciar o dashboard para certificar que o backend encerra de forma limpa os subprocessos e não deixa jobs zumbis em segundo plano.
