#!/usr/bin/env bash
# Download a single NCBI assembly.
# Usage: rsync_assembly.sh [--method datasets|aria2c] <ACCESSION> <ASM_NAME> <OUT_DIR>
#
# --method datasets  (default) uses ncbi-datasets-cli; reliable but can time out on large sets
# --method aria2c    fetches directly from https://ftp.ncbi.nih.gov/genomes via aria2c;
#                    files land as {ACCESSION}_{ASMNAME}_genomic.fna.gz etc., matching
#                    downstream script expectations
set -euo pipefail

METHOD=datasets

while [[ $# -gt 0 ]]; do
    case $1 in
        --method) METHOD=$2; shift 2 ;;
        --) shift; break ;;
        -*) echo "Unknown option: $1" >&2; exit 1 ;;
        *) break ;;
    esac
done

ACCESSION=$1
ASMNAME=$2
OUT=$3

ASMNAME=$(echo "$ASMNAME" | perl -pe 's/[, \/]+/_/g; s/_+/_/;')
TARGET="$OUT/${ACCESSION}_${ASMNAME}"

if [ -d "$TARGET" ]; then
    exit 0
fi

case "$METHOD" in
    datasets)
        TMPDIR=$(mktemp -d)
        trap 'rm -rf "$TMPDIR"' EXIT
        datasets download genome accession "$ACCESSION" \
            --filename "${TMPDIR}/download.zip" \
            --include genome,gff3,protein,cds,seq-report
        unzip -q "${TMPDIR}/download.zip" -d "$TMPDIR"
        mkdir -p "$TARGET"
        mv "${TMPDIR}/ncbi_dataset/data/${ACCESSION}/"* "$TARGET/"
        ;;

    aria2c)
        # Build the NCBI FTP path: genomes/all/{PRE}/{d1}/{d2}/{d3}/{ACCESSION}_{ASMNAME}/
        # The three path components come from the 9-digit numeric portion of the accession
        # (before the version dot), e.g. GCF_010015735.1 -> 010/015/735
        PRE=${ACCESSION%%_*}
        NUM=${ACCESSION#*_}
        NUM=${NUM%%.*}
        ONE=${NUM:0:3}
        TWO=${NUM:3:3}
        THREE=${NUM:6:3}
        BASE_URL="https://ftp.ncbi.nih.gov/genomes/all/${PRE}/${ONE}/${TWO}/${THREE}/${ACCESSION}_${ASMNAME}"

        mkdir -p "$TARGET"

        # Genome FASTA is required; fail and clean up if missing
        if ! aria2c --auto-file-renaming=false -x 4 -s 4 -q \
                -d "$TARGET" \
                "${BASE_URL}/${ACCESSION}_${ASMNAME}_genomic.fna.gz"; then
            rm -rf "$TARGET"
            echo "ERROR: failed to download genome for ${ACCESSION}" >&2
            exit 1
        fi

        # Optional files (annotation / metadata may not exist for all assemblies)
        for suffix in genomic.gff.gz \
                      protein.faa.gz \
                      cds_from_genomic.fna.gz \
                      sequence_report.jsonl.gz \
                      assembly_stats.txt; do
            aria2c --auto-file-renaming=false -x 4 -s 4 -q \
                -d "$TARGET" \
                "${BASE_URL}/${ACCESSION}_${ASMNAME}_${suffix}" 2>/dev/null || true
        done
        ;;

    *)
        echo "Unknown download method: '$METHOD' (use 'datasets' or 'aria2c')" >&2
        exit 1
        ;;
esac
