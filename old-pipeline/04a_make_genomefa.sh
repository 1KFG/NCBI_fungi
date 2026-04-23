#!/usr/bin/bash -l
#SBATCH -p short -N 1 -n 48 --mem 4gb --out logs/makedb.%A.log

CPU=2
if [ ! -z $SLURM_CPUS_ON_NODE ]; then
	CPU=$SLURM_CPUS_ON_NODE
fi

module load miniconda3
module load parallel
DAT=lib/ncbi_accessions_taxonomy.csv

MAX=$(wc -l $DAT | awk '{print $1}')
parallel -j $CPU ./scripts/create_genome_files.py -n {} --infile $DAT ::: $(seq $MAX)

