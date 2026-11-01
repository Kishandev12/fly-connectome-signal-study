"""Compare measured and degree-preserving rewired cM15 networks."""

from pathlib import Path
import argparse

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).parent
RESULTS = ROOT / "results" / "lif"
SOURCE_ID = "720575940628038808"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample-tag", default="h100_k20", help="Subnetwork tag, e.g. h100_k20")
    args = parser.parse_args()
    spike_file = RESULTS / f"cM15_ACh_{args.sample_tag}_measured_vs_rewired_spikes.csv"
    metric_file = RESULTS / f"cM15_ACh_{args.sample_tag}_control_trial_metrics.csv"
    if not spike_file.exists() or not metric_file.exists():
        raise SystemExit("Run simulate_visual_hub.py first.")

    spikes = pd.read_csv(spike_file)
    spikes["root_id"] = spikes["root_id"].astype("string")
    spikes = spikes[spikes["root_id"].ne(SOURCE_ID)].copy()
    spikes["super_class"] = spikes["super_class"].fillna("unannotated")
    metrics = pd.read_csv(metric_file)
    conditions = sorted(metrics["condition"].unique())
    trial_ids = sorted(metrics["trial"].unique())
    classes = sorted(spikes["super_class"].unique())

    per_neuron = spikes.groupby(["condition", "trial", "super_class", "root_id"]).agg(
        first_spike_ms=("time_ms", "min"),
        spike_count=("time_ms", "size"),
    ).reset_index()
    per_trial = per_neuron.groupby(["condition", "trial", "super_class"]).agg(
        active_neurons=("root_id", "nunique"),
        spikes=("spike_count", "sum"),
    )
    full_index = pd.MultiIndex.from_product(
        [conditions, trial_ids, classes], names=["condition", "trial", "super_class"]
    )
    per_trial = per_trial.reindex(full_index).fillna(0).reset_index()
    summary = per_trial.groupby(["condition", "super_class"]).agg(
        mean_active_neurons=("active_neurons", "mean"),
        sd_active_neurons=("active_neurons", "std"),
        mean_spikes=("spikes", "mean"),
        trials_with_activity=("active_neurons", lambda x: int((x > 0).sum())),
    ).fillna(0).reset_index()
    summary.to_csv(RESULTS / f"measured_vs_rewired_by_class_{args.sample_tag}.csv", index=False)

    times = np.arange(0, 200.1, 5)
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    for condition in conditions:
        curves = []
        for trial in trial_ids:
            data = spikes[(spikes["condition"] == condition) & (spikes["trial"] == trial)]
            first = data.groupby("root_id")["time_ms"].min().to_numpy()
            curves.append([(first <= t).sum() for t in times])
        curves = np.asarray(curves, dtype=float)
        mean, sd = curves.mean(axis=0), curves.std(axis=0)
        axes[0].step(times, mean, where="post", label=condition)
        axes[0].fill_between(times, np.maximum(0, mean - sd), mean + sd, step="post", alpha=0.18)

    axes[0].set_xlabel("Time after stimulus (ms)")
    axes[0].set_ylabel("Distinct downstream neurons that have spiked")
    axes[0].set_title("Cumulative downstream recruitment")
    axes[0].legend()

    pivot = summary.pivot(index="super_class", columns="condition", values="mean_active_neurons").fillna(0)
    pivot.plot(kind="bar", ax=axes[1], color={"measured": "#f8961e", "rewired": "#577590"})
    axes[1].set_xlabel("Annotated superclass")
    axes[1].set_ylabel("Mean downstream neurons with spikes per trial")
    axes[1].set_title("Measured vs rewired wiring")
    axes[1].tick_params(axis="x", rotation=35)
    fig.suptitle("cM15 sampled network: measured wiring vs degree-preserving rewires")
    fig.tight_layout()
    fig.savefig(RESULTS / f"measured_vs_rewired_{args.sample_tag}.png", dpi=180)

    trial_totals = spikes.groupby(["condition", "trial"]).agg(
        active_downstream_neurons=("root_id", "nunique"),
        downstream_spikes=("root_id", "size"),
    )
    trial_index = pd.MultiIndex.from_product([conditions, trial_ids], names=["condition", "trial"])
    trial_totals = trial_totals.reindex(trial_index).fillna(0).reset_index()
    paired = trial_totals.pivot(index="trial", columns="condition")
    differences = pd.DataFrame(index=trial_ids)
    differences.index.name = "trial"
    for metric in ["active_downstream_neurons", "downstream_spikes"]:
        differences[f"measured_{metric}"] = paired[metric]["measured"]
        differences[f"rewired_{metric}"] = paired[metric]["rewired"]
        differences[f"measured_minus_rewired_{metric}"] = (
            differences[f"measured_{metric}"] - differences[f"rewired_{metric}"]
        )
    differences.to_csv(RESULTS / f"paired_network_differences_{args.sample_tag}.csv")

    print("Mean downstream activity per trial:")
    print(trial_totals.groupby("condition")[['active_downstream_neurons', 'downstream_spikes']].agg(["mean", "std"]).to_string(float_format=lambda x: f"{x:.2f}"))
    print("\nPaired measured-minus-rewired differences:")
    for metric in ["active_downstream_neurons", "downstream_spikes"]:
        delta = differences[f"measured_minus_rewired_{metric}"]
        print(f"  {metric}: mean {delta.mean():.2f}, SD {delta.std():.2f}, positive pairs {(delta > 0).sum()}/{len(delta)}")
    print("\nActivity by condition and superclass:")
    print(summary.to_string(index=False, float_format=lambda x: f"{x:.2f}"))
    print(f"\nSaved plot and tables in {RESULTS} for {args.sample_tag}")
    print("This is a structural null comparison on a strongest-link sampled subnetwork, not a biological experiment.")


if __name__ == "__main__":
    main()

