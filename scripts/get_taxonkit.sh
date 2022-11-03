#!/usr/bin/bash -l

BINDIR=bin
mkdir -p $BINDIR
TAXONDIR=tmp/taxa # setting to current directory placement but you can also have this somewhere else

if [ ! -f $BINDIR/taxonkit ]; then
	curl -L https://github.com/shenwei356/taxonkit/releases/download/v0.13.0/taxonkit_linux_amd64.tar.gz | tar zxf - -C $BINDIR
fi

if [ ! -d $TAXONDIR ]; then
	mkdir -p $TAXONDIR
fi
if [ ! -f $TAXONDIR/node.dmp ]; then
	curl -L ftp://ftp.ncbi.nih.gov:/pub/taxonomy/taxdump.tar.gz | tar zxf - -C  $TAXONDIR
fi

