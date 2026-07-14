# Plano de teste de usabilidade — Evidence V2

## Participantes

Três perfis no mínimo: bioinformata; pesquisador de virologia sem rotina de terminal; iniciante no pipeline. Não usar o mesmo participante para representar todos os perfis.

## Tarefas observadas

1. Importar um par FASTQ sintético.
2. Iniciar uma análise individual em modo simplificado.
3. Criar um lote com amostra, controle negativo e controle positivo.
4. Corrigir um R1/R2 incompatível indicado pelo formulário.
5. Explicar a diferença entre fragmento exploratório, locus e múltiplos loci.
6. Identificar o aviso de shadow mode e localizar a classificação 1.1.
7. Localizar a etapa de uma falha simulada e sugerir a ação corretiva.
8. Interpretar `UNCONTROLLED` e `CONTROL_ASSOCIATED_SIGNAL` sem concluir contaminação.
9. Abrir relatório, JSON, configuração efetiva e manifesto.
10. Explicar por que a filogenia exploratória está bloqueada.

## Métricas e aceite

- Conclusão da tarefa sem terminal; tempo, erros, pedidos de ajuda e caminhos abandonados.
- Compreensão correta de shadow mode, controles e linguagem não diagnóstica.
- Nenhum participante deve interpretar fragmento de 20–49 bp como detecção isolada.
- Registrar observações, severidade, correção, reteste e aprovação humana antes da beta externa.
