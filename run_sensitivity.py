"""Repeat the paired network comparison at three subnetwork sizes."""

import argparse
import subprocess
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).parent
RESULTS = ROOT / "results" / "lif"
CONFIGS = [(50, 10), (100, 20), (150, 30)]


def run_step(label, script, *args):
    print(f"\n=== {label} ===", flush=True)
    subprocess.run([sys.executable, str(ROOT / script), *args], cwd=ROOT, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=int, default=10, help="Paired trials per sample size")
    parser.add_argument("--seed", type=int, default=7, help="Starting random seed")
    args = parser.parse_args()
    if args.runs < 1:
        raise SystemExit("--runs must be at least 1")

    rows = []
    for first_hop, second_hop in CONFIGS:
        tag = f"h{first_hop}_k{second_hop}"
        run_step(
            f"Simulate {tag} measured and rewired networks",
            "simulate_visual_hub.py",
            "--runs", str(args.runs),
            "--seed", str(args.seed),
            "--first-hop", str(first_hop),
            "--second-hop", str(second_hop),
        )
        run_step(f"Summarize {tag}", "summarize_spikes.py", "--sample-tag", tag)
        run_step(f"Compare conditions for {tag}", "compare_network_conditions.py", "--sample-tag", tag)

        differences = pd.read_csv(RESULTS / f"paired_network_differences_{tag}.csv")
        nodes = pd.read_csv(RESULTS / f"cM15_ACh_{tag}_sampled_circuit_nodes.csv")
        delta_nodes = differences["measured_minus_rewired_active_downstream_neurons"]
        delta_spikes = differences["measured_minus_rewired_downstream_spikes"]
        rows.append({
            "sample_tag": tag,
            "first_hop_links": first_hop,
            "second_hop_links_per_neuron": second_hop,
            "sampled_neurons": len(nodes),
            "mean_paired_extra_active_neurons": delta_nodes.mean(),
            "sd_paired_extra_active_neurons": delta_nodes.std(),
            "mean_paired_extra_spikes": delta_spikes.mean(),
            "positive_pairs_active_neurons": int((delta_nodes > 0).sum()),
            "positive_pairs_spikes": int((delta_spikes > 0).sum()),
            "active_neuron_gain_fraction_of_sample": delta_nodes.mean() / max(1, len(nodes) - 1),
        })

    summary = pd.DataFrame(rows)
    summary.to_csv(RESULTS / "sample_size_sensitivity.csv", index=False)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.bar(summary["sample_tag"], summary["active_neuron_gain_fraction_of_sample"] * 100, color="#3977a8")
    ax.set_ylabel("Measured minus rewired active neurons (% of sampled nodes)")
    ax.set_xlabel("Strong-link sample size")
    ax.set_title("Sensitivity of recruitment advantage to circuit sample size")
    fig.tight_layout()
    fig.savefig(RESULTS / "sample_size_sensitivity.png", dpi=180)
    print("\nSensitivity summary:")
    print(summary.to_string(index=False, float_format=lambda x: f"{x:.3f}"))
    print(f"\nSaved sensitivity table and plot in {RESULTS}")


if __name__ == "__main__":
    main()

