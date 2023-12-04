#!/usr/bin/bash -l
#SBATCH -p short --out logs/download.%a.log -a 1-11
module load aspera
DAT=lib/ncbi_accessions.csv
#ACCESSION,SPECIES,STRAIN,NCBI_TAXID,BIOPROJECT,N50,ASM_NAME
OUT=source/NCBI_ASM
N=${SLURM_ARRAY_TASK_ID}
if [ -z $N ]; then
  N=$1
fi
if [ -z $N ]; then
  echo "cannot run without a number provided either cmdline or --array in sbatch"
  exit
fi
INTERVAL=500
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
mkdir -p $OUT
IFS=,
tail -n +2 $DAT | sed -n ${NSTART},${NEND}p | while read ACCESSION SPECIES STRAIN TAXID BIOPROJECT LEN N50 ASMNAME
do
	#echo -e "ASMNAME is '$ASMNAME'"
	PRE=$(echo $ACCESSION | cut -d_ -f1 )
	ONE=$(echo $ACCESSION | cut -d_ -f2 | awk '{print substr($1,1,3)}')
	TWO=$(echo $ACCESSION | cut -d_ -f2 | awk '{print substr($1,4,3)}')
	THREE=$(echo $ACCESSION | cut -d_ -f2 | awk '{print substr($1,7,3)}')
	ASMNAME=$(echo $ASMNAME | perl -p -e 's/ /_/g; s/_+/_/;')
	echo "anonftp@ftp.ncbi.nlm.nih.gov:/genomes/all/$PRE/$ONE/$TWO/$THREE/${ACCESSION}_$ASMNAME/"
	if [ ! -d $OUT/${ACCESSION}_$ASMNAME ]; then
#		ascp -k1 -Tdr -l400M -i $ASPERAKEY --overwrite=diff anonftp@ftp.ncbi.nlm.nih.gov:/genomes/all/$PRE/$ONE/$TWO/$THREE/${ACCESSION}_$ASMNAME ./$OUT/
		rsync --exclude README.txt -a rsync://ftp.ncbi.nlm.nih.gov:/genomes/all/$PRE/$ONE/$TWO/$THREE/${ACCESSION}_$ASMNAME ./$OUT/
	fi
done
