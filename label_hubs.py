"""Map the highest-degree graph indices to FlyWire's published annotations."""

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).parent
DATA = ROOT / "data"
RESULTS = ROOT / "results"


def main():
    counts_path = RESULTS / "neuron_connection_counts.csv"
    if not counts_path.exists():
        raise SystemExit("Run analyze_connectome.py first.")

    completeness = pd.read_csv(DATA / "Completeness_783.csv", index_col=0)
    annotations = pd.read_csv(
        DATA / "annotations" / "neuron_annotations.tsv",
        sep="\t",
        usecols=["root_id", "cell_type", "cell_class", "super_class", "top_nt", "side"],
        dtype={"root_id": "string"},
    )
    annotations = annotations.drop_duplicates("root_id").set_index("root_id")

    counts = pd.read_csv(counts_path, index_col="neuron_index")
    top = counts.nlargest(20, "outgoing_connections").copy()
    top["neuron_index"] = top.index.astype(int)
    ids = completeness.index.to_series().reset_index(drop=True)
    top["root_id"] = top["neuron_index"].map(ids)
    top["root_id"] = top["root_id"].astype("string")
    labeled = top.join(annotations, on="root_id")
    labeled.to_csv(RESULTS / "top_hubs_with_annotations.csv", index=False)

    print("Top outgoing hubs with FlyWire annotations:")
    print(labeled[["neuron_index", "root_id", "outgoing_connections", "cell_type", "cell_class", "super_class", "top_nt", "side"]].to_string(index=False))
    print(f"\nSaved: {RESULTS / 'top_hubs_with_annotations.csv'}")
    print("Blank labels mean the public annotation table has no label for that neuron.")


if __name__ == "__main__":
    main()

