#!/usr/bin/bash -l

BINDIR=bin
mkdir -p $BINDIR

if [ ! -f $BINDIR/taxonkit ]; then
	curl -L https://github.com/shenwei356/taxonkit/releases/download/v0.13.0/taxonkit_linux_amd64.tar.gz | tar zxf - -C $BINDIR
fi

