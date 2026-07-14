# Gene-In 1.1 — Painel de Uso (UX)

O painel UX é uma interface local do **Gene-In 1.1** para apoiar o fluxo operacional de uso público.

Ele foi projetado para:

- verificar ambiente;
- rodar DEMO reprodutível;
- preparar banco viral;
- importar amostras;
- executar pipeline;
- acompanhar logs;
- acessar histórico e artefatos.

> Escopo científico: o pipeline recupera e prioriza evidências virais (com foco inicial/padrão em PTV/Teschovirus A), mas não confirma infecção sozinho.

## Como iniciar

No WSL/Linux:

```bash
make ux
```

No Windows:

```bat
start_platform.bat
```

Alternativa equivalente:

```bat
bundle\run.bat ux
```

Após iniciar, acesse: `http://localhost:8000`.

## Fluxo operacional no painel

### 1) Verificação de ambiente

- Check rápido de dependências e execução local por meio dos comandos oficiais do projeto.

### 2) DEMO reprodutível

- Execução guiada do ciclo DEMO para validar instalação e gerar artefatos de referência.

### 3) Preparação do banco viral

No fluxo público oficial, a preparação de banco usa:

- `make db`
- `scripts/13_db_manager.sh`

O dashboard pode usar endpoints internos para orquestração da interface, mas a documentação pública deve permanecer compatível com esse fluxo oficial (`make db`/`13_db_manager.sh`).

### 4) Importação de amostras

- Registro de amostras pareadas (R1/R2), com suporte a caminhos locais e fluxos assistidos pela interface.

### 5) Execução do pipeline

- Disparo da execução por amostra, com trilha de auditoria de status e artefatos.

### 6) Histórico, logs e artefatos

- Consulta de execuções anteriores e acesso aos principais outputs de cada rodada.

## Logs e rastreabilidade

- Logs do dashboard: `logs/ux_dashboard_*.log`
- Metadados por execução: `results/runs/<timestamp>_<sample>/run.json`

Esses arquivos ajudam na auditoria operacional e no rastreamento de parâmetros/estado de execução.

## Observação sobre legado

Referências históricas a scripts antigos podem existir em materiais técnicos internos, mas o fluxo principal documentado para banco viral é `make db` com `scripts/13_db_manager.sh`.
