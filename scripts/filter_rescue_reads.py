#!/usr/bin/env python3
import sys
import csv
import argparse
from pathlib import Path

# Adiciona o diretório lib ao path para importar logging_utils
sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from logging_utils import log_fatal, log_info, log_warning, set_context


def main():
    parser = argparse.ArgumentParser(description="Filtra e classifica candidatos a nivel de reads resgatados")
    parser.add_argument("--blast-raw", required=True)
    parser.add_argument("--out-tsv", required=True)
    args = parser.parse_args()

    set_context(etapa="RESCUE_READS")

    raw_path = Path(args.blast_raw)
    out_path = Path(args.out_tsv)
    if raw_path.resolve() == out_path.resolve():
        log_fatal("arquivo de entrada e saida nao podem ser o mesmo", "Use um caminho de saida separado.")

    fieldnames = [
        "qseqid", "sseqid", "pident", "length", "evalue", "bitscore",
        "qlen", "aln_cov", "adj_identity", "evidence_class", "risk_note"
    ]

    best_hits = {} # qseqid -> best hit dict

    try:
        if raw_path.exists() and raw_path.stat().st_size > 0:
            with raw_path.open("r", encoding="utf-8", errors="strict") as fh:
                reader = csv.reader(fh, delimiter="\t")
                for row in reader:
                    if len(row) < 14:
                        continue
                    qseqid = row[0]
                    sseqid = row[1]
                    try:
                        pident = float(row[2])
                        length = int(float(row[3]))
                        evalue = float(row[10])
                        bitscore = float(row[11])
                        qlen = int(float(row[12]))
                    except ValueError:
                        continue

                    if qlen <= 0:
                        continue

                    # Criterios conservadores para sinal no nivel de leitura
                    # pident >= 90
                    # length >= 80 ou length >= 0.8 * qlen
                    # evalue <= 1e-5
                    if pident < 90.0:
                        continue
                    if evalue > 1e-5:
                        continue
                    if length < 80 and length < (0.8 * qlen):
                        continue

                    aln_cov = length / qlen if qlen > 0 else 0.0
                    adj_identity = pident * aln_cov

                    hit = {
                        "qseqid": qseqid,
                        "sseqid": sseqid,
                        "pident": f"{pident:.3f}",
                        "length": length,
                        "evalue": evalue,
                        "bitscore": bitscore,
                        "qlen": qlen,
                        "aln_cov": f"{aln_cov:.5f}",
                        "adj_identity": f"{adj_identity:.3f}",
                        "evidence_class": "READ_LEVEL_SIGNAL",
                        "risk_note": "sinal_de_leitura_sem_contig"
                    }

                    # Seleciona o melhor hit por read (qseqid) com maior bitscore
                    if qseqid not in best_hits or bitscore > best_hits[qseqid]["bitscore"]:
                        best_hits[qseqid] = hit
    except FileNotFoundError:
        log_fatal(f"Arquivo de entrada raw BLAST nao encontrado: {raw_path}", "Verifique a execucao do alinhamento BLAST no modo de resgate.")
    except Exception as exc:
        log_fatal(f"Erro ao ler arquivo raw BLAST {raw_path}: {exc}", "Inspecione o log do pipeline.")

    # Gravar saída
    try:
        with out_path.open("w", encoding="utf-8", newline="") as out_fh:
            writer = csv.DictWriter(out_fh, delimiter="\t", fieldnames=fieldnames, lineterminator="\n")
            writer.writeheader()
            for hit in sorted(best_hits.values(), key=lambda h: -h["bitscore"]):
                h_copy = dict(hit)
                h_copy["evalue"] = f"{hit['evalue']:.2e}"
                writer.writerow(h_copy)
    except Exception as exc:
        log_fatal(f"Erro ao gravar arquivo de candidatos resgatados {out_path}: {exc}", "Verifique as permissoes de escrita no diretorio results/blast/.")

    log_info(f"{len(best_hits)} leitura(s) candidatas resgatadas salvas com sucesso em {out_path}")

if __name__ == "__main__":
    main()
