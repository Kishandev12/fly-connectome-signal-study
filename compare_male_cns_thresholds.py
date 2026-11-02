"""Compare MaleCNS shortest routes as weak edges are filtered out.

Uses the exact R1-R6 and DNg13 body IDs from results/male_cns/queried_path.csv,
so every threshold comparison holds the endpoints fixed.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from neuprint import Client, fetch_shortest_paths


OUT = Path("results/male_cns")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--thresholds", nargs="+", type=int, default=[1, 5, 10, 15],
                        help="minimum synapses per edge; default: 1 5 10 15")
    parser.add_argument("--timeout", type=float, default=5)
    args = parser.parse_args()

    token = os.environ.get("NEUPRINT_TOKEN")
    if not token:
        raise SystemExit("Set your private neuPrint token in NEUPRINT_TOKEN before running this script.")
    baseline_file = OUT / "queried_path.csv"
    if not baseline_file.exists():
        raise SystemExit("Run male_cns_visual_motor.py first so the selected endpoints are saved.")
    baseline = pd.read_csv(baseline_file)
    source_id = int(baseline.iloc[0]["bodyId"])
    target_id = int(baseline.iloc[-1]["bodyId"])

    client = Client("https://neuprint.janelia.org", dataset="male-cns:v1.0", token=token)
    rows: list[dict] = []
    route_rows: list[tuple[int, pd.DataFrame]] = []
    for threshold in sorted(set(args.thresholds)):
        paths = fetch_shortest_paths(source_id, target_id, min_weight=threshold,
                                     timeout=args.timeout, client=client)
        if paths.empty:
            rows.append({"min_synapses_per_edge": threshold, "route_found": False,
                         "neurons_in_route": 0, "hops": 0, "cell_types": "No route found"})
            print(f"threshold {threshold}: no route")
            continue
        route = paths.loc[paths["path"] == paths["path"].min()].copy()
        route = route.drop_duplicates("bodyId", keep="first").reset_index(drop=True)
        types = route["type"].fillna("Unannotated").astype(str).tolist()
        rows.append({
            "min_synapses_per_edge": threshold,
            "route_found": True,
            "neurons_in_route": len(route),
            "hops": max(0, len(route) - 1),
            "cell_types": " -> ".join(types),
            "edge_synapse_counts": " -> ".join(str(int(v)) for v in route["weight"].fillna(0).tolist()[1:]),
        })
        route_rows.append((threshold, route))
        print(f"threshold {threshold}: {len(route) - 1} hops; " + " -> ".join(types))

    summary = pd.DataFrame(rows)
    summary.to_csv(OUT / "threshold_comparison.csv", index=False)

    colors = ["#38bdf8", "#f59e0b", "#a78bfa", "#fb7185", "#34d399", "#f97316"]
    fig = go.Figure()
    for row_idx, (threshold, route) in enumerate(route_rows):
        yy = len(route_rows) - row_idx - 1
        xx = list(range(len(route)))
        edge_weights = route["weight"].fillna(0).astype(int).tolist()
        fig.add_trace(go.Scatter(
            x=xx, y=[yy] * len(route), mode="lines+markers+text",
            line={"color": colors[row_idx % len(colors)], "width": 3},
            marker={"size": 16}, text=route["type"].fillna("Unannotated").astype(str),
            textposition="top center",
            customdata=[[int(route.loc[i, "bodyId"]), edge_weights[i]]
                        for i in range(len(route))],
            hovertemplate=(f"minimum edge weight: {threshold}<br>%{{text}}<br>body ID %{{customdata[0]}}"
                           "<br>incoming edge: %{customdata[1]} synapses<extra></extra>"),
            name=f"minimum {threshold} synapses", showlegend=True,
        ))
    fig.update_layout(
        title="Does the visual-to-motor route change when weak edges are removed?",
        paper_bgcolor="#0b1220", plot_bgcolor="#0b1220",
        font={"color": "#e2e8f0"},
        xaxis={"title": "Hop along shortest route", "dtick": 1, "gridcolor": "#263449"},
        yaxis={"visible": False, "range": [-0.7, max(0, len(route_rows) - 0.3)]},
        margin={"l": 40, "r": 40, "t": 90, "b": 80},
        annotations=[{"text": "Endpoints fixed to the same queried R1-R6 and DNg13 neurons. Threshold is a graph filter, not a physiological threshold.",
                      "xref": "paper", "yref": "paper", "x": 0.5, "y": -0.2,
                      "showarrow": False, "font": {"size": 12, "color": "#cbd5e1"}}],
    )
    fig.write_html(OUT / "threshold_comparison.html", include_plotlyjs=True)
    print(f"Saved threshold_comparison.csv and threshold_comparison.html in {OUT.resolve()}")
    print("Interpretation: this tests route stability under edge filtering, not signal transmission or behavior.")


if __name__ == "__main__":
    main()

