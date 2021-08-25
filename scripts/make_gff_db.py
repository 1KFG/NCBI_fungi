#!/usr/bin/env python3

import sys
import csv
import os
import re, shutil
import argparse

#from BCBio import GFF
import gffutils
def translator(s): return re.sub(r'[\s\-]', '_', s)


parser = argparse.ArgumentParser(description='Create GFF db for parallel fast creation')
parser.add_argument('--asmdir', default="source/NCBI_ASM",
                    help="Folder where NCBI assemblies were downloaded after running pipeline/01_download.sh")

parser.add_argument('--infile', default="lib/ncbi_accessions_taxonomy.csv",
                    type=argparse.FileType('r'),
                    help='Input file with NCBI assembly accession folder names and Taxonomy')

parser.add_argument('--force', default=False, action='store_true', help="Force rebuild index")
parser.add_argument('-n', '--index', default=1, help="Index of line to process")

parser.add_argument('--tmp', default="/scratch", help="Temp folder")
args = parser.parse_args()
args.index = int(args.index)
csvin = csv.reader(args.infile, delimiter=",")
header = next(csvin)

col2num = {}
i = 0
for col in header:
    col2num[col] = i
    i += 1

i = 1
sumparse = re.compile(r'^\#\s+([^:]+):\s+(.+)')
for inrow in csvin:
    if i == args.index:
        folder = os.path.join(args.asmdir, inrow[col2num["ASM_ACCESSION"]])
        gff_file = os.path.join(folder,"{}_genomic.gff.gz".format(inrow[col2num["ASM_ACCESSION"]]))
        if os.path.exists(gff_file):
            final_db_file = os.path.join(folder,"{}_genomic.gff.db".format(inrow[col2num["ASM_ACCESSION"]]))
            if not os.path.exists(final_db_file):
                print("indexing {} as {}".format(gff_file,final_db_file))
                tmpdb_file  = os.path.join(args.tmp,"{}_genomic.gff.db".format(inrow[col2num["ASM_ACCESSION"]]))
                db = gffutils.create_db(gff_file, dbfn=tmpdb_file, force=args.force, keep_order=True, merge_strategy='merge', sort_attribute_values=True)
                shutil.move(tmpdb_file,final_db_file)
            else:
                print("already indexed {}, use --force to force creation".format(final_db_file))

        else:
            print("No gff file {}".format(gff_file))
        break
    i += 1
