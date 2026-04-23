#!/usr/bin/bash -l
#SBATCH -p short -N 1 -n 1 --mem 1gb --out logs/makedb.%a.log


module load miniconda3
DAT=lib/ncbi_accessions_taxonomy.csv

for RUNID in $(grep -n Saccharomycotina $DAT | cut -d: -f1)
do
  ./scripts/create_genome_files.py -n $RUNID --infile $DAT --outfolder asm_Saccharomycotina
  echo $RUNID
done
