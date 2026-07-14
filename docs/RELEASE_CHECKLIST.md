# Checklist de Publicação Pública e Validação Científica (Release)

Este checklist descreve as verificações obrigatórias de integridade, privacidade e segurança que devem ser executadas antes de gerar uma nova versão pública (release/tag) do **Gene-In 1.1** no GitHub.

---

## 1. Verificação de Integridade de Códigos e Comandos
- [ ] **Limpeza de arquivos CRLF:** Garantir que quebras de linha do Windows não tenham sido introduzidas nos scripts Linux (`make fix-wsl`).
- [ ] **Validação de ambiente nativo:** Executar o script de conformidade ambiental (`make test-env`) e certificar-se de que não ocorram erros.
- [ ] **Checklist de instalação:** Executar o instalador `./install_linux.sh` (ou `INSTALAR_GENEIN.bat`) em uma máquina de teste limpa para validar que os downloads e configurações do micromamba são executados corretamente do início ao fim.

---

## 2. Validação da Execução Controlada (Modo Demo)
- [ ] **Executar o demo local:**
  ```bash
  make demo
  make run-demo
  ```
- [ ] **Checagem de saídas do demo:** Executar o script de auditoria do demo para certificar que todos os TSVs e relatórios Markdown esperados estão presentes e íntegros:
  ```bash
  make test-demo SAMPLE=DEMO
  ```

---

## 3. Higienização e Privacidade de Dados (Segurança Biológica e Privada)
- [ ] **Ausência de FASTQs reais:** Garantir que nenhum arquivo FASTQ de sequenciamento de amostra real (pacientes, animais de campo ou experimentos confidenciais) esteja presente nas subpastas de `data/raw/` ou versionado no Git.
- [ ] **Ausência de FASTAs sensíveis:** Validar que arquivos de referência proprietários não estejam salvos na pasta `data/ref/`.
- [ ] **Ausência de alinhamentos brutos:** Certificar-se de que arquivos gigantes de alinhamento intermediário (`.bam`, `.sam`, `.bai`, `.fastq`) não foram adicionados ao repositório.
- [ ] **Ausência de bancos locais:** Garantir que os arquivos binários gerados pelo BLAST ou Bowtie2 no seu computador (extensões `.nhr`, `.nin`, `.nsq`, `.bt2`) não estejam versionados. O banco deve ser gerado pelo usuário localmente com o comando `make db`.
- [ ] **Ausência de resultados confidenciais:** Excluir da pasta `results/` qualquer relatório, tabela ou arquivo `.tsv` pertencente a dados reais de pesquisa antes de publicar.
- [ ] **Remoção de logs de testes:** Limpar a pasta `logs/` para remover históricos de execução de computadores locais.

---

## 4. Segurança de Credenciais e Arquivos Privados
- [ ] **Ausência de credenciais:** Garantir que chaves de API, senhas, tokens de download do NCBI ou credenciais institucionais de servidores locais não estejam salvas em scripts ou arquivos `.env`.
- [x] **Arquivos de configuração desversionados:** Garantir que arquivos locais ativos (`config.env` e `config/picornavirus.env`) não estejam sob controle de versão (devem estar no `.gitignore`). Apenas os templates `.example` devem ser versionados.
- [ ] **Ausência de arquivos ocultos ou temporários:** Remover arquivos do tipo `.DS_Store`, temporários de editores de texto (como `*~` ou `.#*`) e pastas internas de desenvolvimento experimental não documentadas.

---

## 5. Revisão Documental e Conformidade de Publicação
- [ ] **Revisão de caminhos:** Verificar que não existam links absolutos ou locais para arquivos do seu computador (como caminhos contendo `C:/Users/...`). Todos os hiperlinks internos devem ser caminhos relativos de markdown.
- [ ] **Revisão de Encoding:** Garantir que todos os arquivos de documentação (`.md`, `.tsv`, `.py`, `.sh`) estejam salvos em codificação **UTF-8** sem BOM, evitando quebras de acentuação na renderização pública do GitHub.
- [ ] **Integridade Documental:** Validar que todos os documentos de texto reflitam a versão atualizada do software, sem referências desatualizadas a versões anteriores ou notas internas de desenvolvimento.
- [ ] **Conformidade de Créditos:** Validar que todas as menções a instituições parceiras, pesquisadores e fontes de fomento estejam inseridas estritamente em conformidade com as citações científicas e metodológicas do projeto.
- [ ] **Validação do README:** Certificar que o `README.md` principal apresenta de forma clara o escopo científico, as limitações biológicas, o modo demo e as citações provisórias do projeto.

---

## 6. Publicação e Geração de Tags
- [ ] **Consistência do Git:** Garantir que os comandos `git status` indiquem que o diretório de trabalho está limpo.
- [ ] **Criação de Tag:** Utilizar convenção de versão semântica coerente com o histórico do CHANGELOG (ex: `v1.1.0`).
