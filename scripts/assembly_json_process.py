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

args = parser.parse_args()

with open(args.infile, "r",encoding="utf-8") as jsonin, open(args.outfile,"w",newline='') as outcsv:
    data = json.load(jsonin)
    outcsvtbl = csv.writer(outcsv,dialect="unix",quoting=csv.QUOTE_MINIMAL)
    outcsvtbl.writerow(['ACCESSION','SPECIES','STRAIN','NCBI_TAXID','BIOPROJECT','ASM_LENGTH','N50','ASM_NAME'])
    rows = {}

    for assembly in data['reports']:
#        print(list(assembly.keys()))
        json_formatted_str = json.dumps(assembly, indent=2)
#        print(json_formatted_str)
        category = ''
        if 'assembly_category' in assembly['assembly_info']:
            category = assembly['assembly_info']['refseq_category']

        if category != 'representative genome':
            continue

        accession = assembly['assembly_info']['accession']
        assembly_name= assembly['assembly_info']['assembly_name']
#        assembly_name = re.sub(r',','',assembly_name)
#        assembly_name = re.sub(r'[\(\)\/]','_',assembly_name)
#        assembly_name = re.sub(r' _V','_V',assembly_name)
        #print(seen)

        bioprojects = set(assembly['assembly_info']['bioproject_accession'])
        for p in assembly['bioprojects']:
            bioprojects.add(p['accession'])
        species = assembly['assembly_info']['organism']["organism_name"]
        strain  = ""
        if "organism" in assembly:
            if 'infraspecific_names' in assembly['organism']:
                if 'strain' in assembly['organism']['infraspecific_names']:
                    strain = assembly['organism']['infraspecific_names']['strain']
#        if 'strain' in assembly['assembly']['org']:
#            strain  = assembly['assembly']['org']["strain"]
#        elif 'isolate' in  assembly['assembly']['org']:
#            strain  = assembly['assembly']['org']["isolate"]
#        strain = re.sub(r',\s+',';',strain)
        taxid   = assembly['assembly_info']['organism']['tax_id']
        rank = ""
#        if 'rank' in assembly['assembly']['org']:
#            rank    = assembly['assembly']['org']['rank']
#            if rank == "STRAIN":
#                taxid = assembly['assembly']['org']['parent_tax_id']
#                species = re.sub(' {}'.format(strain),'',species)
#        elif species == "Fusarium vanettenii 77-13-4" or species == "Leptosphaeria biglobosa 'brassicae' group":
#            taxid = assembly['assembly']['org']['parent_tax_id']
#            species = re.sub(' {}'.format(strain),'',species)
#        else:
#            print("no rank for {}".format(species))
        n50     = assembly['assembly_stats']['contig_n50']
        seqlength = assembly['assembly_stats']['total_sequence_length']
        if species in rows:
            if accession.startswith("GCF_"):
                rows[species] = [accession,species,strain,taxid,";".join(bioprojects),seqlength,n50,assembly_name]
        else:
            rows[species] = [accession,species,strain,taxid,";".join(sorted(bioprojects)),seqlength,n50,assembly_name]

    for species in sorted(rows.keys()):
        outcsvtbl.writerow(rows[species])
