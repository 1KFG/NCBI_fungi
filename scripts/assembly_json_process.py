#!/usr/bin/env python3
import json, csv,sys, re
import argparse
import hashlib
def sanitize_folder_name(name):
    """Canonical filesystem-safe assembly folder name.

    This is the SINGLE source of truth for turning an ``${ACCESSION}_${ASM_NAME}``
    string into the on-disk directory name. Anything outside [A-Za-z0-9._-] (most
    importantly '#', but also spaces, commas, slashes, parens, etc.) becomes '_';
    runs of '_' are collapsed and leading/trailing '_' trimmed. '.' and '-' are
    kept because they are filesystem-safe and appear in real accessions/asm names
    (e.g. GCA_026170115.1, HCTi.v1.0). Downstream paths are built from this value
    (carried as the ASM_FOLDER column and copied into ASM_ACCESSION by
    add_taxonomy.py), so changing the rule here changes it everywhere.
    """
    name = re.sub(r'[^A-Za-z0-9._-]+', '_', name)
    name = re.sub(r'_+', '_', name).strip('_')
    return name


# Sequence-file extensions and assembler/processing qualifiers that occasionally
# leak into NCBI's assembly_name (e.g. "MyGenome.fasta", "MyGenome.final.scaffolds",
# "MyGenome.nr.fa", "MyGenome.clean", "MyGenome.embl.gz"); stripped from both
# ASM_NAME and the folder name so neither is named like a file. The qualifier
# group repeats so chains like ".final.scaffolds" or ".contigs.clean" all go.
_SEQ_EXT_RE = re.compile(
    r'(?:\.(?:final|scaffolds|contigs|clean|CLC|nr))*'
    r'(?:\.(?:fasta|fas|fsa|fna|ffn|frn|mfa|fa|seq|embl))?'
    r'(?:\.(?:gz|bz2|zip|xz))?$',
    re.IGNORECASE)


def strip_seq_extension(name):
    """Drop a trailing sequence-file extension or assembler/processing qualifier
    (.fasta/.fna/.fa/.embl/..., .final.scaffolds, .contigs, .clean, .CLC, .nr,
    optionally .gz-style compressed) from an assembly name."""
    return _SEQ_EXT_RE.sub('', name)


# After stripping, a legitimate trailing dotted suffix should look like an
# assembly version: ".1" / ".10" (\.\d+) or ".v1.0" (\.v[\d.]+). Anything else
# (e.g. ".spades", ".v2_final") is probably a new file extension we don't yet
# strip, so warn so it can be added to _SEQ_EXT_RE.
_VERSION_RE = re.compile(r'(?:\.\d+|\.v[\d.]+)$', re.IGNORECASE)


def warn_if_unknown_extension(name, accession=""):
    """Emit a stderr warning when ``name`` ends in a dotted suffix that isn't a
    recognized version token, hinting that a new extension should be stripped."""
    if re.search(r'\.[^.]+$', name) and not _VERSION_RE.search(name):
        print("WARNING: {} assembly_name '{}' has an unrecognized trailing "
              "extension (not .<digits> or .v<digits>); consider adding it to "
              "_SEQ_EXT_RE".format(accession or '?', name), file=sys.stderr)


def sanitize_name(name):
    """Normalize biological names: remove nomenclatural suffixes, replace brackets/parens with underscores, and replace commas with underscores."""
    name = name.strip()
    name = re.sub(r'\s*\(nom\.\s*inval\.\)', '', name)
    name = re.sub(r'\[([^\]]*)\]', r'_\1_', name)
    name = re.sub(r'\(([^)]+)\)', r' \1 ', name)
    name = re.sub(r'\/','-', name)
    # replace any remaining commas (e.g. "CRUB 1588,7") so they don't end up
    # quoted in the output CSV; ", " between multiple strains is converted to
    # ";" before this is called.
    name = re.sub(r',', '_', name)
    name = re.sub(r'\s+', ' ', name).strip()
    name = re.sub(r'_+', '_', name)
    return name
#.strip('_')

parser = argparse.ArgumentParser(description="NCBI Datasets Genomes Process.",
                                 epilog="Generate by running. ./datasets summary genome taxon fungi > ncbi_accessions.json")
