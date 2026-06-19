# NCBI fungal genome assemblies — download + summary statistics

Downloads NCBI fungal genome assemblies and computes summary statistics
(assembly N50, gene/exon/CDS/intron counts and lengths, GC content, softmasked
repeat percent) joined against NCBI taxonomy.

Summary-stats parsing is partially inspired by Frandsen et al
[doi:10.1101/2021.02.14.431146](https://doi.org/10.1101/2021.02.14.431146) and
code in [pbfrandsen/insect_genome_assemblies](https://github.com/pbfrandsen/insect_genome_assemblies).

## Environment

All dependencies are managed by **pixi** (`pixi.toml`): `python`, `biopython`,
`gffutils`, `ncbi-datasets-cli` (provides `datasets`/`dataformat`), `taxonkit`,
GNU `parallel`, `perl`, `rsync`, `make`, `bgzip`/`pigz`. No `module load` or
conda activation is needed.

Run any step with:

```bash
pixi run make <target>        # or: pixi shell, then make <target>
```

`make -j` is not used at the top level; each target fans out internally with
GNU `parallel`, so `CPU=N` controls parallelism (e.g. `make stats CPU=32`).

R scripts are deliberately **not** in the pixi env — use a system R install for
plotting.

SLURM is a thin outer layer: `make slurm-<target>` submits the equivalent
`make <target>` as a single `sbatch --wrap` job (no array jobs; `parallel`
inside the job does the sharding). Override the partition with `SLURM_PART=...`.

## Pipeline

Run in order; each target depends on the previous via Make dependencies:

1. `make init` — fetch the NCBI taxdump into `tmp/taxa/`.
2. `make lib/ncbi_accessions.csv` — `datasets summary genome taxon fungi` →
   `lib/ncbi_accessions.json`, then `scripts/assembly_json_process.py` flattens
   it to CSV.
3. `make lib/ncbi_accessions_taxonomy.csv` — `scripts/add_taxonomy.py` joins
   taxonomy via `taxonkit`.
4. `make download` — fans `scripts/sync_ncbi_assembly.sh` over the CSV rows with
   GNU parallel. `DOWNLOAD_METHOD=datasets` (default) downloads by accession;
   `DOWNLOAD_METHOD=aria2c` fetches directly from the NCBI FTP site.
5. `make compress` — `bgzip` the `.fna`/`.faa` and `pigz` the `.gff`/`.jsonl`
   files in `source/NCBI_ASM` (idempotent). Depends directly on `download`;
   filenames are already normalized at download time, so there is no separate
   fix-names step.
6. `make genomes` — `scripts/create_genome_files.py` materializes per-genome
   FASTA/GFF working directories.
7. `make stats` → `assembly_stats.csv` — header once via `--headeronly`, then
   `parse_genome_stats.py --noheader --index N` rows appended in parallel.
8. `make gffdb` — `scripts/make_gff_db.py` builds a gffutils SQLite DB per row.

Maintenance / reporting targets:

- `make detect-stale` / `make clean-stale` — report / delete `source/NCBI_ASM`
  folders whose accession is no longer in `lib/ncbi_accessions.csv` (assemblies
  that NCBI suppressed or superseded).
- `scripts/plot_taxonomic_diversity_growth.py` — plots taxonomic diversity of
  fungal genomes over time from `lib/ncbi_accessions.json` +
  `lib/ncbi_accessions_taxonomy.csv` (outputs CSV + PDF/PNG under `plots/`).

The legacy numbered `*.sh` scripts under `old-pipeline/` are kept for reference
only (they use `module load`/`conda activate` and SLURM array sharding) and are
no longer the entrypoint.

## Data layout

- `lib/ncbi_accessions*.{json,csv}` — dated snapshots of the `datasets summary
  genome taxon fungi` output. The un-suffixed `ncbi_accessions.csv` /
  `ncbi_accessions_taxonomy.csv` are the "current" inputs the pipeline reads.
- `source/NCBI_ASM/` — raw rsync'd NCBI assembly folders (not in git).
- `genomes/` — per-genome processed working dirs (not in git).
- `assembly_stats.csv` — main output table: accession + taxonomy columns +
  `asm_info` (Date, Genome_coverage, Assembly_method, Sequencing_technology,
  Assembly_type, Assembly_level) + `scaffold-N50`, `scaffold-count`,
  `total-length` + gene/exon/CDS/intron count+mean-length + `softmasked_percent`,
  `GC_percent`.

`.gitignore` uses an allow-list: everything is ignored except `README.md`,
`TODO.md`, `CLAUDE.md`, `.gitignore`, `Makefile`, `pixi.toml`, `pixi.lock`, and
the `lib/`, `logs/`, `old-pipeline/`, `plots/`, `scripts/` trees.

## Key scripts

- `scripts/assembly_json_process.py` — JSON → CSV flattener for NCBI `datasets`
  output. Columns: `ACCESSION,SPECIES,STRAIN,NCBI_TAXID,BIOPROJECT,ASM_LENGTH,
  N50,ASM_NAME,ASM_FOLDER`.
- `scripts/add_taxonomy.py` — parallel taxonomy lookup; the Makefile passes
  `--taxonkit taxonkit` so the pixi-provided binary is used. Copies `ASM_FOLDER`
  verbatim into the `ASM_ACCESSION` column used downstream to resolve paths.
- `scripts/sync_ncbi_assembly.sh` — single-accession download helper; args
  `<ACCESSION> <ASM_NAME> <ASM_FOLDER> <OUT_DIR>` with `--method datasets|aria2c`.
  Writes/normalizes every downloaded file to `${ASM_FOLDER}_<suffix>` at download
  time.
- `scripts/detect_stale_assemblies.py` — reports/deletes stale assembly folders;
  keys on the accession prefix, so it is immune to asm-name sanitization drift.
- `scripts/create_genome_files.py` — materializes per-genome working dirs.
- `scripts/parse_genome_stats.py` — per-accession stats extractor, driven by
  `--index` (1-based row in `ncbi_accessions_taxonomy.csv`); `--headeronly` /
  `--noheader` let `parallel` stream rows into one CSV.
- `scripts/make_gff_db.py` — builds the gffutils SQLite DB for a given row index.
- `scripts/plot_taxonomic_diversity_growth.py` — taxonomic-growth-over-time plot.
- `scripts/summary_plot_genomeStats2.R`, `summary_plot_genomeStats.R`,
  `genome_feature_stats.R` — R plotting (R is not in pixi).
- `scripts/make_taxonomy_table.pl` — alternative Perl taxonomy builder.

## Naming conventions

- Input CSV rows are addressed by **1-based line index** passed as `--index` /
  `-n`. The Makefile drives parallelism with `parallel -j $(CPU)` over
  `seq 1 $MAX`.
- **`ASM_FOLDER`** = `sanitize_folder_name("${ACCESSION}_${ASM_NAME}")` is the
  single source of truth for on-disk directory/file names. Anything outside
  `[A-Za-z0-9._-]` (e.g. `#`, spaces, commas, slashes, parens) becomes `_`, runs
  of `_` are collapsed, and leading/trailing `_` trimmed. `.` and `-` are kept
  (they appear in real accessions/asm names). `ASM_NAME` keeps NCBI's name (used
  only to build the aria2c FTP URL).
- **Name sanitization** (`sanitize_name` in `assembly_json_process.py`) is the
  centralized rule for biological `SPECIES`/`STRAIN` strings: it strips
  nomenclatural suffixes, turns brackets/parens into underscores, and replaces
  commas with `_`. For strains, `", "` between multiple strains is first
  converted to `;`; any remaining bare comma (e.g. `CRUB 1588,7`) then becomes
  `_`, so strain fields are never emitted quoted in the output CSV.
- When the same species+strain has multiple assemblies, RefSeq (`GCF_`) is
  preferred over GenBank (`GCA_`).
- `pixi run make <target>` is the canonical entrypoint; avoid re-introducing
  `module load` / `conda activate` in new scripts.
