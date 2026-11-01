"""Compare downstream recruitment in cL21 and repeated cM15 pilot runs."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).parent
RESULTS = ROOT / "results" / "lif"
RUNS = [
    ("cL21 (GABA)", "cL21_subset_spikes.csv", "720575940613065130", None),
    ("cM15 (ACh)", "cM15_ACh_subset_spikes.csv", "720575940628038808", "cM15_ACh_trial_metrics.csv"),
]


def main():
    loaded = []
    all_classes = set()
    for label, filename, source_id, metrics_file in RUNS:
        path = RESULTS / filename
        if not path.exists():
            raise SystemExit(f"Missing pilot output: {path}")
        spikes = pd.read_csv(path)
        if "trial" not in spikes:
            spikes["trial"] = 0
        if label.startswith("cM15") and "condition" in spikes:
            spikes = spikes[spikes["condition"].eq("measured")].copy()
        spikes["root_id"] = spikes["root_id"].astype("string")
        downstream = spikes[spikes["root_id"].ne(source_id)].copy()
        downstream["super_class"] = downstream["super_class"].fillna("unannotated")
        all_classes.update(downstream["super_class"].unique())
        if metrics_file and (RESULTS / metrics_file).exists():
            metric_rows = pd.read_csv(RESULTS / metrics_file)
            if "condition" in metric_rows:
                metric_rows = metric_rows[metric_rows["condition"].eq("measured")]
            trial_ids = sorted(metric_rows["trial"].unique())
        else:
            trial_ids = sorted(spikes["trial"].unique()) or [0]
        loaded.append((label, downstream, trial_ids))

    all_classes = sorted(all_classes)
    times = np.arange(0, 200.1, 5)
    class_rows = []
    curve_rows = []
    for label, downstream, trial_ids in loaded:
        per_trial = downstream.groupby(["trial", "super_class"]).agg(
            active_neurons=("root_id", "nunique"),
            spikes=("root_id", "size"),
        )
        full_index = pd.MultiIndex.from_product([trial_ids, all_classes], names=["trial", "super_class"])
        per_trial = per_trial.reindex(full_index).fillna(0).reset_index()
        summary = per_trial.groupby("super_class").agg(
            mean_active_neurons=("active_neurons", "mean"),
            sd_active_neurons=("active_neurons", "std"),
            mean_spikes=("spikes", "mean"),
            trials_with_activity=("active_neurons", lambda s: int((s > 0).sum())),
        ).fillna(0).reset_index()
        summary.insert(0, "run", label)
        class_rows.append(summary)

        curves = []
        for trial in trial_ids:
            trial_spikes = downstream[downstream["trial"].eq(trial)]
            first = trial_spikes.groupby("root_id")["time_ms"].min().to_numpy()
            curves.append([(first <= t).sum() for t in times])
        curve_rows.append((label, np.asarray(curves, dtype=float)))

    class_summary = pd.concat(class_rows, ignore_index=True)
    class_summary.to_csv(RESULTS / "pilot_downstream_summary.csv", index=False)

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    for label, curves in curve_rows:
        mean = curves.mean(axis=0)
        sd = curves.std(axis=0)
        axes[0].step(times, mean, where="post", label=label)
        axes[0].fill_between(times, mean - sd, mean + sd, step="post", alpha=0.18)
    axes[0].set_xlabel("Time after stimulus (ms)")
    axes[0].set_ylabel("Distinct downstream neurons that have spiked")
    axes[0].set_title("Cumulative downstream recruitment")
    axes[0].legend()

    plot_data = class_summary.pivot(index="super_class", columns="run", values="mean_active_neurons").fillna(0)
    plot_data.plot(kind="bar", ax=axes[1], color=["#577590", "#f8961e"])
    axes[1].set_xlabel("Annotated superclass")
    axes[1].set_ylabel("Mean downstream neurons with spikes per trial")
    axes[1].set_title("Recruitment by superclass")
    axes[1].tick_params(axis="x", rotation=35)
    fig.suptitle("Sampled LIF pilots: cL21 vs cM15")
    fig.tight_layout()
    fig.savefig(RESULTS / "pilot_comparison.png", dpi=180)

    print(class_summary.to_string(index=False, float_format=lambda x: f"{x:.2f}"))
    print(f"\nSaved comparison plot and tables in {RESULTS}")
    print("Each condition is a strongest-link sampled subnetwork; cL21 is one trial and cM15 uses available repeated trials.")


if __name__ == "__main__":
    main()

