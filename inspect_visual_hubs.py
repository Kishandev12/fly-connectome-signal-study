"""Inspect the strongest visual-centrifugal hubs and their output classes."""

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).parent
DATA = ROOT / "data"
RESULTS = ROOT / "results"
PRE = "Presynaptic_Index"
POST = "Postsynaptic_Index"


def main():
    counts_path = RESULTS / "neuron_connection_counts.csv"
    if not counts_path.exists():
        raise SystemExit("Run analyze_connectome.py first.")

    counts = pd.read_csv(counts_path, index_col="neuron_index")
    completeness = pd.read_csv(DATA / "Completeness_783.csv", index_col=0)
    ids = completeness.index.to_series().reset_index(drop=True)
    ann = pd.read_csv(
        DATA / "annotations" / "neuron_annotations.tsv",
        sep="\t",
        usecols=["root_id", "super_class", "cell_type", "top_nt", "side"],
        dtype={"root_id": "string"},
    ).drop_duplicates("root_id")

    neurons = counts.copy()
    neurons["neuron_index"] = neurons.index.astype(int)
    neurons["root_id"] = neurons["neuron_index"].map(ids).astype("string")
    neurons = neurons.reset_index(drop=True).merge(ann, on="root_id", how="left")

    vc = neurons[neurons["super_class"].eq("visual_centrifugal")]
    if vc.empty:
        raise SystemExit("No visual_centrifugal annotations found; check annotation version.")
    hubs = vc.nlargest(10, "outgoing_connections").copy()
    hubs.to_csv(RESULTS / "visual_centrifugal_hubs.csv", index=False)
    hub_indices = set(hubs["neuron_index"].astype(int))

    print("Top visual_centrifugal neurons by outgoing partner count:")
    print(hubs[["neuron_index", "root_id", "cell_type", "outgoing_connections", "incoming_connections", "top_nt", "side"]].to_string(index=False))

    print("\nReading the selected hubs' downstream connections...")
    edges = pd.read_parquet(DATA / "Connectivity_783.parquet", columns=[PRE, POST, "Excitatory x Connectivity"])
    edges = edges[edges[PRE].isin(hub_indices)].copy()
    edges["source_index"] = edges[PRE].astype(int)
    edges["target_index"] = edges[POST].astype(int)
    edges["target_root_id"] = edges["target_index"].map(ids).astype("string")
    edges = edges.merge(
        ann[["root_id", "super_class"]].rename(columns={"root_id": "target_root_id", "super_class": "target_super_class"}),
        on="target_root_id",
        how="left",
    )
    edges["target_super_class"] = edges["target_super_class"].fillna("unannotated")
    targets = edges.groupby(["source_index", "target_super_class"]).agg(
        partner_neurons=(POST, "size"),
        summed_model_weight=("Excitatory x Connectivity", "sum"),
    ).reset_index()
    targets = targets.merge(
        hubs[["neuron_index", "root_id", "cell_type"]].rename(columns={"neuron_index": "source_index", "root_id": "source_root_id", "cell_type": "source_cell_type"}),
        on="source_index",
        how="left",
    )
    targets = targets.sort_values(["source_index", "partner_neurons"], ascending=[True, False])
    targets.to_csv(RESULTS / "visual_centrifugal_hub_targets.csv", index=False)
    print("\nLargest downstream superclass groups for each selected hub:")
    print(targets.groupby("source_index", group_keys=False).head(3)[["source_cell_type", "source_root_id", "target_super_class", "partner_neurons"]].to_string(index=False))
    print(f"\nSaved source and target tables in {RESULTS}")
    print("Partner counts describe graph structure; summed model weights are input values, not measured physiological strengths.")


if __name__ == "__main__":
    main()

