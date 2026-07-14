# Guia de Instalação no Windows via WSL2

O **Gene-In 1.1** utiliza as ferramentas científicas nativas do ecossistema Linux (como BLAST+, Bowtie2, Velvet, SPAdes e o gerenciador micromamba). Para permitir que usuários executem essas ferramentas diretamente no sistema operacional Windows (10 ou 11), a plataforma utiliza o **WSL2 (Windows Subsystem for Linux)**, preferencialmente configurado com a distribuição **Ubuntu 24.04 LTS**.

Para maquinas sem WSL/Ubuntu ou computadores com permissao restrita, leia tambem [`GUIA_RAPIDO_WINDOWS.md`](GUIA_RAPIDO_WINDOWS.md). Ele resume o que precisa estar liberado no Windows, no Ubuntu e na rede.

---

## 🚀 Método de Instalação Simplificado (Usuário Final)

Você **não precisa dominar comandos de Linux ou terminal** para configurar o Gene-In. A plataforma possui scripts interativos que automatizam a detecção e instalação.

### Passo 1: Executar o Instalador
Navegue até a pasta raiz do projeto no Windows e clique duas vezes no arquivo:
*   **📥 `INSTALAR_GENEIN.bat`**

Este script abrirá um terminal e guiará você pelas seguintes etapas automáticas:
1.  **Detecção do WSL:** Verifica se o subsistema Linux está ativo no Windows.
2.  **Verificação do Ubuntu:** Identifica se há uma distribuição Ubuntu compatível instalada.
3.  **Dependências do Linux:** Verifica as ferramentas fundamentais (como `make` e `python3`). Caso alguma esteja ausente, o instalador solicitará sua aprovação para instalá-la de forma automatizada (nesta etapa, pode ser solicitada a senha definida por você durante a criação do seu usuário no Ubuntu/Linux).
4.  **Configuração do Ambiente Isolado:** Cria um ambiente científico local (`~/.gene-in-bundle`) na sua home do WSL para armazenar os pacotes de bioinformática e Python, garantindo que não ocorram conflitos de software no seu computador.

### Passo 2: Iniciar a Plataforma
Após o instalador confirmar o sucesso da configuração, clique duas vezes no arquivo:
*   **🚀 `ABRIR_GENEIN.bat`**

O terminal inicializará o servidor local do dashboard web do Gene-In.

### Passo 3: Acesso ao Dashboard
Abra seu navegador web e digite:
*   **🌐 [http://localhost:8000](http://localhost:8000)**

Para fechar o servidor e encerrar a plataforma, feche a janela do terminal ou pressione `Ctrl + C`.

---

## 🛠️ Requisitos Mínimos do Sistema

*   **Sistema Operacional:** Windows 10 (versão 2004 ou superior, Build 19041 ou superior) ou Windows 11.
*   **Subsistema Linux:** WSL2 ativo.
*   **Distribuição Recomendada:** **Ubuntu 24.04 LTS**. (Também compatível com Ubuntu 22.04 LTS ou Ubuntu 20.04 LTS).
*   **Espaço Livre:** Pelo menos 5 GB livres em disco para acomodar os índices de referência e bancos virais.
*   **Conexão de Internet:** Necessária na primeira execução para realizar o download dos pacotes bioinformáticos.

---

## Instalação em computadores com permissões restritas

Em computadores com permissões restritas, a ativação do WSL2 ou o comando de instalação automática (`sudo apt`) podem falhar por falta de permissões de administrador no Windows ou no Ubuntu.

### Configuração com permissões de administrador

1.  **Habilitar o WSL2 e instalar o Ubuntu 24.04 LTS:**
    Execute no PowerShell do Windows como Administrador:
    ```cmd
    wsl --install -d Ubuntu-24.04
    ```
    *Caso seja necessário reiniciar a máquina, reinicie e aguarde o terminal do Ubuntu abrir para que o pesquisador configure o usuário e senha do Linux.*

2.  **Instalar pacotes básicos de desenvolvimento no Ubuntu:**
    Execute no terminal do Ubuntu (via WSL):
    ```bash
    sudo apt update
    ```
    ```bash
    sudo apt install -y make build-essential git curl wget unzip dos2unix tar bzip2 ca-certificates python3 python3-venv
    ```

3.  **Permissões de Usuário:**
    Certifique-se de que o usuário possua direitos de escrita no diretório onde o repositório do Gene-In está salvo, permissão para executar o comando `wsl.exe`, e que conheça as credenciais criadas para o seu usuário do Ubuntu.

Uma vez concluídos os três passos acima, o usuário poderá executar o arquivo `INSTALAR_GENEIN.bat` normalmente no Windows sem necessitar de privilégios de administrador adicionais.

---

## ❓ Resolução de Dúvidas Comuns

Caso encontre erros relacionados a permissões de script, CRLF do Windows ou problemas na montagem de diretórios do sistema de arquivos do Windows (`/mnt/c`), consulte o guia completo de diagnóstico:
*   📂 [Manual de Resolução de Problemas (Troubleshooting)](TROUBLESHOOTING.md)
