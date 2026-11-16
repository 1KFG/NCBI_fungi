#!/usr/bin/env python3
import json, csv,sys, re
import argparse
from subprocess import Popen, PIPE, STDOUT

# Ranks written to the output CSV, in the order taxonkit is asked for them.
#
# These are requested from `taxonkit reformat2`, which takes full rank names,
# rather than `taxonkit reformat`, whose canonical format offers only
# kingdom/phylum/class/order/family/genus/species -- it has no placeholder for
# subphylum or subclass at all.
#
# This replaces a single-letter {code: column} map that could not work: it
# carried both 's': 'SUBPHYLUM' and 's': 'SPECIES', and since a dict keeps the
# last value for a repeated key, the SUBPHYLUM entry was discarded when the
# module was loaded. SUBCLASS had no entry at all. Both columns were therefore
# emitted empty for every row, silently, for as long as the script has existed
# (0 of 24,523 rows populated in lib/ncbi_accessions_taxonomy_20261023.csv,
# against 100 % for PHYLUM and 99.1 % for CLASS). Parsing is now positional
# against this list, so no code can be ambiguous in that way again.
LINEAGE_RANKS = ['PHYLUM', 'SUBPHYLUM', 'CLASS', 'SUBCLASS',
                 'ORDER', 'FAMILY', 'GENUS', 'SPECIES']

# e.g. "{phylum};{subphylum};{class};{subclass};{order};{family};{genus};{species}"
TAXONKIT_FORMAT = ';'.join('{%s}' % rank.lower() for rank in LINEAGE_RANKS)

# Subcommand + flags shared by both reformat2 call sites below.
#   -I 1  : taxids are in field 1 of the input
#   -f    : explicit rank format (above); missing ranks come back empty, which
#           is what we want -- an absent subclass must not be filled in from a
#           neighbouring rank.
REFORMAT_ARGS = ['reformat2', '-I', '1', '-f', TAXONKIT_FORMAT]

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
    """Map a reformat2 lineage string onto output column numbers.

    Parsing is positional: reformat2 was asked for exactly LINEAGE_RANKS in
    order, so field i is rank i. Ranks the taxid does not define come back as
    empty strings and are left out, so the caller still sees an empty dict for
    a taxid with no lineage at all and can fall back as before.
    """
    taxcols = {}
    if not lineagestr:
        return taxcols
    parts = lineagestr.split(';')
    if len(parts) != len(LINEAGE_RANKS):
        # Not the shape we asked for -- refuse to guess which rank is which,
        # rather than silently writing names into the wrong columns.
        print("WARNING: expected {} lineage fields, got {}: {!r}".format(
            len(LINEAGE_RANKS), len(parts), lineagestr), file=sys.stderr)
        return taxcols
    for rank, name in zip(LINEAGE_RANKS, parts):
        name = name.strip()
        if name:
            taxcols[newoutcol2num[rank]] = sanitize_name(name)
    return taxcols

so, se = run_taxonkit(REFORMAT_ARGS, msg)
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
        so, se = run_taxonkit(REFORMAT_ARGS, list(fallback_taxid_to_names.keys()))
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
