#!/usr/bin/bash
#SBATCH -p short ---mem 24gb -C xeon 

bash scripts/get_ncbi_datasets.sh
./scripts/assembly_json_process.py --infile lib/ncbi_accessions.json --outfile lib/ncbi_accessions.csv

perl scripts/make_taxonomy_table.pl lib/ncbi_accessions.csv > lib/ncbi_accessions_taxonomy.csv
