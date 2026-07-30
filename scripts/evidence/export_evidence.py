#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

try:
    from .common import write_text_atomic
    from .evidence_contract import promote_for_public_output
except ImportError:
    from common import write_text_atomic
    from evidence_contract import promote_for_public_output


def render(data: dict, *, validated: bool = False) -> str:
    if not validated:
        data = promote_for_public_output(data)
    if isinstance(data.get("samples"), list):
        raise ValueError("batch evidence must be rendered by summarize_batch.py")
    specificity = data["specificity"].get("status", "NOT_EVALUATED")
    coverage = data["coverage"].get("status", "NOT_EVALUATED")
    controls = data["controls"].get("status", "NOT_EVALUATED")
    candidates = data.get("candidates", [])
    gate_lines = "\n".join(
        f"- `{gate.get('gate_id', 'unknown')}`: **{gate.get('status', 'NOT_EVALUATED')}** — {gate.get('reason', '')}"
        for gate in data["promotion_gates"]
    )
    caveat_lines = "\n".join(f"- {item}" for item in data["caveats"])
    candidate_lines = "\n".join(
        f"- `{item.get('candidate_id', '')}` — referência `{item.get('reference_id', '')}`, "
        f"categoria `{item.get('category', '')}`, locus `{item.get('locus_id', '')}`, "
        f"classe `{item.get('candidate_class', 'NOT_EVALUATED')}`, "
        f"promoção `{item.get('promotion_status', 'NOT_EVALUATED')}`"
        + (
            f", bloqueios `{', '.join(item.get('blocking_reasons', []))}`"
            if item.get("blocking_reasons") else ""
        )
        for item in candidates
    ) or "- Nenhum candidato recuperado nas condições avaliadas."
    mode_notice = (
        "**SHADOW MODE:** saída de triagem computacional."
        if data["shadow_mode"]
        else "**E1 ATIVO:** saída canônica limitada a evidência computacional."
    )
    policy_rows = ""
    if not data["shadow_mode"]:
        policy_rows = (
            f"| Política | `{data['policy_version']}` |\n"
            f"| Registro de ativação | `{data['activation_record_id']}` |\n"
            f"| Teto | `{data['evidence_ceiling']}` |\n"
        )
    return f"""# Gene-In 2.0 — relatório de evidência — {data['sample_id']}

> {mode_notice} E1 não afirma presença, ausência, identidade ou confirmação viral.

## Estado público

| Dimensão | Valor |
|---|---|
| Run ID | `{data['run_id']}` |
| Execução | `{data['execution_status']}` |
| Resultado da análise | `{data['analysis_outcome']}` |
| Nível de evidência | `{data['evidence_level']}` |
| Especificidade | `{specificity}` |
| Cobertura | `{coverage}` |
| Controles | `{controls}` |
{policy_rows}

## Candidatos medidos

{candidate_lines}

## Gates de promoção

{gate_lines}

## Ressalvas obrigatórias

{caveat_lines}

## Política de interpretação

- E2 e E3 estão bloqueados na versão alpha.2.
- E4 nunca é emitido pelo software.
- `NO_EVIDENCE_RECOVERED` descreve somente a execução nas condições avaliadas; não equivale a ausência viral.
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Export the canonical E1 evidence report")
    parser.add_argument("--json", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    with open(args.json, "r", encoding="utf-8", errors="strict") as handle:
        data = promote_for_public_output(json.load(handle))
    write_text_atomic(args.out, render(data, validated=True))


if __name__ == "__main__":
    main()
