# Gene-In — invariantes para engenharia assistida

Este arquivo orienta agentes e ferramentas de programação. Ele não delega autoridade científica.

## Invariantes científicas

- Preserve a versão 1.1 e mantenha `shadow_mode=true` enquanto os gates de ativação não forem aprovados.
- Não altere limiares, classes, tetos de conclusão ou políticas científicas sem aprovação técnica e científica documentada.
- Fragmentos de 20–49 bp são exploratórios. Nunca os promova isoladamente a identificação, detecção ou resultado positivo.
- Não use linguagem diagnóstica. Prefira “sequência candidata”, “homologia compatível”, “evidência computacional” e “requer validação complementar”.
- Use somente fixtures sintéticos, controles públicos ou dados formalmente autorizados. Dados fora do conjunto científico formal não entram em benchmark, artigo, dissertação ou validação.
- Uma razão amostra/controle provisória altera apenas `control_status`; não confirma contaminação.

## Invariantes de engenharia

- Uma execução Evidence V2 só é válida quando o diretório completo foi promovido e contém `SUCCESS.json` escrito por último.
- Nunca reutilize staging ou artefatos sem marcador de sucesso. Preserve a última execução válida até a promoção completa da próxima.
- Use escrita temporária e promoção atômica para estado, manifestos, índices, BAM/BAI, TSV, JSON, FASTA e relatórios.
- Valide IDs, schemas, caminhos, FASTQ/FASTA, BAM/BAI e enums antes de executar ferramentas externas.
- Não adicione dependências sem entrada e decisão no `docs/TECHNOLOGY_RADAR.md`.
- Não execute automaticamente código obtido de repositórios públicos durante avaliação tecnológica.
- Não faça migrações irreversíveis ou operações destrutivas sem autorização e registro.
- Toda mudança deve ter testes determinísticos proporcionais ao risco. Mocks não equivalem a validação com ferramenta real.

## Registro de contribuição assistida por IA

PR ou change log deve registrar: ferramenta, escopo, arquivos afetados, testes executados, revisão humana e declaração sobre limiares científicos. IA pode sugerir e implementar código revisável, mas não aprova adoção tecnológica ou científica.

## Verificação mínima

1. Testes Python em `scripts/tests/evidence/`.
2. `bash -n` e ShellCheck em Linux/WSL para shell modificado.
3. Teste integrado com versões fixadas das ferramentas reais antes de marcar “validado”.
4. Verificação visual e de acessibilidade do dashboard local.
