#!/usr/bin/env python3
"""Fix two naming issues in NCBI_ASM download directories.

1. PREFIX FIX: Files downloaded by `datasets` lack the directory-name prefix.
   Rename  DIRBASE/genomic.fna.gz  ->  DIRBASE/DIRBASE_genomic.fna.gz
   (and equivalent for gff, faa, cds, assembly_stats, sequence_report).

2. HASH FIX: Directory or file names containing '#' get a symlink with '#'->'_'.
   Original path is kept; symlink is created at the sanitized path.
   e.g.  Rep1-bas4#11/  ->  symlink Rep1-bas4_11/ -> Rep1-bas4#11/
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


def make_hash_symlink(original: Path, dry_run: bool) -> bool:
    """Create a symlink at the '#'->'_' sanitized path pointing to original."""
    safe_name = original.name.replace("#", "_")
    if safe_name == original.name:
        return False
    link = original.parent / safe_name
    if link.exists() or link.is_symlink():
        return False
    print(f"  symlink {link.relative_to(original.parent.parent)} -> {original.name}")
    if not dry_run:
        link.symlink_to(original.name)
    return True


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
    total_symlinked = 0

    for entry in sorted(asm_dir.iterdir()):
        if not entry.is_dir():
            continue

        # Hash fix: directory itself
        if "#" in entry.name:
            if make_hash_symlink(entry, args.dry_run):
                total_symlinked += 1

        # Prefix fix: unprefixed files inside the dir
        n = fix_prefix(entry, args.dry_run)
        total_renamed += n

        # Hash fix: files inside the dir
        for fentry in sorted(entry.iterdir()):
            if "#" in fentry.name:
                if make_hash_symlink(fentry, args.dry_run):
                    total_symlinked += 1

    print(
        f"\nDone: {total_renamed} file(s) renamed, {total_symlinked} symlink(s) created"
        + (" [dry-run]" if args.dry_run else "")
    )


if __name__ == "__main__":
    main()
