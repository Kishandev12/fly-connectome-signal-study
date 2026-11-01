import argparse
import csv
import random
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt


def demo_edges():
    # A small toy network so the project runs before downloading biological data.
    return [(0, 2, 1.0), (0, 3, 0.8), (1, 3, 0.8), (2, 4, 0.9),
            (3, 4, 0.8), (3, 5, 1.0), (4, 6, 0.8), (5, 6, 0.9),
            (6, 7, 1.0), (2, 7, 0.4)]


def read_edges(filename):
    with open(filename, newline="", encoding="utf-8-sig") as handle:
        rows = csv.DictReader(handle)
        required = {"source", "target"}
        if not required.issubset(rows.fieldnames or []):
            raise ValueError("CSV needs source and target columns; weight is optional.")
        return [(int(r["source"]), int(r["target"]), float(r.get("weight") or 1)) for r in rows]


def rewire_degree_preserving(edges, rng, swaps=None):
    """Directed double-edge swaps preserve each node's in/out degree."""
    pairs = [(s, t) for s, t, _ in edges]
    weights = [w for _, _, w in edges]
    edge_set = set(pairs)
    swaps = swaps if swaps is not None else max(1, 5 * len(pairs))
    for _ in range(swaps):
        i, j = rng.sample(range(len(pairs)), 2)
        a, b = pairs[i]
        c, d = pairs[j]
        if a == c or b == d or a == d or c == b:
            continue
        new1, new2 = (a, d), (c, b)
        if new1 in edge_set or new2 in edge_set:
            continue
        edge_set.remove((a, b)); edge_set.remove((c, d))
        edge_set.add(new1); edge_set.add(new2)
        pairs[i], pairs[j] = new1, new2
    return [(s, t, w) for (s, t), w in zip(pairs, weights)]


def simulate(edges, source, steps=20, threshold=1.0, decay=0.35):
    nodes = {n for s, t, _ in edges for n in (s, t)} | {source}
    outgoing = defaultdict(list)
    for s, t, weight in edges:
        outgoing[s].append((t, weight))
    potential = {n: 0.0 for n in nodes}
    active = {source}
    counts = [1]
    for _ in range(steps):
        for n in potential:
            potential[n] *= (1.0 - decay)
        for n in active:
            for target, weight in outgoing[n]:
                potential[target] += weight
        active = {n for n, value in potential.items() if value >= threshold}
        for n in active:
            potential[n] = 0.0  # one event per threshold crossing
        counts.append(len(active))
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--edges", help="CSV edge list (source,target, optional weight)")
    parser.add_argument("--source", type=int, default=0, help="Starting neuron ID")
    parser.add_argument("--steps", type=int, default=20)
    parser.add_argument("--threshold", type=float, default=1.0)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()

    edges = read_edges(args.edges) if args.edges else demo_edges()
    if not edges:
        raise ValueError("No edges found.")
    rng = random.Random(args.seed)
    real = simulate(edges, args.source, args.steps, args.threshold)
    rewired_edges = rewire_degree_preserving(edges, rng)
    rewired = simulate(rewired_edges, args.source, args.steps, args.threshold)

    with open("results.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["step", "measured_wiring", "degree_preserving_rewire"])
        writer.writerows(zip(range(args.steps + 1), real, rewired))
    plt.plot(range(len(real)), real, marker="o", label="Measured wiring")
    plt.plot(range(len(rewired)), rewired, marker="o", label="Rewired control")
    plt.xlabel("Time step")
    plt.ylabel("Neurons active")
    plt.title("Signal spread: connectome vs rewired control")
    plt.legend()
    plt.tight_layout()
    plt.savefig("activity.png", dpi=160)
    print(f"Finished. Active-neuron totals: wiring={sum(real)}, rewired={sum(rewired)}")
    print("Wrote results.csv and activity.png")


if __name__ == "__main__":
    main()

