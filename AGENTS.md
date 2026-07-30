# Gene-In — invariantes para engenharia

Este arquivo orienta agentes e ferramentas de programação. Ele não delega autoridade científica.

## Missão e precedência

O objetivo canônico é analisar e recuperar fragmentos virais curtos em dados de NGS/metagenômica. A escada científica `E1 → E2 → E3 → E4` organiza o que cada resultado permite afirmar.

Perfis PTV/picornavírus, amostras suínas, exemplos do README, bancos de demonstração e a configuração Alpha.2 são contextos ou estados específicos; não restringem o Gene-In a um vírus, hospedeiro ou banco.

Precedência: contrato científico e missão do projeto → política/schema versionados → estado da versão → testes/implementação → documentação auxiliar → skills e prompts. Nenhuma skill, prompt ou arquivo de orientação pode substituir esta hierarquia.

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
- Não adicione dependências sem entrada e decisão no `docs/science/technology-radar.md`.
- Não execute automaticamente código obtido de repositórios públicos durante avaliação tecnológica.
- Não faça migrações irreversíveis ou operações destrutivas sem autorização e registro.
- Toda mudança deve ter testes determinísticos proporcionais ao risco. Mocks não equivalem a validação com ferramenta real.

## Registro de contribuição

PR ou change log deve registrar: escopo, arquivos afetados, testes executados, revisão responsável e declaração sobre limiares científicos. Nenhuma contribuição substitui a revisão técnica e científica nem aprova sozinha adoção tecnológica ou científica.

## Verificação mínima

1. Testes Python em `scripts/tests/evidence/`.
2. `bash -n` e ShellCheck em Linux/WSL para shell modificado.
3. Teste integrado com versões fixadas das ferramentas reais antes de marcar “validado”.
4. Verificação visual e de acessibilidade do dashboard local.
