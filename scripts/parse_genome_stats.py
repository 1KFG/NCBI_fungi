#!/usr/bin/env python3

# inspired and based on https://github.com/pbfrandsen/insect_genome_assemblies/blob/master/extract_genome_stats.py

import sys
import csv
import os
import re
import argparse

def translator(s): return re.sub(r'[\s\-]', '_', s)


parser = argparse.ArgumentParser(description='Extract Genome Stats from NCBI downloads to make plot table',
                                 epilog="Generate input file by running perl scripts/make_taxonomy_table.pl > lin/ncbi_accessions_taxonomy.csv")
parser.add_argument('--asmdir', default="source/NCBI_ASM",
                    help="Folder where NCBI assemblies were downloaded after running pipeline/01_download.sh")

parser.add_argument('--infile', default="lib/ncbi_accessions_taxonomy.csv",
                    type=argparse.FileType('r'),
                    help='Input file with NCBI assembly accession folder names and Taxonomy')
parser.add_argument('--outfile', default="assembly_stats.csv",
                    type=argparse.FileType('w'),
                    help="Output file for summarizing the assembly statistics and taxonomy info")

args = parser.parse_args()
asm_info = ["Date","Genome coverage", "Assembly method","Sequencing technology", "Assembly type", "Assembly level"]
asm_stats = ["scaffold-N50", "scaffold-count", "total-length", "ungapped-length"]
revised_accessions = set()
accessions = set()

csvin = csv.reader(args.infile, delimiter=",")
csvout = csv.writer(args.outfile, delimiter=",")
header = next(csvin)

header.extend([translator(s) for s in asm_info])
header.extend([translator(s) for s in asm_stats])

csvout.writerow(header)

col2num = {}
i = 0
for col in header:
    col2num[col] = i
    i += 1

sumparse = re.compile(r'^\#\s+([^:]+):\s+(.+)')
for row in csvin:
    folder = os.path.join(args.asmdir, row[col2num["ASM_ACCESSION"]])
    statsfile = os.path.join(folder,"{}_assembly_stats.txt".format(row[col2num["ASM_ACCESSION"]]))

    parse_stats = 0
    this_asm_stats = {}
    this_asm_info = {}
    with open(statsfile,"rt",encoding="utf-8") as statsin:
        for line in statsin:
            if parse_stats:
                row = line.split()
                if ( row[0] == "all" and
                     row[1] == "all" and
                     row[2] == "all" and
                     row[3] == "all" ):
                      if row[4] in asm_stats:
                          this_asm_stats[row[4]] = int(row[5])
            else:
                if line.startswith("# unit-name	molecule-name"):
                    parse_stats = 1
                else:
                    m = sumparse.match(line)
                    if m:
                        this_asm_info[m.group(1)] = m.group(2)
    for c in asm_info:
        if c in this_asm_info:
            row.append(this_asm_info[c])
        else:
            row.append("")
    for c in asm_stats:
        if c in this_asm_stats:
            row.append(this_asm_stats[c])
        else:
            row.append("")
    csvout.writerow(row)

# with open(filename) as infile:
#     with open(outfilename, "a") as outfile:
#         csvfile = csv.reader(infile)
#         for count,line in enumerate(csvfile):
#             if count > 0:
#                 accession = line[2]
#                 # print("This is the accession: " + accession + "\n")
#                 assembly_level = line[4]
#                 # print("This is the assembly level: " + assembly_level + "\n")
#                 contig_n50 = line[6]
#                 # print("This is the contig N50: " + contig_n50 + "\n")
#                 display_name = line[7]
#                 extra_stuff = line[9].split(",")
#                 length = line[10]
#                 date = line[-1].strip()
#                 for item in extra_stuff:
#                     if "sci_name" in item:
#                         species_name = item.split(": ")[1]
#                 if accession in revised_accessions:
#                     accessions.add(accession)
#                     genome_number += 1
#                     if assembly_level == "Chromosome":
#                         chrom_genome_number += 1
#                     if int(contig_n50) > 999999:
#                         contig_n50_greater += 1
#                     outfile.write(taxon_name + "," + str(species_name) + "," +
#                         str(display_name) + "," + str(accession) + "," +
#                         str(contig_n50) + "," + str(assembly_level) + "," +
#                         str(length) + "," + str(date) + "\n")
