# Gene-In

![Version](https://img.shields.io/badge/version-2.0.0--alpha.2-blue)
![Status](https://img.shields.io/badge/status-shadow__mode-yellow)
![License](https://img.shields.io/badge/license-limited%20use-lightgrey)

**Gene-In** is a structured bioinformatics pipeline for analyzing, recovering, and prioritizing short viral fragments in high-throughput sequencing data from clinical or complex metagenomic samples with low viral load. The PTV/picornavirus profiles are historical examples and do not limit which viruses can be analyzed.

*Leia isto em [português](README.md).*

---

## Contents

1. [Key Features](#1-key-features)
2. [Who is it for?](#2-who-is-it-for)
3. [What it explicitly is NOT and does NOT do](#3-what-it-explicitly-is-not-and-does-not-do)
4. [Validation status](#4-validation-status)
5. [Installation and Quick Start](#5-installation-and-quick-start)
6. [How to interpret the output](#6-how-to-interpret-the-output)
7. [Repository structure](#7-repository-structure)
8. [Citing the software](#8-citing-the-software)
9. [License](#9-license)

---

## 1. Key Features

*   **Adjusted Identity:** Statistical algorithm that computes adjusted sequence identity (`adj_identity`), mitigating the bias of very short, high-identity alignments.
*   **Public evidence contract:** `E1 | E2 | E3 | NOT_EVALUABLE`, with `E2/E3` blocked in version `2.0.0-alpha.2` and E4 never emitted by the software. The five historical classes exist only as `legacy_label`, capped at E1.
*   **Read-level Rescue Mode:** Automatic activation of direct similarity search on individual reads (`READ_LEVEL_SIGNAL`) if assembly processes fail due to extremely low coverage.
*   **Interactive Dashboard:** Local Python web panel for visual parameterization, real-time pipeline run monitoring, and viewing of formatted scientific reports.

---

## 2. Who is it for?

Gene-In was designed for:
*   Researchers, biologists, and bioinformaticians investigating the virosphere in low-coverage NGS samples.
*   Research and surveillance teams that want to automate non-diagnostic computational screening, with human review and independent controls.

---

## 3. What it explicitly is NOT and does NOT do

> [!IMPORTANT]
> **Scientific and Scope Limitations:**
> *   **NOT clinical diagnostic software:** Gene-In's classification is purely bioinformatic, based on primary sequence homology. It does not provide clinical diagnostic reports of active viral infection.
> *   **E1 does not assert viral presence or absence:** reads, contigs, and historical classes record only homology candidates under the conditions evaluated.
> *   **Requires curation and scientific controls:** Results from very low biological coverage (as in `WEAK_RECOVERABLE`) may reflect laboratory cross-contamination, baseline sequencing noise, or conserved host sequences. Concurrent use of real negative controls and orthogonal experimental validation (e.g., RT-qPCR) is mandatory.
> *   **Reference database bias:** Detection sensitivity is tied to the diversity of sequences contained in the database configured for the pipeline. Incomplete or outdated databases can produce false negatives for highly divergent viral lineages.

---

## 4. Validation status

Version `2.0.0-alpha.2` is in `shadow_mode`. Unit and synthetic tests verify contracts and specific regressions, but do not demonstrate end-to-end scientific correctness. Exiting `shadow_mode` requires a frozen public/synthetic benchmark, real tool execution on Linux, complete controls, independent repetition, and a new audit with no blockers.

Results published by third parties do not replace this project's own frozen benchmark. Detailed status and limitations are documented in [`docs/science/validation-status.md`](docs/science/validation-status.md).

---

## 5. Installation and Quick Start

### Requirements
*   Linux system or Windows WSL2 environment (Ubuntu 22.04 LTS recommended).
*   Conda or Mamba package manager.

For installation on a new Windows machine or a computer with restricted permissions, also see [`docs/getting-started/guia-rapido-windows.md`](docs/getting-started/guia-rapido-windows.md) (Portuguese), which lists the administrator, WSL/Ubuntu, `sudo`, internet, and local port permissions that need to be enabled.

### Setup steps
1.  **Install dependencies via Conda:**
    ```bash
    conda env create -f environment.yml
    conda activate gene-in
    ```
2.  **Prepare a selected reference database (the `ptv` profile is just a historical example):**
    ```bash
    make db DB=ptv
    ```
3.  **Start the Web Dashboard:**
    ```bash
    python3 scripts/ux_dashboard.py
    ```
    Open in your browser: [http://localhost:8000](http://localhost:8000).

### Command-line execution (CLI)
For fine-grained control of the pipeline:
```bash
# 1. Add input FASTQs
make sample-add ID=teste_ptv R1=data/raw/demo_R1.fastq.gz R2=data/raw/demo_R2.fastq.gz

# 2. Run the main pipeline with the spades assembler
make pipeline SAMPLE=teste_ptv ASSEMBLER=spades

# 3. Generate a summary report
make report SAMPLE=teste_ptv
```

---

## 6. How to interpret the output

The canonical artifact is `sample_evidence.json`. A valid run with no candidates uses `analysis_outcome=NO_EVIDENCE_RECOVERED`, `evidence_level=E1`, an empty list, and an explicit caveat; this does not mean viral absence. Scientific failure or an invalid artifact uses `NOT_EVALUABLE`.

### Compatibility of runs prior to Alpha.2

Evidence V2 results generated before `2.0.0-alpha.2` do not retroactively satisfy the current contract. They remain preserved for audit purposes, but the dashboard identifies them as `LEGACY_INCOMPATIBLE`, with outcome `NOT_EVALUABLE`, and does not display their labels as Alpha.2 evidence. To obtain a valid result, the analysis must be rerun with the current version. There is no automatic promotion of these artifacts to E1.

The local runs `79f201633acf43b9a395c23725d2e0f0` and `8e612a9309d94d8eae8dca0d291af199` are historical Alpha.1 examples: their original files must be kept, and the analyses need to be rerun to produce the full Alpha.2 columns, evidence document, and manifest.

`results/blast/{SAMPLE}_labeled_hits.tsv` is a legacy compatibility artifact. Its labels are not public evidence levels and can never exceed E1:

| Evidence Class | Main Bioinformatic Criterion | Scientific Meaning | Recommended Action |
|---|---|---|---|
| `STRONG` | Length $\ge 80$ bp, pident $\ge 90\%$, adj_identity $\ge 70\%$, e-value $\le 10^{-10}$ | Strong evidence of viral homology. Long, well-aligned contig. | Prioritize contig for detailed phylogenetic analysis. |
| `STRONG_DIVERGENT` | Historical homology rule | `legacy_label`; does not call a variant or lineage. | Exploratory E1 review. |
| `MODERATE` | Length $50-79$ bp, pident $\ge 85\%$, adj_identity $\ge 60\%$, e-value $\le 10^{-5}$ | Intermediate evidence of viral homology. | Analyze taxonomic context and accessory similarities. |
| `WEAK_RECOVERABLE` | Length $20-49$ bp, pident $\ge 90\%$, bitscore $\ge 35$ | Very short but identical hits. Risk of false positive. | Requires careful manual review against general databases to rule out artifacts. |
| `REVIEW` | Does not meet the criteria above, but has residual signal. | Inconclusive or indeterminate signal. | Review raw alignments to rule out/confirm partial homology. |

---

## 7. Repository structure

```text
Gene-In/
+-- Makefile                   # Pipeline step automation
+-- README.md                  # This document, in Portuguese
+-- README.en.md                # This document, in English
+-- CHANGELOG.md               # Change history
+-- AGENTS.md                  # Engineering and review invariants
+-- LICENSE                    # Limited-use public license
+-- environment.yml            # Conda/Mamba environment definition
+-- config/
│   +-- picornavirus.env.example # Environment variable template
│   +-- targets.json           # Default viral accession definitions
+-- scripts/
│   +-- 00_import_sample.sh    # Local import script
│   +-- 20_run_pipeline.sh     # Main pipeline execution script
│   +-- ux_dashboard.py        # Local Python web dashboard
│   +-- tests/
│   │   +-- run_smoke_test.sh  # Synthetic smoke-test script
│   +-- lib/                   # Shared Python and Bash libraries
+-- docs/                      # Documentation (see docs/README.md for the full index)
│   +-- README.md              # Documentation index
│   +-- getting-started/       # Installation, usage, and troubleshooting
│   +-- architecture/          # Architecture, evidence contract, and terminology
│   +-- science/               # Scientific validation and technology radar
│   +-- quality/               # Review, release, and usability checklists
+-- data/
│   +-- raw/                   # Raw FASTQ reads (not versioned)
│   +-- ref/                   # Viral references in FASTA format
+-- results/                   # Generated results (reports and statistics)
```

See the [full documentation index](docs/README.md) for the list of all guides, architecture documents, scientific validation, and quality checklists.

> Most documentation under `docs/` is currently written in Portuguese (pt-BR). Contributions translating it to English are welcome.

---

## 8. Citing the software

If you use Gene-In in academic work, please cite this repository and the associated publication when available.

*Citation details: pending.*

---

## 9. License

This project is made available under a limited-use public license. Gene-In may be used for academic evaluation, educational use, non-commercial research, demonstration, and testing, as described in the [LICENSE](LICENSE) file. Redistribution, modification, resale, sublicensing, reverse engineering, or diagnostic/regulatory use are not permitted without prior written authorization.
