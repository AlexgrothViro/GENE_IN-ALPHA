# Resolução de Problemas (Troubleshooting)

Este guia descreve as causas e soluções para as falhas e dúvidas mais comuns encontradas durante a configuração e execução do pipeline **Gene-In 1.1**.

---

## 1. Falha ao Encontrar Dependências no Ambiente (`make test-env`)

*   **Sintoma:** O comando retorna mensagens indicando que o `blast+`, `bowtie2` ou outras ferramentas essenciais não foram encontradas.
*   **Causa:** O ambiente científico isolado do Gene-In não foi criado ou não está ativado no shell.
*   **Solução:**
    Execute o script de instalação para recriar o ambiente isolado do micromamba:
    ```bash
    ./install_linux.sh
    ```
    Caso prefira forçar a reinstalação das dependências:
    ```bash
    make deps
    ```

---

## 2. Erro de Permissão Negada em Scripts (WSL2 / Linux)

*   **Sintoma:** `bash: scripts/00_check_env.sh: Permission denied` ao tentar rodar comandos.
*   **Causa:** Os arquivos perderam a permissão de execução (comum após clonar repositórios ou descompactar arquivos no Windows/WSL).
*   **Solução:**
    Conceda permissão de execução aos scripts shell e utilitários Python:
    ```bash
    make fix-wsl
    # Alternativamente, execute de forma manual:
    chmod +x scripts/*.sh scripts/*.py
    ```

---

## 3. Lentidão Extrema ou Erros de Escrita em I/O no WSL2

*   **Sintoma:** O pipeline demora tempos excessivos nas fases de montagem de contigs e leitura de arquivos, ou reporta falhas ao salvar arquivos temporários. O painel web exibe alertas de latência de disco.
*   **Causa:** A pasta do Gene-In está localizada em um diretório montado do Windows pelo WSL. A ponte de tradução de arquivos entre o Windows (NTFS) e o Linux do WSL2 possui altíssima latência.
*   **Solução:** Mova o diretório completo do projeto para dentro do sistema de arquivos nativo do Linux (por exemplo, na pasta home `~` do seu usuário no Ubuntu):
    ```bash
    # A partir da pasta atual do Gene-In, copiar o projeto para a home do Linux
    cp -a . ~/Gene-In-Public

    # Acessar a nova localização e rodar dali
    cd ~/Gene-In-Public
    ```

---

## 4. SPAdes: Opção `--rnaviral` não reconhecida

*   **Sintoma:**
    ```text
    Unknown option: --rnaviral
    ```
*   **Causa:** A versão do SPAdes instalada via gerenciador de pacotes antigo do sistema operacional (como `apt` em distribuições Linux antigas) é igual ou inferior a 3.13, que não suporta a flag `--rnaviral`.
*   **Solução (Opção A — Remover a flag via variáveis de ambiente):**
    Abra o arquivo `config/picornavirus.env` e remova a flag `--rnaviral` de `SPADES_PARAMS`. Exemplo de alteração:
    ```bash
    SPADES_PARAMS="-k 21,33,55,77"
    ```
    Ou execute o pipeline especificando o parâmetro diretamente na linha de comando:
    ```bash
    bash scripts/20_run_pipeline.sh --sample DEMO --assembler spades --spades-params "-k 21,33,55,77"
    ```
*   **Solução (Opção B — Atualizar o SPAdes no ambiente isolado):**
    Garanta que o pipeline esteja utilizando o SPAdes fornecido pelo ambiente isolado do Gene-In em `~/.gene-in-bundle/env/bin/spades.py`. Caso queira reinstalar via Conda:
    ```bash
    conda install -c bioconda spades
    ```

---

## 5. BLAST: Banco de Dados não Encontrado

*   **Sintoma:**
    ```text
    [ERRO] Banco BLAST não encontrado em blastdb/ptv.nhr
    ```
*   **Causa:** O banco de referências virais não foi gerado ou foi corrompido.
*   **Solução:**
    Gere o banco BLAST executando:
    ```bash
    make db DB=ptv
    # Ou para gerar apenas os índices do BLAST local:
    make blastdb
    ```

---

## 6. Velvet: Falha por Segmentation Fault (Exit Code 139)

*   **Sintoma:** O pipeline interrompe a execução com a mensagem `Velvet falhou com segmentation fault (exit code 139)`.
*   **Causa:** Limitação de memória física, incompatibilidade do montador com a alta densidade de leituras de tamanho muito reduzido, ou latência crítica ao acessar arquivos em pasta montada do Windows pelo WSL.
*   **Solução:**
    A forma mais robusta de contornar essa limitação é utilizar o montador SPAdes ou metaSPAdes:
    ```bash
    make pipeline SAMPLE=<id> ASSEMBLER=spades
    # Ou utilizando metaSPAdes:
    make pipeline SAMPLE=<id> ASSEMBLER=metaspades
    ```
    Se estiver usando a interface gráfica local, altere o montador no seletor "Assembler" do dashboard de "Velvet" para "SPAdes".

---

## 7. Windows: Erros ao Rodar os Atalhos `.bat`

*   **Sintomas:**
    *   `[ERRO] O ambiente nao esta preparado: WSL nao foi encontrado.`
    *   `[ERRO] O ambiente nao esta preparado: nenhuma distribuicao Ubuntu foi encontrada.`
*   **Causa:** O Windows Subsystem for Linux (WSL2) ou a distribuição Ubuntu não foram ativados no seu Windows.
*   **Solução:**
    Abra o PowerShell do Windows como administrador e execute a instalação do subsistema:
    ```cmd
    wsl --install -d Ubuntu-24.04
    ```
    Após reiniciar o computador e concluir a criação do usuário Linux, execute novamente o script `INSTALAR_GENEIN.bat`.
