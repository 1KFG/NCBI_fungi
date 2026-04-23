# NCBI fungi download + summary stats pipeline.
# Run inside the pixi environment: `pixi run make <target>` or
# `pixi shell` then `make <target>`.

SHELL := /bin/bash
.ONESHELL:

CPU ?= 8

TAXONKIT_DIR   := tmp/taxa
ACCESSIONS_JSON := lib/ncbi_accessions.json
ACCESSIONS_CSV  := lib/ncbi_accessions.csv
TAXONOMY_CSV    := lib/ncbi_accessions_taxonomy.csv
ASM_DIR         := source/NCBI_ASM
STATS_CSV       := assembly_stats.csv

.PHONY: all help init download compress genomes stats gffdb clean \
        slurm-download slurm-compress slurm-stats slurm-gffdb slurm-genomes

all: $(STATS_CSV)

help:
	@echo "Targets:"
	@echo "  init          fetch taxonkit taxdump database"
	@echo "  download      rsync NCBI fungal assemblies into $(ASM_DIR)"
	@echo "  compress      bgzip all .fna and .gff and .faa files in $(ASM_DIR)"
	@echo "  genomes       build per-genome working directories"
	@echo "  stats         build $(STATS_CSV)"
	@echo "  gffdb         build gffutils SQLite databases"
	@echo "  slurm-<tgt>   submit <tgt> as a SLURM job"
	@echo ""
	@echo "Override CPU with e.g. 'make stats CPU=32'"

# ---------------------------------------------------------------------------
# Taxonomy data (binary is provided by pixi; only the taxdump is fetched here)
# ---------------------------------------------------------------------------
$(TAXONKIT_DIR)/nodes.dmp:
	mkdir -p $(TAXONKIT_DIR)
	curl -L ftp://ftp.ncbi.nih.gov/pub/taxonomy/taxdump.tar.gz \
	    | tar zxf - -C $(TAXONKIT_DIR)

init: $(TAXONKIT_DIR)/nodes.dmp

# ---------------------------------------------------------------------------
# Accession list -> flattened CSV -> taxonomy-joined CSV
# ---------------------------------------------------------------------------
$(ACCESSIONS_JSON):
	mkdir -p lib
	datasets summary genome taxon fungi > $@

$(ACCESSIONS_CSV): $(ACCESSIONS_JSON)
	scripts/assembly_json_process.py --all-categories --infile $< --outfile $@

$(TAXONOMY_CSV): $(ACCESSIONS_CSV) $(TAXONKIT_DIR)/nodes.dmp
	scripts/add_taxonomy.py --infile $< --outfile $@ \
	    --taxonkit taxonkit --taxonkitdir $(TAXONKIT_DIR) --cpu $(CPU)

# ---------------------------------------------------------------------------
# Download assemblies (GNU parallel over accession rows)
# ---------------------------------------------------------------------------
download: $(ACCESSIONS_CSV) $(TAXONOMY_CSV)
	mkdir -p $(ASM_DIR)
	tail -n +2 $(ACCESSIONS_CSV) \
	  | parallel -j $(CPU) --colsep ',' scripts/rsync_assembly.sh {1} {8} $(ASM_DIR)

# ---------------------------------------------------------------------------
# Compress downloaded .fna files with bgzip (idempotent: skips *.fna.gz)
# ---------------------------------------------------------------------------
compress: download
	find $(ASM_DIR) -name '*.fna' ! -name '*.fna.gz' -type f -print0 \
	  | parallel -j $(CPU) -0 bgzip -f {}
	find $(ASM_DIR) -name '*.faa' ! -name '*.faa.gz' -type f -print0 \
	  | parallel -j $(CPU) -0 bgzip -f {}
	find $(ASM_DIR) -name '*.gff' ! -name '*.gff.gz' -type f -print0 \
	  | parallel -j $(CPU) -0 pigz -f {}


slurm-compress:
	mkdir -p logs
	sbatch -p $(SLURM_PART) -N 1 -n 1 -c $(CPU) --mem 8gb \
	    --out logs/make-compress.%j.log -J compress \
	    --wrap "pixi run make compress CPU=$(CPU)"

# ---------------------------------------------------------------------------
# Per-genome working directories
# ---------------------------------------------------------------------------
genomes: $(TAXONOMY_CSV)
	MAX=$$(( $$(wc -l < $(TAXONOMY_CSV)) - 1 ))
	parallel -j $(CPU) scripts/create_genome_files.py --index {} ::: $$(seq 1 $$MAX)

# ---------------------------------------------------------------------------
# assembly_stats.csv: header once, then one row per accession in parallel
# ---------------------------------------------------------------------------
$(STATS_CSV): $(TAXONOMY_CSV)
	scripts/parse_genome_stats.py --headeronly --outfile $@
	LEN=$$(wc -l < $(TAXONOMY_CSV))
	parallel -j $(CPU) scripts/parse_genome_stats.py --noheader \
	    --outfile - --index {} ::: $$(seq 1 $$LEN) >> $@

stats: $(STATS_CSV)

# ---------------------------------------------------------------------------
# gffutils SQLite databases
# ---------------------------------------------------------------------------
gffdb: $(TAXONOMY_CSV)
	MAX=$$(wc -l < $(TAXONOMY_CSV))
	parallel -j $(CPU) scripts/make_gff_db.py -n {} --infile $(TAXONOMY_CSV) \
	    ::: $$(seq 1 $$MAX)

# ---------------------------------------------------------------------------
# SLURM wrappers: submit `make <target>` as a single job that fans out with -j
# ---------------------------------------------------------------------------
SLURM_PART ?= short
SLURM_LOG   = logs/make-$(1).%j.log

slurm-download:
	mkdir -p logs
	sbatch -p $(SLURM_PART) -N 1 -n 1 -c $(CPU) --mem 16gb \
	    --out logs/make-download.%j.log -J download \
	    --wrap "pixi run make download CPU=$(CPU)"

slurm-stats:
	mkdir -p logs
	sbatch -p $(SLURM_PART) -N 1 -n 1 -c $(CPU) --mem 64gb \
	    --out logs/make-stats.%j.log \
	    --wrap "pixi run make stats CPU=$(CPU)"

slurm-gffdb:
	mkdir -p logs
	sbatch -p $(SLURM_PART) -N 1 -n 1 -c $(CPU) --mem 8gb \
	    --out logs/make-gffdb.%j.log \
	    --wrap "pixi run make gffdb CPU=$(CPU)"

slurm-genomes:
	mkdir -p logs
	sbatch -p $(SLURM_PART) -N 1 -n 1 -c $(CPU) --mem 24gb \
	    --out logs/make-genomes.%j.log \
	    --wrap "pixi run make genomes CPU=$(CPU)"

clean:
	rm -f $(STATS_CSV)
