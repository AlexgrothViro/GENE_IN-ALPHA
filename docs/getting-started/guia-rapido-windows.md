# Guia rapido para Windows, WSL e permissoes de administrador

Este guia e para quem vai instalar o Gene-In no Windows, mesmo sem experiencia previa com Linux, WSL ou terminal.

O Gene-In usa ferramentas cientificas que rodam em Linux, como BLAST+, Bowtie2, Velvet, SPAdes e Micromamba. No Windows, essas ferramentas rodam por meio do WSL2 com Ubuntu. O instalador do Gene-In ajuda a detectar o que falta e instala o ambiente do Gene-In depois que WSL/Ubuntu estao disponiveis.

Algumas etapas podem exigir permissao de administrador do computador. Se voce nao tiver essa permissao, sera necessario pedir a alguem que tenha acesso de administrador para executar esses passos.

## Comece aqui

1. Extraia a pasta do Gene-In em um local simples, como `Downloads`, `Documentos` ou `Desktop`.
2. Nao coloque o Gene-In em `C:\Program Files` nem em pastas protegidas do Windows.
3. Entre na pasta extraida do Gene-In.
4. Clique duas vezes em `INSTALAR_GENEIN.bat`.
5. Leia a mensagem da janela preta antes de fechar. Ela vai dizer o que esta faltando.

Se a instalacao terminar com sucesso, clique duas vezes em:

```text
ABRIR_GENEIN.bat
```

O navegador deve abrir em:

```text
http://localhost:8000
```

## Escolha o seu caso

| O que apareceu | O que fazer |
|---|---|
| `INSTALAR_GENEIN.bat` terminou com `[OK]` | Abra `ABRIR_GENEIN.bat`. |
| WSL nao foi encontrado | Abra PowerShell como Administrador e instale WSL/Ubuntu com `wsl --install -d Ubuntu-24.04`. |
| Nenhuma distribuicao Ubuntu foi localizada | Instale o Ubuntu ou abra o Ubuntu pelo menu Iniciar uma vez para concluir a criacao de usuario e senha. |
| O Ubuntu pediu senha | Digite a senha criada no Ubuntu. A senha nao aparece enquanto voce digita; isso e normal. |
| Erro de `sudo` | O usuario do Ubuntu nao tem permissao administrativa. Entre com um usuario com `sudo` ou ajuste a permissao desse usuario. |
| Erro de internet, `apt`, Conda, Micromamba ou NCBI | Verifique conexao e firewall. A primeira instalacao precisa baixar pacotes e referencias. |
| `Address already in use` ou porta 8000 ocupada | O Gene-In pode ja estar aberto. Acesse `http://localhost:8000` ou feche a janela antiga. |

## O que e normal durante a instalacao

- A janela preta pode ficar aberta por varios minutos.
- A primeira instalacao pode baixar muitos pacotes.
- O Windows pode pedir reinicio depois de instalar WSL/Ubuntu.
- O Ubuntu pode pedir para criar usuario e senha na primeira abertura.
- Ao digitar a senha do Ubuntu, nada aparece na tela. Continue digitando e pressione Enter.
- Se o computador nao permitir instalar WSL, Ubuntu ou pacotes, sera necessario usar uma conta com permissao de administrador.

## Roteiro para Windows sem WSL/Ubuntu

1. Clique em `INSTALAR_GENEIN.bat`.
2. Se aparecer que falta WSL ou Ubuntu, abra o menu Iniciar e procure `PowerShell`.
3. Clique com o botao direito em PowerShell e escolha `Executar como Administrador`.
4. Rode:

```cmd
wsl --install -d Ubuntu-24.04
```

5. Reinicie o Windows se for solicitado.
6. Abra `Ubuntu` pelo menu Iniciar.
7. Crie um usuario e uma senha quando o Ubuntu pedir.
8. Feche o Ubuntu.
9. Volte para a pasta do Gene-In.
10. Clique novamente em `INSTALAR_GENEIN.bat`.
11. Se o instalador perguntar se pode instalar dependencias, responda `S`.
12. Se pedir senha, digite a senha criada no Ubuntu.
13. Ao final, clique em `ABRIR_GENEIN.bat`.

## O que precisa estar liberado no computador

Para instalar em Windows novo ou bloqueado, o computador precisa permitir:

- WSL2 no Windows.
- Recurso `Windows Subsystem for Linux`.
- Recurso `Virtual Machine Platform`.
- Virtualizacao habilitada na BIOS/UEFI, quando estiver desativada.
- Instalacao de uma distribuicao Ubuntu, preferencialmente `Ubuntu-24.04`.
- Execucao de `wsl.exe` pelo usuario.
- Abertura do Ubuntu para criar usuario e senha Linux.
- Permissao de `sudo` dentro do Ubuntu para instalar pacotes via `apt`.
- Escrita na pasta onde o Gene-In foi extraido.
- Uso local de `127.0.0.1` / `localhost`, especialmente porta `8000`, para abrir o dashboard.

## Pacotes basicos no Ubuntu

Se for necessario preparar o Ubuntu manualmente, abra o Ubuntu e rode:

```bash
sudo apt update
sudo apt install -y make build-essential git curl wget unzip dos2unix tar bzip2 ca-certificates python3 python3-venv
```

Para confirmar que o usuario tem permissao de `sudo`:

```bash
sudo -v
```

Para confirmar que os comandos basicos existem:

```bash
command -v make
command -v python3
command -v curl
command -v tar
command -v bzip2
```

## Internet e firewall

Na primeira instalacao, podem ser necessarios acessos externos para:

- repositorios `apt` do Ubuntu;
- GitHub, caso o pacote seja baixado ou atualizado por Git;
- `micro.mamba.pm`;
- canais Conda/Bioconda/Conda-Forge;
- NCBI, para download ou consulta de referencias biologicas.

Se a rede bloquear esses acessos, a instalacao pode parar mesmo com WSL e sudo corretos.

## Problemas comuns

### WSL nao foi encontrado

O Windows ainda nao tem WSL habilitado. Abra PowerShell como Administrador e rode:

```cmd
wsl --install -d Ubuntu-24.04
```

### WSL existe, mas Ubuntu nao foi localizado

O Ubuntu ainda nao foi instalado ou ainda nao foi aberto pela primeira vez. Instale o Ubuntu, abra pelo menu Iniciar e conclua a criacao de usuario e senha.

### Erro de sudo

O usuario Linux nao tem permissao administrativa dentro do Ubuntu. Use um usuario com `sudo` ou ajuste a permissao desse usuario antes de instalar os pacotes basicos.

### Senha do sudo

A senha solicitada pelo `sudo` e a senha criada no Ubuntu, nao necessariamente a senha do Windows.

### Porta 8000 ocupada

Se aparecer `Address already in use`, provavelmente ja existe um dashboard aberto em `http://localhost:8000`. Feche a janela antiga ou use outra porta:

```cmd
bundle\run.bat ux PORT=8001
```

Depois acesse:

```text
http://localhost:8001
```

## Checklist final

- `wsl.exe` abre normalmente no Windows.
- Ubuntu 24.04 abre pelo menu Iniciar.
- Usuario Linux foi criado.
- `sudo -v` funciona no Ubuntu.
- `make`, `python3`, `curl`, `tar` e `bzip2` estao disponiveis.
- O usuario consegue escrever na pasta do Gene-In.
- `INSTALAR_GENEIN.bat` conclui sem erro critico.
- `ABRIR_GENEIN.bat` abre `http://localhost:8000`.
