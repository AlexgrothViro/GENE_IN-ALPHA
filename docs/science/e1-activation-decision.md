# Decisao de ativacao E1

Data: 2026-07-29

Evidence V2 agora emite a saida canonica com `shadow_mode=false`, teto `E1` e registro versionado em `config/evidence_activation.json`. A versao 1.1 permanece preservada para compatibilidade historica.

Esta ativacao nao libera E2, E3 ou E4, nao muda limiares cientificos e nao autoriza linguagem diagnostica. Fragmentos de 20--49 bp continuam exploratorios e nunca promovem uma conclusao isoladamente.

Execucoes shadow sem metadados de ativacao sao aceitas apenas como artefatos historicos/fixtures para reprodutibilidade; novas execucoes devem carregar `policy_version`, `activation_record_id`, `activation_record_sha256` e `evidence_ceiling`.

## Novos perfis

- `canonical-e1`: perfil padrao, saida canonica E1, SPAdes como montador configurado.
- `assembly-consensus`: executa Velvet, SPAdes e metaSPAdes quando aplicavel; promove apenas a concordancia exata entre pelo menos dois montadores como corroboracao, sem elevar o nivel de evidencia.

## Testes desta mudanca

- Testes direcionados de ativacao, perfis e concordancia: aprovados.
- Suite Python: 156 testes coletados; 1 erro de ambiente Windows por `fcntl`, dependencia POSIX do teste de promocao de banco BLAST; 4 testes foram ignorados nominalmente.
- `compileall` Python e `bash -n` dos orquestradores: aprovados.

Revisao humana continua obrigatoria antes de declarar validacao cientifica com ferramentas reais ou ampliar o teto E1.
