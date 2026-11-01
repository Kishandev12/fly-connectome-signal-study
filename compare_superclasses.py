"""Check which annotated superclasses are enriched among high-outdegree neurons."""

from math import ceil
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).parent
DATA = ROOT / "data"
RESULTS = ROOT / "results"


def main():
    counts_path = RESULTS / "neuron_connection_counts.csv"
    if not counts_path.exists():
        raise SystemExit("Run analyze_connectome.py first.")

    counts = pd.read_csv(counts_path, index_col="neuron_index")
    completeness = pd.read_csv(DATA / "Completeness_783.csv", index_col=0)
    annotations = pd.read_csv(
        DATA / "annotations" / "neuron_annotations.tsv",
        sep="\t",
        usecols=["root_id", "super_class"],
        dtype={"root_id": "string"},
    ).drop_duplicates("root_id")

    root_ids = completeness.index.to_series().reset_index(drop=True)
    counts = counts.copy()
    counts["root_id"] = counts.index.to_series().map(root_ids).astype("string")
    data = counts.reset_index().merge(annotations, on="root_id", how="left")
    data["super_class"] = data["super_class"].fillna("unannotated")

    # Define hubs as the top 1% of neurons by distinct outgoing partner count.
    hub_count = max(1, ceil(len(data) * 0.01))
    hub_indices = set(data.nlargest(hub_count, "outgoing_connections")["neuron_index"])
    data["is_hub"] = data["neuron_index"].isin(hub_indices)
    baseline_rate = data["is_hub"].mean()

    summary = data.groupby("super_class", dropna=False).agg(
        neuron_count=("neuron_index", "size"),
        hub_count=("is_hub", "sum"),
        median_outgoing=("outgoing_connections", "median"),
        p90_outgoing=("outgoing_connections", lambda s: s.quantile(0.90)),
    )
    summary["hub_rate"] = summary["hub_count"] / summary["neuron_count"]
    summary["hub_enrichment"] = summary["hub_rate"] / baseline_rate
    summary = summary[summary["neuron_count"] >= 50].sort_values("hub_enrichment", ascending=False)

    RESULTS.mkdir(exist_ok=True)
    summary.to_csv(RESULTS / "superclass_hub_enrichment.csv")
    plot_data = summary.head(15).sort_values("hub_enrichment")
    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.barh(plot_data.index, plot_data["hub_enrichment"], color="#3977a8")
    ax.axvline(1.0, color="#b94a48", linestyle="--", linewidth=1, label="Overall hub rate")
    ax.set_xlabel("Enrichment among top 1% by outgoing partner count")
    ax.set_title("Which FlyWire neuron classes contain more high-outdegree neurons?")
    ax.legend()
    fig.tight_layout()
    fig.savefig(RESULTS / "superclass_hub_enrichment.png", dpi=180)

    print(f"Neurons analyzed: {len(data):,}; hubs by rank (top 1%): {hub_count:,}")
    print(f"Annotation coverage: {data['super_class'].ne('unannotated').mean():.1%}")
    print("\nSuperclasses with highest hub enrichment (at least 50 neurons):")
    print(summary.head(15).to_string(float_format=lambda x: f"{x:.3f}"))
    print(f"\nSaved table and plot in {RESULTS}")
    print("Enrichment is descriptive; it does not establish a causal or functional role.")


if __name__ == "__main__":
    main()

