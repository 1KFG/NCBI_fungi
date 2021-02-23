#!/usr/bin/bash
#SBATCH -p short --out logs/download.%a.log
module load aspera
DAT=lib/ncbi_accessions.csv
#ACCESSION,SPECIES,STRAIN,NCBI_TAXID,BIOPROJECT,N50,ASM_NAME
OUT=source/NCBI_ASM
IFS=,
tail -n +2 $DAT | while read ACCESSION SPECIES STRAIN TAXID BIOPROJECT N50 ASMNAME
do
	ASMNAME=$(echo $ASMNAME | perl -p -e 's/ /_/g')
	echo "$OUT/$ACCESSION -> $OUT/${ACCESSION}_$ASMNAME"
	mv $OUT/$ACCESSION $OUT/${ACCESSION}_$ASMNAME
done
