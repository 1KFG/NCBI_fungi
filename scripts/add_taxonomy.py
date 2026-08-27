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
                    help='processed NCBI datasets file into simple accession set')
parser.add_argument('--outfile',dest='outfile',default="lib/ncbi_accessions_taxonomy.csv",
                    help="Output file for NCBI processing")
parser.add_argument('--taxonkitdir',default="tmp/taxa",help="Directory for the taxonkit DB folder")
parser.add_argument('--cpus','--cpu',default='4',help="number of CPUs to use")

parser.add_argument('-v','--verbose', default=False, action='store_true', help="Verbose mode")
parser.add_argument('--tmp', default="/scratch", help="Temp folder")
args = parser.parse_args()

infile = open(args.infile, 'r', newline='')
csvin = csv.reader(infile, delimiter=",")
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

def sanitize_name(name):
    """Replace characters unsafe in filenames and normalize biological name suffixes."""
    name = name.strip()
    name = re.sub(r'\s*\(nom\.\s*inval\.\)', '', name)
    # Unwrap NCBI's uncertain-placement brackets, e.g. "[Candida] argentea" -> "Candida argentea".
    # Only a single whitespace-free token inside the brackets is treated this way (a misapplied
    # genus name); brackets containing spaces fall through to the filename-safety substitution below.
    name = re.sub(r'\[([^\[\]\s]+)\]', r' \1 ', name)
    # ncbi_accessions.csv (produced by assembly_json_process.sanitize_name) has already
    # rewritten those same brackets to "_Candida_" by the time this script sees them, so
    # the bracket regex above never matches on that input; unwrap that form too, e.g.
    # "_Lipomyces_ oligophaga" -> "Lipomyces oligophaga".
    name = re.sub(r'(?:^|(?<=\s))_([^\s_]+)_(?=\s|$)', r' \1 ', name)
    name = re.sub(r'\(([^)]+)\)', r' \1 ', name)
    name = re.sub(r'[/\\|*?<>:()\[\];\r\n]', '_', name)
    name = re.sub(r'\s+', ' ', name).strip()
    name = re.sub(r'_+', '_', name).strip('_').strip()
    return name

i =0
msg = ''
csvout = csv.writer(open(args.outfile, 'w', newline=''), delimiter=",", lineterminator='\n')
csvout.writerow(newheader)
msg = []
rows = {}        # accession -> row
taxid_to_accs = {}  # taxid -> [accession, ...]
for inrow in csvin:
    # want to save a subset of cols but we could always just make this a mashup of the two sets too
    # for simplicity, not sure the reasoning for this TBH
    # ASM_FOLDER is the canonical filesystem-safe folder name produced once by
    # assembly_json_process.sanitize_folder_name(); carry it through verbatim as
    # ASM_ACCESSION so every script resolves the same on-disk path. Fall back to
    # ACCESSION_ASM_NAME for older CSVs that predate the ASM_FOLDER column.
    if 'ASM_FOLDER' in col2num:
        acc = inrow[col2num['ASM_FOLDER']]
    else:
        acc = sanitize_name(re.sub(r'\s+','_',inrow[col2num['ACCESSION']]+"_"+inrow[col2num['ASM_NAME']]))
    taxid = inrow[col2num["NCBI_TAXID"]].strip()
    row = [ acc,
            taxid,
            sanitize_name(inrow[col2num["SPECIES"]]),
            sanitize_name(inrow[col2num["STRAIN"]]),
    ]
    row.extend([""]*8)
    rows[acc] = row
    if taxid not in taxid_to_accs:
        taxid_to_accs[taxid] = []
        msg.append(taxid)
    taxid_to_accs[taxid].append(acc)

def run_taxonkit(subargs, input_lines):
    p = Popen([args.taxonkit,'--data-dir',args.taxonkitdir,'--threads',args.cpus]+subargs,
              stdout=PIPE, stdin=PIPE, stderr=PIPE)
    combined = "\n".join(input_lines)+"\n"
    (so,se) = p.communicate(input=combined.encode())
    return so, se

def parse_lineage(lineagestr):
    taxcols = {}
    for l in lineagestr.split(';'):
        if "__" not in l:
            continue
        (rank,name) = l.split("__",1)
        if rank in rankToName:
            taxcols[newoutcol2num[rankToName[rank]]] = sanitize_name(name)
    return taxcols

so, se = run_taxonkit(['reformat', '-I','1', '-P'], msg)
unresolved_taxids = []
if len(so) == 0:
    print("error no result for {}, error is {}".format(msg,se))
else:
    for str in so.decode().splitlines():
        taxrow = str.split("\t")
        ncbi_id = taxrow[0].strip()
        lineagestr = taxrow[1].strip() if len(taxrow) > 1 else ''
        if ncbi_id not in taxid_to_accs:
            print("cannot find {} in db of rows?".format(ncbi_id))
            continue
        taxcols = parse_lineage(lineagestr)
        if not taxcols:
            # taxid has no lineage (e.g. deleted/retired NCBI taxonomy node) -
            # fall back to resolving the leading (genus/family/order) word of
            # the submitted species name instead of leaving the row blank.
            unresolved_taxids.append(ncbi_id)
        for acc in taxid_to_accs[ncbi_id]:
            row = rows[acc]
            for colnum, name in taxcols.items():
                row[colnum] = name

if unresolved_taxids:
    fallback_name_to_taxids = {}
    for ncbi_id in unresolved_taxids:
        acc = taxid_to_accs[ncbi_id][0]
        species = rows[acc][newoutcol2num["SPECIES_IN"]]
        fallback_name = species.split()[0] if species else ''
        if not fallback_name:
            continue
        fallback_name_to_taxids.setdefault(fallback_name, []).append(ncbi_id)

    so, se = run_taxonkit(['name2taxid'], list(fallback_name_to_taxids.keys()))
    fallback_taxid_to_names = {}
    for str in so.decode().splitlines():
        cols = str.split("\t")
        if len(cols) < 2 or not cols[1].strip():
            continue
        fallback_taxid_to_names.setdefault(cols[1].strip(), []).append(cols[0].strip())

    if fallback_taxid_to_names:
        so, se = run_taxonkit(['reformat', '-I','1', '-P'], list(fallback_taxid_to_names.keys()))
        for str in so.decode().splitlines():
            taxrow = str.split("\t")
            fb_taxid = taxrow[0].strip()
            lineagestr = taxrow[1].strip() if len(taxrow) > 1 else ''
            taxcols = parse_lineage(lineagestr)
            if not taxcols or fb_taxid not in fallback_taxid_to_names:
                continue
            for fallback_name in fallback_taxid_to_names[fb_taxid]:
                for ncbi_id in fallback_name_to_taxids[fallback_name]:
                    for acc in taxid_to_accs[ncbi_id]:
                        row = rows[acc]
                        for colnum, name in taxcols.items():
                            row[colnum] = name

for row in rows.values():
    csvout.writerow(row)
