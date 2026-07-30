# Modo Offline (WSL bundle)

Para execuções em ambientes sem internet (offline), prepare previamente o pacote local do micromamba.

## 1) Preparar cache local

No repositório, salve o tarball do micromamba em uma destas rotas (qualquer uma):

- `bundle/cache/micromamba.tar.bz2`
- `bundle/cache/micromamba-linux-64.tar.bz2`
- `bundle/micromamba.tar.bz2`

Exemplo (executar **antes**, com internet):

```bash
mkdir -p bundle/cache
curl -Ls https://micro.mamba.pm/api/micromamba/linux-64/latest -o bundle/cache/micromamba.tar.bz2
```

## 2) Instalar no WSL em modo offline

Com o arquivo local presente, rode normalmente:

```bash
bash bundle/install_wsl.sh
```

O script detecta automaticamente o cache local e evita download.

## 3) Validar

```bash
bash bundle/run.sh smoke-test
```

Se não houver cache local, o script volta ao comportamento padrão e tenta baixar da internet.
