"""Summarize connection counts in the FlyWire v783 table."""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).parent
DATA = ROOT / "data" / "Connectivity_783.parquet"
OUT = ROOT / "results"


def main():
    if not DATA.exists():
        raise SystemExit(f"Connectome file not found: {DATA}")

    print("Reading FlyWire connections (first run may take a little while)...")
    connections = pd.read_parquet(DATA, columns=["Presynaptic_Index", "Postsynaptic_Index"])
    out_degree = connections.groupby("Presynaptic_Index").size().rename("outgoing_connections")
    in_degree = connections.groupby("Postsynaptic_Index").size().rename("incoming_connections")
    stats = pd.concat([out_degree, in_degree], axis=1).fillna(0).astype("int64")
    stats.index.name = "neuron_index"

    OUT.mkdir(exist_ok=True)
    stats.to_csv(OUT / "neuron_connection_counts.csv")
    stats.describe(percentiles=[0.5, 0.9, 0.95, 0.99]).to_csv(OUT / "degree_summary.csv")

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    for ax, column, title in [
        (axes[0], "incoming_connections", "Incoming connections per neuron"),
        (axes[1], "outgoing_connections", "Outgoing connections per neuron"),
    ]:
        positive = stats.loc[stats[column] > 0, column]
        ax.hist(positive, bins=60, color="#3977a8", edgecolor="white")
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlabel("Number of connected partner neurons (log scale)")
        ax.set_ylabel("Number of neurons (log scale)")
        ax.set_title(title)

    fig.suptitle("FlyWire v783 connection counts")
    fig.tight_layout()
    fig.savefig(OUT / "degree_distribution.png", dpi=180)

    print(f"Neurons represented in connection table: {len(stats):,}")
    print(f"Connection pairs: {len(connections):,}")
    print("\nTop 10 neurons by outgoing partner count:")
    print(stats.nlargest(10, "outgoing_connections").to_string())
    print(f"\nSaved results to: {OUT}")
    print("These are graph counts, not biological cell-type labels.")


if __name__ == "__main__":
    main()

