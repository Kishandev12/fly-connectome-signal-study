"""Run a compact cM15 circuit with LIF parameters from the Shiu et al. model.

The full model needs several GB of memory when loading every connection into
Brian2. This script streams the public connectome in batches and retains only
the strongest first- and second-hop links around one annotated cM15 neuron.
"""

from pathlib import Path
import argparse
import random

import brian2 as b2
import pandas as pd
import pyarrow.parquet as pq


ROOT = Path(__file__).parent
DATA = ROOT / "data"
RESULTS = ROOT / "results" / "lif"
PRE = "Presynaptic_Index"
POST = "Postsynaptic_Index"
WEIGHT = "Excitatory x Connectivity"
SOURCE_ROOT_ID = "720575940628038808"
SOURCE_TAG = "cM15_ACh"


def read_source_index():
    completeness = pd.read_csv(DATA / "Completeness_783.csv", index_col=0)
    ids = [str(root_id) for root_id in completeness.index]
    try:
        return ids.index(SOURCE_ROOT_ID)
    except ValueError as exc:
        raise SystemExit(f"Source FlyWire ID {SOURCE_ROOT_ID} is not in the v783 neuron table.") from exc


def scan_outgoing(source_indices):
    """Stream the Parquet file and keep only rows from the requested neurons."""
    file = pq.ParquetFile(DATA / "Connectivity_783.parquet")
    selected = []
    source_indices = set(int(value) for value in source_indices)
    for batch in file.iter_batches(columns=[PRE, POST, WEIGHT], batch_size=200_000):
        frame = batch.to_pandas()
        hits = frame[frame[PRE].isin(source_indices)]
        if not hits.empty:
            selected.append(hits)
    if not selected:
        return pd.DataFrame(columns=[PRE, POST, WEIGHT])
    return pd.concat(selected, ignore_index=True)


def make_sampled_circuit(source_index, first_hop_limit, second_hop_limit, sample_tag):
    first = scan_outgoing([source_index])
    if first.empty:
        raise SystemExit("No outgoing connections found for the selected cL21 neuron.")
    first = first[first[POST] != source_index].copy()
    first["abs_weight"] = first[WEIGHT].abs()
    first = first.nlargest(first_hop_limit, "abs_weight")

    first_layer = first[POST].astype(int).unique().tolist()
    second = scan_outgoing(first_layer)
    if not second.empty:
        second = second[second[PRE] != second[POST]].copy()
        second["abs_weight"] = second[WEIGHT].abs()
        second = (
            second.sort_values("abs_weight", ascending=False)
            .groupby(PRE, sort=False)
            .head(second_hop_limit)
        )

    columns = [PRE, POST, WEIGHT]
    edges = pd.concat([first[columns], second[columns]], ignore_index=True)
    edges = edges.drop_duplicates([PRE, POST]).copy()
    edges[PRE] = edges[PRE].astype(int)
    edges[POST] = edges[POST].astype(int)

    neuron_indices = sorted(set(edges[PRE]) | set(edges[POST]) | {source_index})
    completeness = pd.read_csv(DATA / "Completeness_783.csv", index_col=0)
    root_ids = [str(root_id) for root_id in completeness.index]
    ann = pd.read_csv(
        DATA / "annotations" / "neuron_annotations.tsv",
        sep="\t",
        usecols=["root_id", "super_class", "cell_type", "top_nt", "side"],
        dtype={"root_id": "string"},
    ).drop_duplicates("root_id")
    nodes = pd.DataFrame({"neuron_index": neuron_indices})
    nodes["root_id"] = nodes["neuron_index"].map(lambda i: root_ids[int(i)]).astype("string")
    nodes = nodes.merge(ann, on="root_id", how="left")
    nodes["local_index"] = range(len(nodes))
    local = dict(zip(nodes["neuron_index"], nodes["local_index"]))
    edges["i"] = edges[PRE].map(local).astype(int)
    edges["j"] = edges[POST].map(local).astype(int)
    edges.to_csv(RESULTS / f"{SOURCE_TAG}_{sample_tag}_sampled_circuit_edges.csv", index=False)
    nodes.to_csv(RESULTS / f"{SOURCE_TAG}_{sample_tag}_sampled_circuit_nodes.csv", index=False)
    return nodes, edges, local[source_index]


