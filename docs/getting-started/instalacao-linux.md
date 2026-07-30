# Guia de Instalação em Linux Nativo

O **Gene-In 1.1** foi projetado para rodar nativamente em ambientes Linux. Para garantir a estabilidade e evitar conflitos com outras instalações existentes de Python, Conda ou Mamba no sistema, a plataforma utiliza um ambiente científico isolado gerenciado localmente via `micromamba`.

---

## 🚀 Como Instalar e Executar

### Passo 1: Instalação do Ambiente (Apenas no primeiro uso)
Abra o terminal na pasta do projeto e execute o script de instalação automática:

```bash
./install_linux.sh
```

**O que o instalador realiza automaticamente:**
1.  **Validação básica:** Verifica a presença de ferramentas essenciais de sistema (`curl`, `tar`, `bash`).
2.  **Isolamento de ambiente:** Detecta se há ambientes Conda ou Mamba globais ativos no seu terminal e garante que o Gene-In não interfira com eles.
3.  **Configuração do micromamba:** Instala localmente o executável do gerenciador de pacotes em `~/.gene-in-bundle/bin/micromamba`.
4.  **Criação do ambiente científico:** Baixa e instala todas as dependências de Python e ferramentas de bioinformática (como BLAST+, Bowtie2, Velvet, SPAdes, etc.) necessárias para o pipeline, armazenando-as de forma isolada em `~/.gene-in-bundle/env`.

### Passo 2: Inicialização do Painel Web (Uso rotineiro)
Sempre que desejar interagir com o Gene-In via interface gráfica local, execute:

```bash
./run_linux.sh
```

**O que o inicializador realiza:**
1.  Valida se o ambiente isolado foi criado corretamente (caso contrário, orienta a execução do instalador).
2.  Inicia o servidor web local utilizando o interpretador Python do ambiente isolado.

### Passo 3: Acesso ao Dashboard
Abra seu navegador de preferência e digite o endereço:

```text
http://localhost:8000
```

Para encerrar o servidor web local e fechar a plataforma, basta pressionar `Ctrl + C` no terminal.

---

## 🛠️ Requisitos de Sistema

| Requisito | Descrição |
|---|---|
| **Sistema Operacional** | Linux (distribuições populares como Ubuntu, Debian, Fedora, Arch, etc.) |
| **Ferramentas de Sistema** | `bash`, `curl` (ou `wget`), `tar` |
| **make** | Necessário para execução do pipeline via linha de comando |
| **Privilégios** | **Sem necessidade de permissões de administrador (`sudo`)** para as bibliotecas de bioinformática, as quais são instaladas integralmente na pasta do usuário (`~/.gene-in-bundle`). |
| **Conexão de Rede** | Necessária durante o primeiro uso para realizar o download dos pacotes. |

*Nota:* O uso de `sudo` pode ser solicitado apenas se o seu sistema não possuir os comandos básicos (`curl`, `tar`, `make`) instalados de fábrica.

---

## 🔒 Coexistência com Conda/Mamba Global

O Gene-In **não interfere** e **não é afetado** por gerenciadores Conda Globais instalados em sua máquina.
*   **Sem Alterações Ocultas:** O instalador do Gene-In não modifica arquivos de configuração do seu terminal (como `.bashrc` ou `.zshrc`).
*   **Sem Instalações Globais:** Nenhum pacote do pipeline é instalado no Conda raiz do seu computador.

---

## ❓ Resolução de Dúvidas e Problemas Comuns

Se você encontrar mensagens de erro durante a execução (como falta de bibliotecas, problemas com comandos ou lentidão), consulte o manual específico de diagnóstico:
*   📂 [Manual de Resolução de Problemas (Troubleshooting)](TROUBLESHOOTING.md)
