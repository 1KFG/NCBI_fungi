#!/usr/bin/env python3

# inspired and based on https://github.com/pbfrandsen/insect_genome_assemblies/blob/master/extract_genome_stats.py

import sys
import gzip, shutil, re, os, csv
import argparse

def translator(s): return re.sub(r'[\s\-]', '_', s)
genomeExtension = "{}_genomic.fna.gz"
dir_type = ['DNA','CDS','pep']
parser = argparse.ArgumentParser(description='Create genome assembly files named by species and strain',
                                 epilog="Generate input file by running perl scripts/make_taxonomy_table.pl > lin/ncbi_accessions_taxonomy.csv")
parser.add_argument('--asmdir', default="source/NCBI_ASM",
                    help="Folder where NCBI assemblies were downloaded after running pipeline/01_download.sh")

parser.add_argument('--infile', default="lib/ncbi_accessions_taxonomy.csv",
                    type=argparse.FileType('r'),
                    help='Input file with NCBI assembly accession folder names and Taxonomy')
parser.add_argument('--outfolder', default="assemblies",
                    help="Output folder of assemblies")
parser.add_argument('-n', '--index', default=1, help="Index of line to process to allow parallelization")
parser.add_argument('--force', default=False, action='store_true', help="Force remake file")
parser.add_argument('-v','--verbose', default=False, action='store_true', help="Verbose mode")
parser.add_argument('--tmp', default="/scratch", help="Temp folder")
args = parser.parse_args()

args.index = int(args.index)

if not os.path.exists(args.outfolder):
    os.mkdir(args.outfolder)
for t in dir_type:
    if not os.path.exists(os.path.join(args.outfolder,t)):
        os.mkdir(os.path.join(args.outfolder,t))

csvin = csv.reader(args.infile, delimiter=",")
header = next(csvin)

col2num = {}
i = 0
for col in header:
    col2num[col] = i
    i += 1

sumparse = re.compile(r'^\#\s+([^:]+):\s+(.+)')
i = 1

for inrow in csvin:
    i += 1 # line 1 is the header so we add before checking value
    if i != args.index:
        continue
    folder = os.path.join(args.asmdir, inrow[col2num["ASM_ACCESSION"]])
    fasta_file = os.path.join(folder,genomeExtension.format(inrow[col2num["ASM_ACCESSION"]]))
    species_info = ""
    if len(inrow) < col2num["SPECIES"]:
        print("inrow doesn't have species column {}".format(inrow))
        species_info=inrow[col2num["SPECIES_IN"]]
    else:
        species_info=inrow[col2num["SPECIES"]]
    species = re.sub(r'[\[\]\(\)]','',species_info)
    species = re.sub(r'\s+','_',species)
    fname = "{}.dna.fasta".format(species)
    outfasta   = os.path.join(args.outfolder,'DNA',fname)
    if os.path.exists(outfasta) and not args.force:
        if args.verbose:
            print("Skipping {} as {} already exists".format(inrow[col2num["SPECIES"]],outfasta))
        continue

    if os.path.exists(fasta_file):
        with gzip.open(fasta_file,'rb') as fhin, open(outfasta,"wb") as fhout:
            shutil.copyfileobj(fhin, fhout)

    else:
        print("No FASTA file for {} as {}".format(species,fasta_file))
    break
