"""Run a memory-conscious whole-connectome LIF pilot using the Shiu parameters.

Unlike simulate_visual_hub.py, this keeps the full v783 edge set. Parquet is
read in batches and immediately narrowed to 32-bit numeric arrays to avoid the
large temporary pandas dataframe that caused the earlier memory allocation
failure. A full run can still require substantial RAM and may be slow when
Brian2 falls back to its NumPy target.
"""

from pathlib import Path
import argparse
import gc

import brian2 as b2
import numpy as np
import pandas as pd
import pyarrow.parquet as pq


ROOT = Path(__file__).parent
DATA = ROOT / "data"
RESULTS = ROOT / "results" / "whole_brain"
PRE = "Presynaptic_Index"
POST = "Postsynaptic_Index"
WEIGHT = "Excitatory x Connectivity"
SOURCE_ROOT_ID = "720575940628038808"


def load_edges_batched(batch_size):
    """Load the full edge list in compact typed arrays, not pandas frames."""
    path = DATA / "Connectivity_783.parquet"
    parquet = pq.ParquetFile(path)
    pre_parts, post_parts, weight_parts = [], [], []
    rows = 0
    print("Reading full connectivity in compact batches...")
    for number, batch in enumerate(
        parquet.iter_batches(columns=[PRE, POST, WEIGHT], batch_size=batch_size), start=1
    ):
        # iter_batches returns only the selected columns, so use that batch's
        # schema positions rather than positions from the full Parquet schema.
        pre_col = batch.schema.get_field_index(PRE)
        post_col = batch.schema.get_field_index(POST)
        weight_col = batch.schema.get_field_index(WEIGHT)
        if min(pre_col, post_col, weight_col) < 0:
            raise SystemExit(f"Expected connectome columns are missing from {path.name}.")
        pre = batch.column(pre_col).to_numpy(zero_copy_only=False).astype(np.int32, copy=False)
        post = batch.column(post_col).to_numpy(zero_copy_only=False).astype(np.int32, copy=False)
        weight = batch.column(weight_col).to_numpy(zero_copy_only=False).astype(np.float32, copy=False)
        keep = pre != post
        pre_parts.append(pre[keep].copy())
        post_parts.append(post[keep].copy())
        weight_parts.append(weight[keep].copy())
        rows += int(keep.sum())
        print(f"  batches read: {number}; connections retained: {rows:,}", end="\r")
        del batch, pre, post, weight, keep
    print()
    pre = np.concatenate(pre_parts)
    post = np.concatenate(post_parts)
    weight = np.concatenate(weight_parts)
    del pre_parts, post_parts, weight_parts
    gc.collect()
    return pre, post, weight


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--duration-ms", type=float, default=200.0, help="Simulation duration")
    parser.add_argument("--seed", type=int, default=7, help="Random seed for the input stimulus")
    parser.add_argument("--batch-size", type=int, default=200_000, help="Parquet rows read per batch")
    parser.add_argument(
        "--connection-chunk-size",
        type=int,
        default=250_000,
        help="Connections added to Brian2 per synapse group to limit temporary memory",
    )
    args = parser.parse_args()
    if args.duration_ms <= 0 or args.batch_size < 1 or args.connection_chunk_size < 1:
        raise SystemExit("--duration-ms, --batch-size, and --connection-chunk-size must be positive")

    completeness = pd.read_csv(DATA / "Completeness_783.csv", index_col=0)
    root_ids = completeness.index.astype("string")
    matches = np.flatnonzero(root_ids == SOURCE_ROOT_ID)
    if len(matches) != 1:
        raise SystemExit(f"Could not uniquely find stimulated FlyWire ID {SOURCE_ROOT_ID}.")
    source_index = int(matches[0])
    neuron_count = len(completeness)
    del completeness, root_ids, matches

    pre, post, weights = load_edges_batched(args.batch_size)
    if pre.size == 0 or int(max(pre.max(), post.max())) >= neuron_count:
        raise SystemExit("Connectivity indices do not match the v783 neuron index file.")

    connection_count = len(pre)
    print(f"Full network: {neuron_count:,} neurons, {connection_count:,} directed connections")
    print("Starting one stimulated whole-connectome trial with the published LIF parameters...")

    b2.start_scope()
    b2.seed(args.seed)
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
        neuron_count,
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
    neurons.rfc[source_index] = 0 * b2.ms

    # A single full-size connect(i, j) makes Brian2 allocate large int64
    # temporary source/target arrays. Build several smaller groups so its
    # temporary arrays stay bounded by --connection-chunk-size.
    synapse_groups = []
    chunk_size = args.connection_chunk_size
    chunk_count = (connection_count + chunk_size - 1) // chunk_size
    print(f"Adding {connection_count:,} connections in {chunk_count} chunks...")
    for chunk_number, start in enumerate(range(0, connection_count, chunk_size), start=1):
        stop = min(start + chunk_size, connection_count)
        synapses = b2.Synapses(
            neurons,
            neurons,
            model="w : volt",
            on_pre="g_post += w",
            delay=1.8 * b2.ms,
            name=f"connectome_synapses_{chunk_number}",
        )
        synapses.connect(i=pre[start:stop], j=post[start:stop])
        synapses.w = weights[start:stop] * 0.275 * b2.mV
        synapse_groups.append(synapses)
        print(f"  connection chunks: {chunk_number}/{chunk_count}", end="\r")
    print()
    del pre, post, weights
    gc.collect()

    stimulus = b2.PoissonInput(
        neurons[source_index],
        target_var="v",
        N=1,
        rate=150 * b2.Hz,
        weight=0.275 * 250 * b2.mV,
    )
    monitor = b2.SpikeMonitor(neurons)
    network = b2.Network(neurons, *synapse_groups, stimulus, monitor)
    network.run(args.duration_ms * b2.ms, report="text")

    RESULTS.mkdir(parents=True, exist_ok=True)
    events = pd.DataFrame({"neuron_index": monitor.i[:], "time_ms": monitor.t[:] / b2.ms})
    events.to_csv(RESULTS / "whole_brain_spikes.csv", index=False)
    active = events.groupby("neuron_index").agg(spike_count=("time_ms", "size"), first_spike_ms=("time_ms", "min"))
    active.to_csv(RESULTS / "whole_brain_active_neurons.csv")
    summary = pd.DataFrame([{
        "neurons_in_model": neuron_count,
        "connections_in_model": connection_count,
        "duration_ms": args.duration_ms,
        "spikes": len(events),
        "neurons_with_spikes": int(events["neuron_index"].nunique()),
        "seed": args.seed,
    }])
    summary.to_csv(RESULTS / "whole_brain_run_summary.csv", index=False)
    print(summary.to_string(index=False))
    print(f"Saved whole-network outputs to {RESULTS}")
    print("This is a model run on the full v783 graph, not a biological recording or validated behavior model.")


if __name__ == "__main__":
    main()

