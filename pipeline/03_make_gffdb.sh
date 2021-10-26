#!/usr/bin/bash -l
#SBATCH -p short -N 1 -n 1 --mem 1gb --out logs/makedb.%a.log -a 1

module load miniconda3
conda activate bcbio
DAT=lib/ncbi_accessions_taxonomy.csv

N=${SLURM_ARRAY_TASK_ID}
if [ -z $N ]; then
  N=$1
fi
if [ -z $N ]; then
  echo "cannot run without a number provided either cmdline or --array in sbatch"
  exit
fi

INTERVAL=5
NSTART=$(perl -e "printf('%d',1 + $INTERVAL * ($N - 1))")
NEND=$(perl -e "printf('%d',$INTERVAL * $N)")
MAX=$(wc -l $DAT| awk '{print $1}')
if [ "$NSTART" -gt "$MAX" ]; then
	echo "NSTART ($NSTART) > $MAX"
	exit
fi
if [ "$NEND" -gt "$MAX" ]; then
	NEND=$MAX
fi
echo "$NSTART -> $NEND"

for RUNID in $(seq $NSTART $NEND)
do
  time ./scripts/make_gff_db.py -n $RUNID --infile $DAT
done
