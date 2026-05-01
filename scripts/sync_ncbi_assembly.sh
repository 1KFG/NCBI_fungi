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

if [[ -d "$TARGET" && -f "${TARGET}/${ACCESSION}_${ASMNAME}_assembly_stats.txt" ]]; then
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
        # Download a URL to dest_dir/filename; tries aria2c, falls back to curl.
        ftp_get() {
            local url=$1 dir=$2 file=$3
            if aria2c --auto-file-renaming=false -x 2 -s 2 -c -q \
                    --check-certificate=false \
                    -d "$dir" -o "$file" "$url"; then
                return 0
            fi
            echo "aria2c failed for $file, retrying with curl..." >&2
            curl -fL --retry 3 --retry-delay 5 \
                -o "${dir}/${file}" "$url"
        }

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
	echo "target is $TARGET request is $BASE_URL/${ACCESSION}_${ASMNAME}_genomic.fna.gz"
        # Genome FASTA is required; fail and clean up if missing
        if ! ftp_get \
                "${BASE_URL}/${ACCESSION}_${ASMNAME}_genomic.fna.gz" \
                "$TARGET" \
                "${ACCESSION}_${ASMNAME}_genomic.fna.gz"; then
            rm -rf "$TARGET"
            echo "ERROR: failed to download genome for ${ACCESSION}" >&2
            exit 1
        fi

        # Optional files (annotation / metadata may not exist for all assemblies)
        for suffix in genomic.gff.gz \
                      protein.faa.gz \
                      cds_from_genomic.fna.gz \
		      assembly_report.txt \
                      sequence_report.jsonl \
                      assembly_stats.txt; do
            ftp_get \
                "${BASE_URL}/${ACCESSION}_${ASMNAME}_${suffix}" \
                "$TARGET" \
                "${ACCESSION}_${ASMNAME}_${suffix}" 2>/dev/null || true
        done
        ;;

    *)
        echo "Unknown download method: '$METHOD' (use 'datasets' or 'aria2c')" >&2
        exit 1
        ;;
esac