def simulate(nodes, edges, source_local, seed):
    b2.start_scope()
    b2.seed(seed)
    b2.defaultclock.dt = 0.1 * b2.ms
    b2.prefs.codegen.target = "numpy"

    params = {
        "v_rest": -52 * b2.mV,
        "v_reset": -52 * b2.mV,
        "v_threshold": -45 * b2.mV,
        "tau_m": 20 * b2.ms,
        "tau_syn": 5 * b2.ms,
    }
    equations = """
    dv/dt = (v_rest - v + g) / tau_m : volt (unless refractory)
    dg/dt = -g / tau_syn : volt (unless refractory)
    rfc : second
    """
    neurons = b2.NeuronGroup(
        len(nodes),
        model=equations,
        threshold="v > v_threshold",
        reset="v = v_reset; g = 0*mV",
        refractory="rfc",
        method="linear",
        namespace=params,
    )
    neurons.v = params["v_rest"]
    neurons.g = 0 * b2.mV
    neurons.rfc = 2.2 * b2.ms
    neurons.rfc[source_local] = 0 * b2.ms

    synapses = b2.Synapses(
        neurons,
        neurons,
        model="w : volt",
        on_pre="g_post += w",
        delay=1.8 * b2.ms,
    )
    synapses.connect(i=edges["i"].to_numpy(), j=edges["j"].to_numpy())
    synapses.w = edges[WEIGHT].to_numpy(dtype=float) * 0.275 * b2.mV

    stimulus = b2.PoissonInput(
        neurons[source_local],
        target_var="v",
        N=1,
        rate=150 * b2.Hz,
        weight=0.275 * 250 * b2.mV,
    )
    monitor = b2.SpikeMonitor(neurons)
    network = b2.Network(neurons, synapses, stimulus, monitor)
    network.run(200 * b2.ms)

    events = pd.DataFrame({
        "local_index": monitor.i[:],
        "time_ms": monitor.t[:] / b2.ms,
    })
    events = events.merge(
        nodes[["local_index", "neuron_index", "root_id", "cell_type", "super_class", "top_nt", "side"]],
        on="local_index",
        how="left",
    )
    return events


def degree_preserving_rewire(edges, seed):
    """Shuffle directed partner assignments while preserving in/out degrees."""
    pairs = list(zip(edges["i"].astype(int), edges["j"].astype(int)))
    edge_set = set(pairs)
    rng = random.Random(seed)
    for _ in range(max(1, 10 * len(pairs))):
        a_i, b_i = rng.sample(range(len(pairs)), 2)
        a, b = pairs[a_i]
        c, d = pairs[b_i]
        if a == c or b == d or a == d or c == b:
            continue
        new_a, new_c = (a, d), (c, b)
        if new_a in edge_set or new_c in edge_set:
            continue
        edge_set.remove((a, b))
        edge_set.remove((c, d))
        edge_set.add(new_a)
        edge_set.add(new_c)
        pairs[a_i], pairs[b_i] = new_a, new_c
    rewired = edges.copy()
    rewired["i"] = [pair[0] for pair in pairs]
    rewired["j"] = [pair[1] for pair in pairs]
    return rewired


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=int, default=10, help="Independent Poisson-input trials")
    parser.add_argument("--seed", type=int, default=7, help="Starting random seed")
    parser.add_argument("--first-hop", type=int, default=100, help="Strongest source-to-partner links to keep")
    parser.add_argument("--second-hop", type=int, default=20, help="Strongest outgoing links per first-hop neuron")
    args = parser.parse_args()
    if args.runs < 1 or args.first_hop < 1 or args.second_hop < 1:
        raise SystemExit("--runs, --first-hop, and --second-hop must all be at least 1")
    sample_tag = f"h{args.first_hop}_k{args.second_hop}"

    RESULTS.mkdir(parents=True, exist_ok=True)
    source_index = read_source_index()
    print("Preparing a memory-limited two-hop circuit by streaming connectome batches...")
    nodes, edges, source_local = make_sampled_circuit(source_index, args.first_hop, args.second_hop, sample_tag)
    print(f"Sampled circuit: {len(nodes):,} neurons, {len(edges):,} connections")
    print(f"Simulating {args.runs} paired trials on measured and degree-preserving rewired wiring...")
    trials = []
    trial_metrics = []
    for trial in range(args.runs):
        rewired = degree_preserving_rewire(edges, args.seed + 10_000 + trial)
        for condition, condition_edges in [("measured", edges), ("rewired", rewired)]:
            events = simulate(nodes, condition_edges, source_local, args.seed + trial)
            events["trial"] = trial
            events["condition"] = condition
            trials.append(events)
            trial_metrics.append({
                "trial": trial,
                "condition": condition,
                "spikes": len(events),
                "neurons_with_spikes": events["local_index"].nunique(),
            })
            print(f"  trial {trial + 1}/{args.runs}, {condition}: {len(events):,} spikes, {events['local_index'].nunique():,} neurons")
    events = pd.concat(trials, ignore_index=True)
    out = RESULTS / f"{SOURCE_TAG}_{sample_tag}_measured_vs_rewired_spikes.csv"
    events.to_csv(out, index=False)
    pd.DataFrame(trial_metrics).to_csv(RESULTS / f"{SOURCE_TAG}_{sample_tag}_control_trial_metrics.csv", index=False)
    print(f"Total spikes across trials: {len(events):,}")
    print(f"Saved spike events: {out}")
    print("Stimulated neuron: cM15, annotated acetylcholine, visual_centrifugal.")
    print("This is a sampled-subnetwork comparison, not a full-brain reproduction.")


if __name__ == "__main__":
    main()

