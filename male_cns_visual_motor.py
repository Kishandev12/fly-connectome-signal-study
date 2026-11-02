"""Query and animate one real MaleCNS visual-to-motor route.

The animation is an educational activity model on a queried shortest path. It
is not a physiological simulation or a claim about fly behavior.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import plotly.graph_objects as go
from neuprint import Client, NeuronCriteria, fetch_neurons, fetch_shortest_paths

OUT = Path("results/male_cns")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--min-weight", type=int, default=5,
                        help="minimum synapse count required for each path edge")
    parser.add_argument("--timeout", type=float, default=5,
                        help="neuPrint path-query timeout in seconds")
    args = parser.parse_args()

    token = os.environ.get("NEUPRINT_TOKEN")
    if not token:
        raise SystemExit(
            "NEUPRINT_TOKEN is not set. Create a neuPrint account/token, then set it "
            "in this terminal with: $env:NEUPRINT_TOKEN='your-token'"
        )

    OUT.mkdir(parents=True, exist_ok=True)
    client = Client("https://neuprint.janelia.org", dataset="male-cns:v1.0", token=token)
    print("Looking up R1-R6 visual neurons and DNg13 descending neurons in MaleCNS v1.0...")
    sources, _ = fetch_neurons(NeuronCriteria(type="R1-R6"), omit_rois=True, client=client)
    targets, _ = fetch_neurons(NeuronCriteria(type="DNg13"), omit_rois=True, client=client)
    if sources.empty or targets.empty:
        raise SystemExit(
            f"Could not find both cell types (R1-R6: {len(sources)}, DNg13: {len(targets)}). "
            "Check the current dataset annotations in neuPrint."
        )

    # Cap candidate pairs so this remains a small targeted query.
    sources = sources.sort_values("bodyId").head(3)
    targets = targets.sort_values("bodyId").head(3)
    chosen = None
    for source in sources.itertuples(index=False):
        for target in targets.itertuples(index=False):
            paths = fetch_shortest_paths(
                int(source.bodyId), int(target.bodyId), min_weight=args.min_weight,
                timeout=args.timeout, client=client,
            )
            if not paths.empty:
                first_path = paths.loc[paths["path"] == paths["path"].min()].copy()
                first_path = first_path.drop_duplicates("bodyId", keep="first")
                if len(first_path) >= 2:
                    chosen = (source, target, first_path)
                    break
        if chosen:
            break

    if not chosen:
        raise SystemExit(
            "No route found among the sampled R1-R6/DNg13 pairs at this threshold. "
            "Try --min-weight 1 or rerun later; no large dataset was downloaded."
        )

    source, target, path = chosen
    path = path.reset_index(drop=True)
    if "type" not in path:
        path["type"] = "Unannotated"
    path["label"] = path["type"].fillna("Unannotated").astype(str)
    path.loc[0, "label"] = "R1-R6 visual input"
    path.loc[path.index[-1], "label"] = "DNg13 descending output"
    path["step"] = range(len(path))
    OUT.mkdir(parents=True, exist_ok=True)
    path.to_csv(OUT / "queried_path.csv", index=False)

    n = len(path)
    x = list(range(n))
    y = [0.0] * n
    edges_x, edges_y = [], []
    for i in range(n - 1):
        edges_x.extend([x[i], x[i + 1], None])
        edges_y.extend([y[i], y[i + 1], None])
    weights = path["weight"].fillna(0).astype(float).tolist()
    frames = []
    for t in range(n + 2):
        active = min(t, n - 1)
        colors = ["#ffb000" if i <= active else "#334155" for i in range(n)]
        frames.append(go.Frame(
            name=str(t), data=[go.Scatter(marker={"color": colors})],
            layout={"title": f"Illustrative activity pulse — step {t}/{n + 1}"},
            traces=[1],
        ))

    fig = go.Figure(
        data=[
            go.Scatter(x=edges_x, y=edges_y, mode="lines",
                       line={"color": "#64748b", "width": 3}, hoverinfo="skip", showlegend=False),
            go.Scatter(
                x=x, y=y, mode="markers+text", text=path["label"], textposition="top center",
                customdata=[[int(path.loc[i, "bodyId"]), weights[i]] for i in range(n)],
                hovertemplate="%{text}<br>body ID %{customdata[0]}<br>incoming edge: %{customdata[1]} synapses<extra></extra>",
                marker={"size": 30, "color": ["#334155"] * n,
                        "line": {"color": "#e2e8f0", "width": 2}}, showlegend=False,
            ),
        ],
        frames=frames,
        layout=go.Layout(
            title="MaleCNS visual-to-motor route", paper_bgcolor="#0b1220", plot_bgcolor="#0b1220",
            font={"color": "#e2e8f0", "size": 14},
            xaxis={"visible": False, "range": [-0.6, n - 0.4]},
            yaxis={"visible": False, "range": [-0.8, 1.0]},
            margin={"l": 30, "r": 30, "t": 80, "b": 40},
            annotations=[{"text": "Real MaleCNS shortest-path wiring • pulse timing is illustrative",
                          "xref": "paper", "yref": "paper", "x": 0.5, "y": -0.08,
                          "showarrow": False, "font": {"color": "#cbd5e1", "size": 12}}],
            updatemenus=[{"type": "buttons", "showactive": False, "x": 0.02, "y": 1.15,
                          "buttons": [
                              {"label": "▶ Play", "method": "animate", "args": [None, {"frame": {"duration": 650, "redraw": True}, "fromcurrent": True}]},
                              {"label": "↺ Reset", "method": "animate", "args": [["0"], {"frame": {"duration": 0, "redraw": True}, "mode": "immediate"}]},
                          ]}],
            sliders=[{"active": 0, "x": 0.22, "len": 0.75, "y": 0,
                       "steps": [{"method": "animate", "label": str(i),
                                  "args": [[str(i)], {"mode": "immediate", "frame": {"duration": 0, "redraw": True}}]}
                                 for i in range(n + 2)]}],
        ),
    )
    fig.write_html(OUT / "male_cns_visual_motor.html", include_plotlyjs=True)
    print(f"Path found: {len(path)} neurons; source bodyId={int(source.bodyId)}, target bodyId={int(target.bodyId)}")
    print(f"Saved interactive animation and path table under {OUT.resolve()}")
    print("This is a small connectome query plus an illustrative activity model, not a full-brain simulation.")


if __name__ == "__main__":
    main()

