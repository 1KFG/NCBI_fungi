#!/usr/bin/

BINDIR=bin
mkdir -p $BINDIR

if [ ! -f $BINDIR/datasets ]; then
	curl -o $BINDIR/dataformat https://ftp.ncbi.nlm.nih.gov/pub/datasets/command-line/LATEST/linux-amd64/dataformat
	curl -o $BINDIR/datasets https://ftp.ncbi.nlm.nih.gov/pub/datasets/command-line/LATEST/linux-amd64/datasets

	chmod +x dataformat datasets
fi
ACCESSION=lib/ncbi_accessions.json

if [ ! -s ]; then
	$BINDIR/datasets summary genome taxon fungi > $ACCESSION
fi
