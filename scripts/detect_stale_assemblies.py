#!/usr/bin/env python3
"""Detect (and optionally remove) downloaded assembly folders that are no longer
present in the current accession list.

NCBI periodically suppresses an assembly or supersedes it with a new version, so
a fresh ``datasets summary`` no longer lists the old accession -- but the old
download still occupies disk under ``source/NCBI_ASM``. This finds those.

Matching is done on the **accession**, not the full folder name. Folder names are
``${ACCESSION}_${ASMFOLDER}`` but the trailing portion is a sanitized assembly
name whose exact form has changed over time (and older downloads may differ from
the current ASM_FOLDER). The accession (``GCA_########.v`` / ``GCF_########.v``)
is the stable unique key and always prefixes the folder, so we key on that to
avoid false positives. A folder is stale iff its accession is absent from the CSV.

By default this only *reports* stale folders. Pass --delete to remove them
(symlinks are unlinked; real directories are removed recursively).
"""
import argparse
import csv
import os
import re
import shutil
import sys
from pathlib import Path

ACCESSION_RE = re.compile(r"^(GC[AF]_[0-9]+\.[0-9]+)_")


def csv_accessions(csv_path):
    """Return the set of accessions in the current accession CSV."""
    accessions = set()
    with open(csv_path, newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            accessions.add(row["ACCESSION"].strip())
    return accessions


def folder_accession(name):
    """Extract the accession prefix from a folder name, or None if it doesn't parse."""
    m = ACCESSION_RE.match(name)
    return m.group(1) if m else None


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--infile", default="lib/ncbi_accessions.csv",
                   help="current accession CSV (default: lib/ncbi_accessions.csv)")
    p.add_argument("--asmdir", default="source/NCBI_ASM",
                   help="assembly download directory (default: source/NCBI_ASM)")
    p.add_argument("--delete", action="store_true",
                   help="remove stale folders (default: report only / dry run)")
    args = p.parse_args()

    csv_path = Path(args.infile)
    asm_dir = Path(args.asmdir)

    if not csv_path.is_file():
        sys.exit(f"ERROR: accession CSV not found: {csv_path}")
    if not asm_dir.is_dir():
        sys.exit(f"ERROR: assembly directory not found: {asm_dir}")

    accessions = csv_accessions(csv_path)

    folders = [d for d in sorted(asm_dir.iterdir())
               if d.is_dir() or d.is_symlink()]

    stale = []
    unparsed = []
    for d in folders:
        acc = folder_accession(d.name)
        if acc is None:
            unparsed.append(d)
        elif acc not in accessions:
            stale.append(d)

    print(f"{len(accessions)} accessions in {csv_path}", file=sys.stderr)
    print(f"{len(folders)} folders in {asm_dir}", file=sys.stderr)
    if unparsed:
        print(f"{len(unparsed)} folder(s) with unrecognized names (skipped):",
              file=sys.stderr)
        for d in unparsed:
            print(f"  ?\t{d}", file=sys.stderr)
    print(f"{len(stale)} stale folder(s): accession no longer in {csv_path.name}",
          file=sys.stderr)

    for d in stale:
        if args.delete:
            if d.is_symlink():
                os.unlink(d)
            else:
                shutil.rmtree(d)
            print(f"REMOVED\t{d}")
        else:
            print(f"STALE\t{d}")

    if stale and not args.delete:
        print("\nRe-run with --delete (or `make clean-stale`) to remove these.",
              file=sys.stderr)


if __name__ == "__main__":
    main()
