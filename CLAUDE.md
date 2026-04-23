# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

Downloads NCBI fungal genome assemblies and computes summary statistics (assembly N50, gene/exon/CDS/intron counts and lengths, GC content, softmasked repeat percent) joined against NCBI taxonomy. Inspired by Frandsen et al. (doi:10.1101/2021.02.14.431146) and `pbfrandsen/insect_genome_assemblies`.

## Execution environment

- **All dependencies are managed by pixi** (`pixi.toml`) — `python`, `biopython`, `gffutils`, `ncbi-datasets-cli` (provides `datasets`/`dataformat`), `taxonkit`, GNU `parallel`, `perl`, `rsync`, `make`. No `module load` or conda env activation is needed.
- Run pipeline steps via `pixi run make <target>` (or `pixi shell` then `make <target>`). `make -j` is not used at the top level; each target fans out internally via GNU `parallel` so `CPU=N` controls parallelism (e.g. `make stats CPU=32`).
- R scripts are deliberately **not** in the pixi env — use a system R install for plotting.
- SLURM is a thin outer layer: `make slurm-<target>` submits the equivalent `make <target>` as a single `sbatch --wrap` job. No array jobs; `parallel` inside the job does the sharding.

## Pipeline (Makefile targets)

Run in order; each depends on the previous via Make dependencies:

1. `make init` — fetches the NCBI taxdump into `tmp/taxa/` (taxonkit binary itself comes from pixi).
2. `make lib/ncbi_accessions.csv` — runs `datasets summary genome taxon fungi` → `lib/ncbi_accessions.json`, then `scripts/assembly_json_process.py` flattens it.
3. `make lib/ncbi_accessions_taxonomy.csv` — `scripts/add_taxonomy.py` joins taxonomy via `taxonkit`.
4. `make download` — fans `scripts/rsync_assembly.sh` over rows of `lib/ncbi_accessions.csv` with GNU parallel (expects columns: ACCESSION,SPECIES,STRAIN,NCBI_TAXID,BIOPROJECT,ASM_LENGTH,N50,ASM_NAME; uses `{1}` and `{8}`).
5. `make genomes` — `scripts/create_genome_files.py --index N` over all rows.
6. `make stats` → `assembly_stats.csv` — header once via `--headeronly`, then parallel `parse_genome_stats.py --noheader --index N` rows appended.
7. `make gffdb` — `scripts/make_gff_db.py -n N` over all rows.

The legacy numbered `*.sh` scripts under `old-pipeline/` are kept for reference only; they use `module load`/`conda activate` and SLURM array sharding and are no longer the entrypoint.

## Data layout

- `lib/ncbi_accessions*.{json,csv}` — dated snapshots of the NCBI `datasets summary genome taxon fungi` output. The un-suffixed `ncbi_accessions.csv` / `ncbi_accessions_taxonomy.csv` are the "current" inputs the pipeline reads.
- `source/NCBI_ASM/` — raw rsync'd NCBI assembly folders (not in git).
- `genomes/` — per-genome processed working dirs (not in git).
- `assembly_stats.csv` — main output table. CSV header: accession + taxonomy columns + `asm_info` (`Date`, `Genome_coverage`, `Assembly_method`, `Sequencing_technology`, `Assembly_type`, `Assembly_level`) + `scaffold-N50`, `scaffold-count`, `total-length` + gene/exon/CDS/intron count+mean-length + `softmasked_percent`, `GC_percent`.
- `.gitignore` uses an allow-list pattern: everything is ignored except `README.md`, `TODO.md`, `CLAUDE.md`, `.gitignore`, `Makefile`, `pixi.toml`, `pixi.lock`, and the `lib/`, `logs/`, `old-pipeline/`, `plots/`, `scripts/` trees. New tracked files must fall under those paths.

## Key scripts

- `scripts/assembly_json_process.py` — JSON → CSV flattener for NCBI `datasets` output.
- `scripts/add_taxonomy.py` — parallel taxonomy lookup; defaults to `bin/taxonkit` and `tmp/taxa` but the Makefile passes `--taxonkit taxonkit` so the pixi-provided binary on `PATH` is used.
- `scripts/parse_genome_stats.py` — per-accession stats extractor; driven by `--index` (1-based row in `ncbi_accessions_taxonomy.csv`). `--headeronly` / `--noheader` let `parallel` stream rows into one CSV.
- `scripts/create_genome_files.py` — materializes per-genome FASTA/GFF working directories.
- `scripts/make_gff_db.py` — builds gffutils SQLite DB for a given row index.
- `scripts/rsync_assembly.sh` — single-accession rsync helper used by `make download` (replaces the inline loop from the old `01a_download.sh`).
- `scripts/summary_plot_genomeStats2.R`, `summary_plot_genomeStats.R`, `genome_feature_stats.R` — R plotting (project also has `NCBI_fungi.Rproj`). R is not in pixi.
- `scripts/make_taxonomy_table.pl` — alternative Perl taxonomy builder referenced in `parse_genome_stats.py`'s help epilog.
- `scripts/get_ncbi_datasets.sh`, `scripts/get_taxonkit.sh` — legacy binary fetchers; obsolete now that pixi provides `datasets`/`dataformat`/`taxonkit`. `get_taxonkit.sh` still contains the correct taxdump-download logic, which `make init` reproduces.

## Conventions

- Input CSV rows are addressed by 1-based line index passed as `--index` / `-n`. The Makefile drives parallelism with `parallel -j $(CPU)` over `seq 1 $MAX` — there is no more `INTERVAL`-based sharding.
- Accession folder names are `${ACCESSION}_${ASMNAME}` with `ASMNAME` sanitized via `s/[, \/]+/_/g; s/_+/_/;` (implemented in `scripts/rsync_assembly.sh`).
- `pixi run make <target>` is the canonical way to invoke any step; avoid re-introducing `module load` or `conda activate` in new scripts.
