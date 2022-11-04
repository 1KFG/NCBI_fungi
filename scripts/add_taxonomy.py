#!/usr/bin/env python3
import json, csv,sys, re
import argparse
from subprocess import Popen, PIPE, STDOUT

# todo -figure out how to get subphylum from taxonkit ...

rankToName = {# 'k': 'Kingdom', # don't need to save Kingdom
              'p': 'PHYLUM',
              's': 'SUBPHYLUM',
              'c': 'CLASS',
              'o': 'ORDER',
              'f': 'FAMILY',
              'g': 'GENUS',
              's': 'SPECIES' }

parser = argparse.ArgumentParser(description="Add Taxonomy Columns to genome accession set.",
                                 epilog="requires bin/taxonkit to be installed - see scripts/get_taxonkit.sh")
parser.add_argument('--taxonkit',default='bin/taxonkit',help='taxonkit tool')
parser.add_argument('--infile', dest='infile', default="lib/ncbi_accessions.csv",
                    type=argparse.FileType('r'),
                    help='processed NCBI datasets file into simple accession set')
parser.add_argument('--outfile',dest='outfile',default="lib/ncbi_accessions_taxonomy.csv",
                    type=argparse.FileType('w'),
                    help="Output file for NCBI processing")
parser.add_argument('--taxonkitdir',default="tmp/taxa",help="Directory for the taxonkit DB folder")
parser.add_argument('--cpus','--cpu',default='4',help="number of CPUs to use")

parser.add_argument('-v','--verbose', default=False, action='store_true', help="Verbose mode")
parser.add_argument('--tmp', default="/scratch", help="Temp folder")
args = parser.parse_args()

csvin = csv.reader(args.infile, delimiter=",")
header = next(csvin)

# should be ACCESSION,SPECIES,STRAIN,NCBI_TAXID,BIOPROJECT,ASM_LENGTH,N50,ASM_NAME
data = []
newheader = ["ASM_ACCESSION","NCBI_TAXID","SPECIES_IN","STRAIN",
             "PHYLUM","SUBPHYLUM","CLASS","SUBCLASS","ORDER","FAMILY","GENUS","SPECIES"]
data.append(newheader)

col2num = {}
i = 0
for col in header:
    col2num[col] = i
    i += 1

newoutcol2num = {}
i = 0
for col in newheader:
    newoutcol2num[col] = i
    i += 1

sumparse = re.compile(r'^\#\s+([^:]+):\s+(.+)')

i =0
msg = ''
csvout = csv.writer(args.outfile,delimiter=",")
csvout.writerow(newheader)
msg = []
rows = {}
for inrow in csvin:
    # want to save a subset of cols but we could always just make this a mashup of the two sets too
    # for simplicity, not sure the reasoning for this TBH
    acc = re.sub(r'\s+','_',inrow[col2num['ACCESSION']]+"_"+inrow[col2num['ASM_NAME']])
    row = [ acc,
            inrow[col2num["NCBI_TAXID"]],
            inrow[col2num["SPECIES"]],
            inrow[col2num["STRAIN"]],
    ]
    row.extend([""]*8)
    rows[inrow[col2num["NCBI_TAXID"]]] = row
    msg.append( inrow[col2num["NCBI_TAXID"]] )

p = Popen([args.taxonkit,'--data-dir',args.taxonkitdir,'--threads',args.cpus,
           'reformat', '-I','1', '-P'], stdout=PIPE, stdin=PIPE, stderr=PIPE)
combined = "\n".join(msg)+"\n"
(so,se) = p.communicate(input=combined.encode())
if len(so) == 0:
    print("error no result for {}, error is {}".format(msg,se))
else:
    for str in so.decode().splitlines():
        taxrow = str.split("\t")
        ncbi_id = taxrow[0]
        lineagestr = taxrow[1]
        if ncbi_id not in rows:
            print("cannot find {} in db of rows?".format(ncbi_id))
            continue
        else:
            row = rows[ncbi_id]
            for l in lineagestr.split(';'):
                (rank,name) = l.split("__",2)
                if rank in rankToName:
                    colnum = newoutcol2num[rankToName[rank]]
                    row[colnum] = name
            csvout.writerow(row)