parser.add_argument('--infile', dest='infile', default="ncbi_accessions.json",
                    help='NCBI JSON processed from https://www.ncbi.nlm.nih.gov/datasets/docs/command-line-assembly/ datasets')

parser.add_argument('--outfile',dest='outfile',default="ncbi_accessions.csv",
                    help="Output file for NCBI processing")

parser.add_argument('--verbose','-v',dest='verbose',default=False, action='store_true',
                    help="Verbose debugging output")

parser.add_argument('--all-categories', dest='all_categories', default=False, action='store_true',
                    help="Include all assemblies regardless of refseq_category (default: reference genome only)")

args = parser.parse_args()

with open(args.infile, "r",encoding="utf-8") as jsonin, open(args.outfile,"w",newline='') as outcsv:
    data = json.load(jsonin)
    outcsvtbl = csv.writer(outcsv,dialect="unix",quoting=csv.QUOTE_MINIMAL)
    outcsvtbl.writerow(['ACCESSION','SPECIES','STRAIN','NCBI_TAXID','BIOPROJECT','ASM_LENGTH','N50','ASM_NAME','ASM_FOLDER'])
    rows = {}

    for assembly in data['reports']:
        if args.verbose:
            json_formatted_str = json.dumps(assembly, indent=2)
            print(json_formatted_str)
        category = ''
        if 'refseq_category' in assembly['assembly_info']:
            category = assembly['assembly_info']['refseq_category']

        if not args.all_categories and category != 'reference genome':
            continue

        accession=assembly['accession']
        assembly_name=assembly['assembly_info']['assembly_name']
        # normalize whitespace / commas / slashes / underscores to single _
        assembly_name=re.sub(r'[\s,/_\\]+','_',assembly_name.strip())
        assembly_name=re.sub(r'[()]+','_',assembly_name)
        assembly_name=re.sub(r'_+','_',assembly_name).strip('_')
        # drop trailing sequence/assembler file extensions (e.g.
        # ".final.scaffolds", ".fasta") from ASM_NAME itself, then warn (only
        # with --verbose) if a non-version-like suffix remains (likely a new
        # extension to strip)
        assembly_name=strip_seq_extension(assembly_name)
        if args.verbose:
            warn_if_unknown_extension(assembly_name, accession)

        bioprojects = set()
        bioprojects.add(assembly['assembly_info']['bioproject_accession'])
        if args.verbose:
            print (assembly['assembly_info']['bioproject_lineage'])
        for p in assembly['assembly_info']['bioproject_lineage']:
            for acc in p['bioprojects']:
                bioprojects.add(acc['accession'])
        species = sanitize_name(assembly['organism']["organism_name"])
        if args.verbose:
            print(species)
        strain = ""
        infra = assembly['organism'].get('infraspecific_names', {})
        if 'strain' in infra:
            strain = infra['strain']
        elif 'isolate' in infra:
            strain = infra['isolate']
        strain = sanitize_name(re.sub(r',\s+', ';', strain))
        strain = re.sub(r'\s*\(\s*$', '', strain).strip()
        taxid     = assembly['organism']['tax_id']
        n50       = assembly['assembly_stats']['scaffold_n50']
        seqlength = int(assembly['assembly_stats']['total_sequence_length'])

        # ASM_NAME keeps NCBI's (lightly normalized) name; ASM_FOLDER is the
        # filesystem-safe directory name used for every on-disk path. Strip any
        # trailing sequence-file extension so the folder isn't named like a file.
        asm_folder = sanitize_folder_name(
            "{}_{}".format(accession, strip_seq_extension(assembly_name)))
        row = [accession, species, strain, taxid,
               ";".join(sorted(bioprojects)), seqlength, n50, assembly_name, asm_folder]
        # prefer GCF_ (RefSeq) over GCA_ when the same species+strain has multiple assemblies
        key = (species, strain)
        prev = rows.get(key)
        if prev is None or (accession.startswith("GCF_") and not prev[0].startswith("GCF_")):
            rows[key] = row
        if args.verbose:
            print(rows[key])
    for key in sorted(rows.keys()):
        outcsvtbl.writerow(rows[key])
