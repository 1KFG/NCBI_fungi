#!/usr/bin/

if [ ! -f datasets ]; then
	curl -O https://ftp.ncbi.nlm.nih.gov/pub/datasets/command-line/LATEST/linux-amd64/dataformat
	curl -O https://ftp.ncbi.nlm.nih.gov/pub/datasets/command-line/LATEST/linux-amd64/datasets

	chmod +x dataformat datasets
fi
ACCESSION=ncbi_accessions.json
if [ ! -s ]; then
	./datasets summary genome taxon fungi > $ACCESSION
fi
