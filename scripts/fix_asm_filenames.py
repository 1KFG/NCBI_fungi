#!/usr/bin/env python3
"""Fix naming of NCBI_ASM download directories.

PREFIX FIX: Files downloaded by `datasets` lack the directory-name prefix.
   Rename  DIRBASE/genomic.fna.gz  ->  DIRBASE/DIRBASE_genomic.fna.gz
   (and equivalent for gff, faa, cds, assembly_stats, sequence_report).

Folder names are now made filesystem-safe at download time via the ASM_FOLDER
column (sanitize_folder_name in assembly_json_process.py), so the old '#'->'_'
symlink workaround is no longer applied here. Pre-existing '#' symlinks from
earlier runs are harmless and left in place.
"""

import argparse
import os
import sys
from pathlib import Path

# Suffixes that should carry the directory-name prefix.
# Ordered longest-first so we don't accidentally double-match.
PREFIXED_SUFFIXES = [
    "cds_from_genomic.fna.gz",
    "cds_from_genomic.fna",
    "genomic.fna.gz",
    "genomic.fna",
    "genomic.gff.gz",
    "genomic.gff",
    "genomic.gtf.gz",
    "genomic.gtf",
    "protein.faa.gz",
    "protein.faa",
    "assembly_stats.txt",
    "sequence_report.jsonl.gz",
    "sequence_report.jsonl",
]


def fix_prefix(asmpath: Path, dry_run: bool) -> int:
    """Rename unprefixed files inside asmpath to carry the directory name."""
    dirbase = asmpath.name
    renamed = 0
    for suffix in PREFIXED_SUFFIXES:
        src = asmpath / suffix
        if not src.exists():
            continue
        dst = asmpath / f"{dirbase}_{suffix}"
        if dst.exists() or dst.is_symlink():
            # Already exists (either real file or symlink) — skip.
            continue
        print(f"  rename  {src.relative_to(asmpath.parent)} -> {dst.name}")
        if not dry_run:
            src.rename(dst)
        renamed += 1
    return renamed


def main():
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("asm_dir", help="Path to the NCBI_ASM directory")
    p.add_argument("--dry-run", action="store_true", help="Print actions without executing")
    args = p.parse_args()

    asm_dir = Path(args.asm_dir).resolve()
    if not asm_dir.is_dir():
        sys.exit(f"ERROR: {asm_dir} is not a directory")

    total_renamed = 0

    for entry in sorted(asm_dir.iterdir()):
        if not entry.is_dir():
            continue

        # Prefix fix: unprefixed files inside the dir
        n = fix_prefix(entry, args.dry_run)
        total_renamed += n

    print(
        f"\nDone: {total_renamed} file(s) renamed"
        + (" [dry-run]" if args.dry_run else "")
    )


if __name__ == "__main__":
    main()
