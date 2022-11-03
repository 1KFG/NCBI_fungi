#!/usr/bin/bash -l
#SBATCH -p short --mem 24gb -C xeon

bash scripts/get_ncbi_datasets.sh
bash scripts/get_taxonkit.sh
./scripts/assembly_json_process.py --infile lib/ncbi_accessions.json --outfile lib/ncbi_accessions.csv
./scripts/add_taxonomy.py --infile lib/ncbi_accessions.csv --outfile lib/ncbi_accessions_taxonomy.csv
