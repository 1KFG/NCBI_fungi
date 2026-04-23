#!/usr/bin/bash -l
#SBATCH --mem 24gb -p short -c 96 -n 1 -N 1
CPU=2
if [ ! -z $SLURM_CPUS_ON_NODE ]; then
    CPU=$SLURM_CPUS_ON_NODE
fi
#pushd Public_genomes
MAX=$(expr `wc -l lib/ncbi_accessions.csv | awk '{print $1}'` - 1)
parallel -j $CPU ./scripts/create_genome_files.py --index {} ::: $(seq $MAX)
