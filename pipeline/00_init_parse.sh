#!/usr/bin/bash -l
#SBATCH -p short -N 1 -n 1 -c 8 --mem 8gb -C xeon --out logs/init_parse.log

CPU=8
bash scripts/get_ncbi_datasets.sh
bash scripts/get_taxonkit.sh
./scripts/assembly_json_process.py --infile lib/ncbi_accessions.json --outfile lib/ncbi_accessions.csv
echo "setting up taxonomy lookups"
./scripts/add_taxonomy.py --infile lib/ncbi_accessions.csv --outfile lib/ncbi_accessions_taxonomy.csv --cpu $CPU
