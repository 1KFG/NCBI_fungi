#!/usr/bin/bash -l
#SBATCH -p short -N 1 -n 1 --mem 4gb --out logs/makedb.%a.log


module load miniconda3
DAT=lib/ncbi_accessions_taxonomy.csv

MAX=$(wc -l $DAT| awk '{print $1}')

for RUNID in $(seq $MAX)
do
  ./scripts/create_genome_files.py -n $RUNID --infile $DAT
done
