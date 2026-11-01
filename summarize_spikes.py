"""Summarize repeated cM15 pilot spike output by annotated superclass."""

from pathlib import Path
import argparse

import pandas as pd


ROOT = Path(__file__).parent
SOURCE_ID = "720575940628038808"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample-tag", default="h100_k20", help="Subnetwork tag, e.g. h100_k20")
    args = parser.parse_args()
    results = ROOT / "results" / "lif"
    spikes_path = results / f"cM15_ACh_{args.sample_tag}_measured_vs_rewired_spikes.csv"
    trials_path = results / f"cM15_ACh_{args.sample_tag}_control_trial_metrics.csv"
    if not spikes_path.exists():
        raise SystemExit("Run simulate_visual_hub.py first.")
    if not trials_path.exists():
        raise SystemExit("Run the updated simulate_visual_hub.py first to create trial metrics.")

    spikes = pd.read_csv(spikes_path)
    if spikes.empty:
        print("The pilot produced no spikes. No downstream summary was written.")
        return
    spikes["root_id"] = spikes["root_id"].astype("string")
    spikes = spikes[spikes["root_id"].ne(SOURCE_ID)].copy()
    if spikes.empty:
        print("No downstream neurons fired in these trials.")
        return
    spikes["super_class"] = spikes["super_class"].fillna("unannotated")
    spikes["cell_type"] = spikes["cell_type"].fillna("unannotated")
    per_neuron = spikes.groupby(["condition", "trial", "super_class", "root_id"]).agg(
        first_spike_ms=("time_ms", "min"),
        spikes=("time_ms", "size"),
    ).reset_index()
    per_trial = per_neuron.groupby(["condition", "trial", "super_class"]).agg(
        neurons_with_spikes=("root_id", "nunique"),
        total_spikes=("spikes", "sum"),
        median_first_spike_ms=("first_spike_ms", "median"),
    )
    trial_metrics = pd.read_csv(trials_path)
    trial_ids = sorted(trial_metrics["trial"].unique())
    conditions = sorted(trial_metrics["condition"].unique())
    classes = sorted(per_trial.index.get_level_values("super_class").unique())
    full_index = pd.MultiIndex.from_product([conditions, trial_ids, classes], names=["condition", "trial", "super_class"])
    per_trial = per_trial.reindex(full_index)
    per_trial[["neurons_with_spikes", "total_spikes"]] = per_trial[["neurons_with_spikes", "total_spikes"]].fillna(0)
    per_trial["trials_with_activity"] = (per_trial["neurons_with_spikes"] > 0).astype(int)
    per_trial = per_trial.reset_index()
    summary = per_trial.groupby(["condition", "super_class"]).agg(
        mean_neurons_with_spikes=("neurons_with_spikes", "mean"),
        sd_neurons_with_spikes=("neurons_with_spikes", "std"),
        mean_total_spikes=("total_spikes", "mean"),
        sd_total_spikes=("total_spikes", "std"),
        median_first_spike_ms=("median_first_spike_ms", "median"),
        trials_with_activity=("trials_with_activity", "sum"),
    ).fillna(0).sort_values("mean_neurons_with_spikes", ascending=False)
    out = results / f"cM15_ACh_{args.sample_tag}_control_summary.csv"
    summary.to_csv(out)
    print(f"Downstream spikes across trials: {len(spikes):,}")
    print(f"Trials per condition: {len(trial_ids)}")
    print("\nMean downstream activity by condition and superclass:")
    print(summary.head(15).to_string(float_format=lambda x: f"{x:.2f}"))
    print(f"\nSaved: {out}")
    print("These repeated runs estimate model variability, not biological variation or experimental uncertainty.")


if __name__ == "__main__":
    main()

