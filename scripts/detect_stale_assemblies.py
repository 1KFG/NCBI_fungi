#!/usr/bin/env python3
"""Detect (and optionally remove) downloaded assembly folders that are no longer
present in the current accession list.

NCBI periodically suppresses an assembly or supersedes it with a new version, so
a fresh ``datasets summary`` no longer lists the old accession -- but the old
download still occupies disk under ``source/NCBI_ASM``. This finds those.

Matching is done on the **full sanitized folder name** (the ``ASM_FOLDER`` column,
= ``sanitize_folder_name("${ACCESSION}_${ASM_NAME}")``). A folder is stale iff its
name is not one of the current ``ASM_FOLDER`` values. This catches both:
  * suppressed/superseded accessions (the accession, and thus its folder, is gone)
  * folders whose sanitized name changed (e.g. a new asm-name-stripping rule
    produces a different ASM_FOLDER, leaving the old-named download orphaned --
    downstream scripts now look under the new name).

The CSV column is auto-detected: ``ASM_FOLDER`` (lib/ncbi_accessions.csv) or
``ASM_ACCESSION`` (lib/ncbi_accessions_taxonomy.csv, which copies ASM_FOLDER
verbatim).

By default this only *reports* stale folders. Pass --delete to remove them
(symlinks are unlinked; real directories are removed recursively).
"""
import argparse
import csv
import os
import shutil
import sys
from pathlib import Path

# CSV column holding the canonical sanitized folder name, in preference order.
FOLDER_COLUMNS = ("ASM_FOLDER", "ASM_ACCESSION")


def csv_folder_names(csv_path):
    """Return the set of current sanitized folder names from the accession CSV."""
    with open(csv_path, newline="") as fh:
        reader = csv.DictReader(fh)
        col = next((c for c in FOLDER_COLUMNS if c in (reader.fieldnames or [])),
                   None)
        if col is None:
            sys.exit(f"ERROR: {csv_path} has none of the expected folder-name "
                     f"columns {FOLDER_COLUMNS}; header is {reader.fieldnames}")
        return {row[col].strip() for row in reader}


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

    valid = csv_folder_names(csv_path)

    folders = [d for d in sorted(asm_dir.iterdir())
               if d.is_dir() or d.is_symlink()]

    stale = [d for d in folders if d.name not in valid]

    print(f"{len(valid)} folder names in {csv_path}", file=sys.stderr)
    print(f"{len(folders)} folders in {asm_dir}", file=sys.stderr)
    print(f"{len(stale)} stale folder(s): name not in {csv_path.name}",
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
