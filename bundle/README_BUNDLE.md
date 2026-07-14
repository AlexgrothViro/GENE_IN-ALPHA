# Gene-In 1.1 — Pacote de Execução Rápida (WSL Bundle)

Este diretório contém os scripts wrappers desenvolvidos para facilitar a execução rápida e isolada do pipeline **Gene-In 1.1** em computadores pessoais executando Windows (através do WSL2) ou sistemas Linux nativos, sem alterar a lógica bioinformática ou os parâmetros científicos do pipeline principal.

---

## 🚀 Como Executar no Windows (WSL2)

O bundle executa a chamada automatizada do pipeline a partir do Prompt de Comando ou PowerShell do Windows, encapsulando o interpretador do Linux de forma transparente:

1.  Certifique-se de ter habilitado o WSL2 e instalado a distribuição Ubuntu conforme as instruções descritas em:
    *   📂 [docs/INSTALACAO_WINDOWS.md](../docs/INSTALACAO_WINDOWS.md)
2.  Extraia a pasta do projeto em um diretório do computador.
3.  Utilize o atalho **`ABRIR_GENEIN.bat`** na raiz do projeto para iniciar a plataforma com suporte de interface gráfica, ou interaja via terminal do Windows com os seguintes comandos:

```cmd
# Executar a validação mínima (smoke-test)
bundle\run.bat smoke-test

# Executar o pipeline de triagem em uma amostra de teste
bundle\run.bat pipeline SAMPLE=DEMO
```

---

## 🐧 Como Executar Diretamente no WSL (Linux)

Caso prefira operar de dentro do terminal Linux integrado do WSL:

```bash
# Executar a validação de smoke-test
bash bundle/run.sh smoke-test

# Executar o pipeline para uma amostra configurada
bash bundle/run.sh pipeline SAMPLE=DEMO
```

Na primeira chamada de qualquer script, o instalador local fará o download automatizado do micromamba e configurará de forma inteiramente isolada o ambiente de bioinformática dentro da pasta do usuário no Linux (`~/.gene-in-bundle/`). Esta arquitetura nativa do Linux no espaço do usuário evita problemas comuns de permissão de escrita e alta latência característicos do sistema de arquivos NTFS do Windows.
