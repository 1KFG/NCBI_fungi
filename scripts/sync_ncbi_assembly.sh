#!/usr/bin/env bash
# Download a single NCBI assembly.
# Usage: sync_ncbi_assembly.sh [--method datasets|aria2c] <ACCESSION> <ASM_NAME> <ASM_FOLDER> <OUT_DIR>
#
# ASM_NAME   : NCBI's (lightly normalized) assembly name; used ONLY to build the
#              remote NCBI FTP path for the aria2c method.
# ASM_FOLDER : the canonical filesystem-safe folder name (from the ASM_FOLDER
#              column / sanitize_folder_name); used for the local directory and
#              every local filename so paths never contain '#', spaces, etc.
#
# --method datasets  (default) uses ncbi-datasets-cli; reliable but can time out on large sets
# --method aria2c    fetches directly from https://ftp.ncbi.nih.gov/genomes via aria2c;
#                    files land as {ASM_FOLDER}_genomic.fna.gz etc., matching
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
ASMFOLDER=$3
OUT=$4

# Local directory + filenames use the precomputed, filesystem-safe ASM_FOLDER.
TARGET="$OUT/${ASMFOLDER}"

# Normalize the files a `datasets` download drops into ${TARGET} to the canonical
# ${ASMFOLDER}_${suffix} names downstream scripts expect. datasets emits the
# genome FASTA already prefixed with NCBI's own assembly name and everything else
# (gff/protein/cds/seq-report) bare, so rename all of them to OUR ASM_FOLDER
# prefix. (This replaces the old standalone scripts/fix_asm_filenames.py pass.)
normalize_filenames() {
    local suffix src dst
    # Bare files: exact name -> ASM_FOLDER-prefixed name.
    for suffix in genomic.fna genomic.gff protein.faa cds_from_genomic.fna \
                  sequence_report.jsonl assembly_stats.txt assembly_report.txt; do
        src="${TARGET}/${suffix}"
        dst="${TARGET}/${ASMFOLDER}_${suffix}"
        [[ -e "$src" && ! -e "$dst" ]] && mv "$src" "$dst"
    done
    # Genome FASTA usually arrives as ${ACCESSION}_<ncbi-name>_genomic.fna; rename
    # it to our prefix. Skip the cds file (it also ends in _genomic.fna) and skip
    # if it is already canonical.
    dst="${TARGET}/${ASMFOLDER}_genomic.fna"
    if [[ ! -e "$dst" && ! -e "${dst}.gz" ]]; then
        for src in "$TARGET"/*_genomic.fna; do
            [[ -e "$src" ]] || continue
            [[ "$src" == *cds_from_genomic.fna ]] && continue
            [[ "$src" == "$dst" ]] && break
            mv "$src" "$dst"
            break
        done
    fi
}

# Skip if already downloaded -- the prefixed genome FASTA is the reliable marker
# (present for both download methods, compressed or not).
if [[ -d "$TARGET" ]] && \
   { [[ -e "${TARGET}/${ASMFOLDER}_genomic.fna" ]] || [[ -e "${TARGET}/${ASMFOLDER}_genomic.fna.gz" ]]; }; then
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
        normalize_filenames
        ;;

    aria2c)
        # Download a URL to dest_dir/filename; tries aria2c, falls back to curl.
        ftp_get() {
            local url=$1 dir=$2 file=$3
	    if [ ! -f ${dir}/${file} ]; then
              if aria2c --auto-file-renaming=false -x 2 -s 2 -c -q \
                    -d "$dir" -o "$file" "$url"; then
                return 0
              fi
              echo "aria2c failed for $file, retrying with curl..." >&2
              curl -k -fL --retry 3 --retry-delay 5 \
                -o "${dir}/${file}" "$url"
	    fi	
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
        #BASE_URL="https://130.14.250.107/genomes/all/${PRE}/${ONE}/${TWO}/${THREE}/${ACCESSION}_${ASMNAME}"


        mkdir -p "$TARGET"
	echo "target is $TARGET request is $BASE_URL/${ACCESSION}_${ASMNAME}_genomic.fna.gz"
        # Remote files use NCBI's raw ${ACCESSION}_${ASMNAME} naming; local files
        # are saved with the filesystem-safe ${ASMFOLDER} prefix.
        # Genome FASTA is required; fail and clean up if missing
        if ! ftp_get \
                "${BASE_URL}/${ACCESSION}_${ASMNAME}_genomic.fna.gz" \
                "$TARGET" \
                "${ASMFOLDER}_genomic.fna.gz"; then
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
                "${ASMFOLDER}_${suffix}" 2>/dev/null || true
        done
        ;;

    *)
        echo "Unknown download method: '$METHOD' (use 'datasets' or 'aria2c')" >&2
        exit 1
        ;;
esac
