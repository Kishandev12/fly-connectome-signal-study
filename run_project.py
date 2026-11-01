"""Run the FlyWire project pipeline from one command."""

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).parent


def run_step(label, script, *args):
    print(f"\n=== {label} ===", flush=True)
    subprocess.run([sys.executable, str(ROOT / script), *args], cwd=ROOT, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=int, default=10, help="Paired measured/rewired trials (default: 10)")
    parser.add_argument("--seed", type=int, default=7, help="Starting random seed")
    parser.add_argument("--refresh-structure", action="store_true", help="Recalculate the full connectome degree and hub analyses")
    args = parser.parse_args()
    if args.runs < 1:
        raise SystemExit("--runs must be at least 1")

    counts = ROOT / "results" / "neuron_connection_counts.csv"
    if args.refresh_structure or not counts.exists():
        run_step("Connectome degree analysis", "analyze_connectome.py")
    else:
        print("Using saved structural analysis. Add --refresh-structure to recalculate it.", flush=True)

    hubs = ROOT / "results" / "top_hubs_with_annotations.csv"
    if args.refresh_structure or not hubs.exists():
        run_step("Label high-outdegree neurons", "label_hubs.py")
    else:
        print("Using saved neuron annotations.", flush=True)

    enrichment = ROOT / "results" / "superclass_hub_enrichment.csv"
    if args.refresh_structure or not enrichment.exists():
        run_step("Compare hub enrichment by superclass", "compare_superclasses.py")

    targets = ROOT / "results" / "visual_centrifugal_hub_targets.csv"
    if args.refresh_structure or not targets.exists():
        run_step("Inspect visual-centrifugal hub targets", "inspect_visual_hubs.py")

    run_step(
        "Paired measured versus rewired LIF simulations",
        "simulate_visual_hub.py",
        "--runs",
        str(args.runs),
        "--seed",
        str(args.seed),
    )
    run_step("Summarize spike activity", "summarize_spikes.py")
    run_step("Compare network conditions and save figures", "compare_network_conditions.py")
    print("\nPipeline complete. Results are in results/ and results/lif/.", flush=True)


if __name__ == "__main__":
    main()

