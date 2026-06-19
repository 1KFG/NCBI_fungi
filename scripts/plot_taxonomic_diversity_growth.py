#!/usr/bin/env python3
"""Plot cumulative taxonomic diversity of NCBI fungal genomes over time.

Reads lib/ncbi_accessions.json for release dates and
lib/ncbi_accessions_taxonomy.csv for taxonomy, then produces a
multipanel PDF showing how genera, families, orders, and multi-strain
species accumulate by month.
"""

import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--json", default="lib/ncbi_accessions.json",
                   help="NCBI datasets JSON file")
    p.add_argument("--taxonomy", default="lib/ncbi_accessions_taxonomy.csv",
                   help="Taxonomy CSV (output of add_taxonomy.py)")
    p.add_argument("--outcsv", default="lib/taxonomic_diversity_by_month.csv",
                   help="Output summary CSV")
    p.add_argument("--outpdf", default="plots/taxonomic_diversity_growth.pdf",
                   help="Output PDF figure")
    p.add_argument("--outpng", default="plots/taxonomic_diversity_growth.png",
                   help="Output PNG figure")
    return p.parse_args()


def load_release_dates(json_path):
    """Return {bare_accession: 'YYYY-MM-DD'} from the JSON."""
    with open(json_path) as f:
        data = json.load(f)
    dates = {}
    for r in data["reports"]:
        acc = r["accession"]
        date = r["assembly_info"].get("release_date")
        if date:
            dates[acc] = date
    return dates


def load_taxonomy(csv_path):
    """Return {bare_accession: {GENUS, FAMILY, ORDER, SPECIES, STRAIN, ...}}."""
    acc_re = re.compile(r"(GC[AF]_\d+\.\d+)")
    tax = {}
    with open(csv_path) as f:
        for row in csv.DictReader(f):
            m = acc_re.match(row["ASM_ACCESSION"])
            if not m:
                continue
            tax[m.group(1)] = row
    return tax


def main():
    args = parse_args()

    dates = load_release_dates(args.json)
    taxonomy = load_taxonomy(args.taxonomy)

    matched = sorted(taxonomy.keys() & dates.keys())
    if not matched:
        sys.exit("No accessions matched between JSON and taxonomy CSV.")

    records = []
    for acc in matched:
        records.append({
            "accession": acc,
            "date": dates[acc],
            "month": dates[acc][:7],
            "genus": taxonomy[acc].get("GENUS", "").strip(),
            "family": taxonomy[acc].get("FAMILY", "").strip(),
            "order": taxonomy[acc].get("ORDER", "").strip(),
            "species": taxonomy[acc].get("SPECIES", "").strip(),
            "strain": taxonomy[acc].get("STRAIN", "").strip(),
        })

    records.sort(key=lambda r: r["date"])

    months = []
    cum_genera = []
    cum_families = []
    cum_orders = []
    cum_multistrain = []
    cum_species = []
    cum_assemblies = []

    seen_genera = set()
    seen_families = set()
    seen_orders = set()
    seen_species = set()
    species_count = defaultdict(int)
    n_assemblies = 0

    current_month = None
    for rec in records:
        m = rec["month"]
        if m != current_month:
            if current_month is not None:
                months.append(current_month)
                cum_genera.append(len(seen_genera))
                cum_families.append(len(seen_families))
                cum_orders.append(len(seen_orders))
                cum_species.append(len(seen_species))
                cum_multistrain.append(
                    sum(1 for c in species_count.values() if c > 1)
                )
                cum_assemblies.append(n_assemblies)
            current_month = m

        if rec["genus"]:
            seen_genera.add(rec["genus"])
        if rec["family"]:
            seen_families.add(rec["family"])
        if rec["order"]:
            seen_orders.add(rec["order"])
        if rec["species"]:
            seen_species.add(rec["species"])
            species_count[rec["species"]] += 1
        n_assemblies += 1

    if current_month is not None:
        months.append(current_month)
        cum_genera.append(len(seen_genera))
        cum_families.append(len(seen_families))
        cum_orders.append(len(seen_orders))
        cum_species.append(len(seen_species))
        cum_multistrain.append(
            sum(1 for c in species_count.values() if c > 1)
        )
        cum_assemblies.append(n_assemblies)

    month_dates = [datetime.strptime(m, "%Y-%m") for m in months]

    with open(args.outcsv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["month", "cumulative_assemblies", "cumulative_species",
                     "cumulative_genera", "cumulative_families",
                     "cumulative_orders", "species_with_multiple_strains"])
        for i, m in enumerate(months):
            w.writerow([m, cum_assemblies[i], cum_species[i],
                         cum_genera[i], cum_families[i],
                         cum_orders[i], cum_multistrain[i]])
    print(f"Wrote {args.outcsv} ({len(months)} months)")

    fig, axes = plt.subplots(2, 2, figsize=(14, 10), sharex=True)
    fig.suptitle("Cumulative Taxonomic Diversity of NCBI Fungal Genomes",
                 fontsize=14, fontweight="bold")

    color_order = "#2c7bb6"
    color_family = "#d7191c"
    color_genus = "#fdae61"
    color_multi = "#1a9641"

    panels = [
        (axes[0, 0], cum_orders, "Cumulative orders", "Orders", color_order),
        (axes[0, 1], cum_families, "Cumulative families", "Families", color_family),
        (axes[1, 0], cum_genera, "Cumulative genera", "Genera", color_genus),
        (axes[1, 1], cum_multistrain, "Species count",
         "Species with multiple strains", color_multi),
    ]

    for ax, ydata, ylabel, title, color in panels:
        ax.plot(month_dates, ydata, color=color, linewidth=1.5)
        ax.fill_between(month_dates, ydata, alpha=0.15, color=color)
        ax.set_ylabel(ylabel, color=color)
        ax.set_title(title)
        ax.grid(True, alpha=0.3)

        ax2 = ax.twinx()
        ax2.plot(month_dates, cum_assemblies, color="black", linewidth=1,
                 linestyle="-", alpha=0.7)
        ax2.set_ylabel("Cumulative assemblies", color="black", fontsize=8)
        ax2.tick_params(axis="y", labelsize=7, colors="black")

    for ax in axes.flat:
        ax.xaxis.set_major_locator(mdates.YearLocator(2))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        ax.tick_params(axis="x", rotation=45)

    final_month = months[-1]
    stats_text = (
        f"As of {final_month}:  "
        f"{cum_assemblies[-1]:,} assemblies  |  "
        f"{cum_species[-1]:,} species  |  "
        f"{cum_genera[-1]:,} genera  |  "
        f"{cum_families[-1]:,} families  |  "
        f"{cum_orders[-1]:,} orders  |  "
        f"{cum_multistrain[-1]:,} multi-strain species"
    )
    fig.text(0.5, 0.01, stats_text, ha="center", fontsize=9, style="italic")

    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    fig.savefig(args.outpdf, dpi=150, bbox_inches="tight")
    fig.savefig(args.outpng, dpi=150, bbox_inches="tight")
    print(f"Wrote {args.outpdf}")
    print(f"Wrote {args.outpng}")
    print(stats_text)


if __name__ == "__main__":
    main()
