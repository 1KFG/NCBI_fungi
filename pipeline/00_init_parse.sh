#!/usr/bin/bash
#SBATCH -p short

bash scripts/get_ncbi_datasets.sh
./scripts/assembly_json_process.py --infile lib/ncbi_accessions.json --outfile lib/ncbi_accessions.csv
