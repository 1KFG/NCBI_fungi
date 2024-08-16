#!/usr/bin/env python3

# inspired and based on https://github.com/pbfrandsen/insect_genome_assemblies/blob/master/extract_genome_stats.py

import sys
import csv
import os
import re, shutil
import argparse
#from BCBio import GFF
import gffutils
def translator(s): return re.sub(r'[\s\-]', '_', s)


parser = argparse.ArgumentParser(description='Extract Genome Stats from NCBI downloads to make plot table',
                                 epilog="Generate input file by running perl scripts/make_taxonomy_table.pl > lib/ncbi_accessions_taxonomy.csv")
parser.add_argument('--asmdir', default="source/NCBI_ASM",
                    help="Folder where NCBI assemblies were downloaded after running pipeline/01_download.sh")

parser.add_argument('--infile', default="lib/ncbi_accessions_taxonomy.csv",
                    type=argparse.FileType('r'),
                    help='Input file with NCBI assembly accession folder names and Taxonomy')
parser.add_argument('--outfile', default="assembly_stats.csv",
                    type=argparse.FileType('w'),
                    help="Output file for summarizing the assembly statistics and taxonomy info")
parser.add_argument('--force', default=False, action='store_true', help="Force rebuild index")
parser.add_argument('-v','--verbose', default=False, action='store_true', help="Verbose mode")
parser.add_argument('-n', '--index', default=1, help="Index of line to process")
parser.add_argument('--headeronly', default=False, action='store_true', help="Only Print Header")
parser.add_argument('--noheader', default=False, action='store_true', help="Only Print Header")
parser.add_argument('--tmp', default="/scratch", help="Temp folder")
args = parser.parse_args()

args.index = int(args.index)
asm_info = ["Date","Genome coverage", "Assembly method","Sequencing technology", "Assembly type", "Assembly level"]
asm_stats = ["scaffold-N50", "scaffold-count", "total-length"]
gene_stats = ["gene_count","gene_length_mean","exon_count","exon_length_mean","CDS_count","CDS_length_mean","intron_count","intron_length_mean"]

revised_accessions = set()
accessions = set()

csvin = csv.reader(args.infile, delimiter=",")
csvout = csv.writer(args.outfile, delimiter=",")
header = next(csvin)


header.extend([translator(s) for s in asm_info])
header.extend([translator(s) for s in asm_stats])
header.extend([translator(s) for s in gene_stats])
if not args.noheader:
    csvout.writerow(header)

if args.headeronly:
    exit()

col2num = {}
i = 0
for col in header:
    col2num[col] = i
    i += 1

sumparse = re.compile(r'^\#\s+([^:]+):\s+(.+)')
i = 1

for inrow in csvin:
    if i != args.index:
        i += 1
        continue
    folder = os.path.join(args.asmdir, inrow[col2num["ASM_ACCESSION"]])
    statsfile = os.path.join(folder,"{}_assembly_stats.txt".format(inrow[col2num["ASM_ACCESSION"]]))
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
    gff_file = os.path.join(folder,"{}_genomic.gff.gz".format(inrow[col2num["ASM_ACCESSION"]]))
    db_file  = os.path.join(folder,"{}_genomic.gff.db".format(inrow[col2num["ASM_ACCESSION"]]))
    this_gene_stats = {}
    for k in gene_stats:
        this_gene_stats[k] = 0

    if os.path.exists(gff_file):
        final_db_file = os.path.join(folder,"{}_genomic.gff.db".format(inrow[col2num["ASM_ACCESSION"]]))
        if not os.path.exists(final_db_file):
            tmpdb_file  = os.path.join(args.tmp,"{}_genomic.gff.db".format(inrow[col2num["ASM_ACCESSION"]]))
            if args.verbose:
                print("indexing {} as {}".format(gff_file,final_db_file))
            db = gffutils.create_db(gff_file, dbfn=tmpdb_file, force=args.force, keep_order=True, merge_strategy='merge', sort_attribute_values=True)
            shutil.move(tmpdb_file,final_db_file)

        db = gffutils.FeatureDB(final_db_file)

        this_gene_stats['gene_count'] = db.count_features_of_type('gene')
        this_gene_stats['exon_count'] = db.count_features_of_type('exon')
        this_gene_stats['CDS_count'] = db.count_features_of_type('CDS')

        for gene in db.features_of_type('gene'):
            this_gene_stats['gene_length_mean'] += len(gene)
        for exon in db.features_of_type('exon'):
            this_gene_stats['exon_length_mean'] += len(exon)
        for cds in db.features_of_type('CDS'):
            this_gene_stats['CDS_length_mean'] += len(cds)

        for intron in db.create_introns():
            if intron.start > 0 and intron.end > 0:
                if intron.end < intron.start:
                    this_gene_stats['intron_length_mean'] += abs(intron.start - intron.end) + 1
                else:
                    this_gene_stats['intron_length_mean'] += len(intron)
                this_gene_stats['intron_count'] += 1

        if this_gene_stats['gene_count'] > 0:
            this_gene_stats['gene_length_mean'] /= this_gene_stats['gene_count']
        if this_gene_stats['exon_count'] > 0:
            this_gene_stats['exon_length_mean'] /= this_gene_stats['exon_count']
        if this_gene_stats['CDS_count'] > 0:
            this_gene_stats['CDS_length_mean'] /= this_gene_stats['CDS_count']
        if this_gene_stats['intron_count'] > 0:
            this_gene_stats['intron_length_mean'] /= this_gene_stats['intron_count']

    for c in asm_info:
        if c in this_asm_info:
            inrow.append(this_asm_info[c])
        else:
            inrow.append("")
    for c in asm_stats:
        if c in this_asm_stats:
            inrow.append(this_asm_stats[c])
        else:
            inrow.append("")
    for c in gene_stats:
        if c in this_gene_stats:
            inrow.append(this_gene_stats[c])
        else:
            inrow.append("")

    csvout.writerow(inrow)
    i += 1
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
