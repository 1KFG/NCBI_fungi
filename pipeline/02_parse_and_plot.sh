#!/usr/bin/bash -l
#SBATCH -p short --mem 64gb -N 1 -n 64 --out logs/parse_genome_stats.log

module load parallel
module load miniconda3
conda activate ./bcbio-env
CPU=2
if [ ! -z $SLURM_CPUS_ON_NODE ]; then
	CPU=$SLURM_CPUS_ON_NODE
fi
./scripts/parse_genome_stats.py --headeronly --outfile assembly_stats.csv
LEN=$(wc -l lib/ncbi_accessions_taxonomy.csv | awk '{print $1}')

parallel -j $CPU ./scripts/parse_genome_stats.py --noheader --outfile - --index {} ::: $(seq 1 $LEN) >> assembly_stats.csv

# now plot
