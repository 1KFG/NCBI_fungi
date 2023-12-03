#!/usr/bin/env python3
import json, csv,sys, re
import argparse
import hashlib
parser = argparse.ArgumentParser(description="NCBI Datasets Genomes Process.",
                                 epilog="Generate by running. ./datasets summary genome taxon fungi > ncbi_accessions.json")
parser.add_argument('--infile', dest='infile', default="ncbi_accessions.json",
                    help='NCBI JSON processed from https://www.ncbi.nlm.nih.gov/datasets/docs/command-line-assembly/ datasets')

parser.add_argument('--outfile',dest='outfile',default="ncbi_accessions.csv",
                    help="Output file for NCBI processing")

parser.add_argument('--verbose','-v',dest='verbose',default=False, action='store_true',
                    help="Verbose debugging output")

args = parser.parse_args()

with open(args.infile, "r",encoding="utf-8") as jsonin, open(args.outfile,"w",newline='') as outcsv:
    data = json.load(jsonin)
    outcsvtbl = csv.writer(outcsv,dialect="unix",quoting=csv.QUOTE_MINIMAL)
    outcsvtbl.writerow(['ACCESSION','SPECIES','STRAIN','NCBI_TAXID','BIOPROJECT','ASM_LENGTH','N50','ASM_NAME'])
    rows = {}

    for assembly in data['reports']:
        if args.verbose:
            json_formatted_str = json.dumps(assembly, indent=2)
            print(json_formatted_str)
        category = ''
        if 'refseq_category' in assembly['assembly_info']:
            category = assembly['assembly_info']['refseq_category']

        if category != 'representative genome':
            continue

        accession = assembly['accession']
        assembly_name= assembly['assembly_info']['assembly_name']

        bioprojects = set(assembly['assembly_info']['bioproject_accession'])
        if args.verbose:
            print (assembly['assembly_info']['bioproject_lineage'])
        for p in assembly['assembly_info']['bioproject_lineage']:
            for acc in p['bioprojects']:
                bioprojects.add(acc['accession'])
        species = assembly['organism']["organism_name"]
        if args.verbose:
            print(species)
        strain  = ""
        if "organism" in assembly:
            if 'infraspecific_names' in assembly['organism']:
                if 'strain' in assembly['organism']['infraspecific_names']:
                    strain = assembly['organism']['infraspecific_names']['strain']
                elif 'isolate' in assembly['organism']['infraspecific_names']:
                    strain = assembly['organism']['infraspecific_names']['isolate']
        strain = re.sub(r',\s+',';',strain)
        taxid   = assembly['organism']['tax_id']
        n50     = assembly['assembly_stats']['contig_n50']
        seqlength = assembly['assembly_stats']['total_sequence_length']
        if species in rows:
            if accession.startswith("GCF_"):
                rows[species] = [accession,species,strain,taxid,";".join(bioprojects),seqlength,n50,assembly_name]
        else:
            rows[species] = [accession,species,strain,taxid,";".join(sorted(bioprojects)),seqlength,n50,assembly_name]
        if args.verbose:
            print(rows[species])
    for species in sorted(rows.keys()):
        outcsvtbl.writerow(rows[species])
