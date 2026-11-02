# MaleCNS visual-to-motor pathway project

## Question

How does the shortest connectome route from a visual input neuron (R1-R6) to a descending neuron (DNg13) change when we ignore connections with fewer synapses?

## What the project does

The first script queries two annotated neurons and asks neuPrint for a shortest path between them. In the run currently captured in `results/male_cns/queried_path.csv`, the route was:

**R1-R6 → L2 → TmY3 → LPLC4 → AN06B009 → DNg13**

The reported edge counts along that route were 6, 6, 11, 6, and 10 synapses. These counts describe reconstructed graph connections for this chosen pair. They are not direct measurements of synaptic efficacy.

The HTML animation turns the route into a visual pulse. Its timing and the successive yellow highlights are for teaching; the program does not simulate membrane voltage, neurotransmitter dynamics, or real firing measurements.

The second script keeps the same R1-R6 and DNg13 body IDs fixed, then asks for shortest routes with minimum edge weights of 1, 5, 10, and 15 synapses. Comparing those routes shows how robust the graph path is to filtering weak edges. A threshold here is a data-selection rule, not a biological firing threshold.

## First threshold-sensitivity result

For the saved endpoint pair, the queried route changed across the two thresholds where a route was found:

| Minimum synapses on every edge | Shortest route | Hops |
| ---: | --- | ---: |
| 1 | R1-R6 → L2 → Dm17 → 5-HTPMPV03 → DNg13 | 4 |
| 5 | R1-R6 → L2 → TmY3 → LPLC4 → AN06B009 → DNg13 | 5 |
| 10 | No route found | — |
| 15 | No route found | — |

The threshold-1 route uses edge counts 4, 5, 1, and 1. The threshold-5 route uses 6, 6, 11, 6, and 10. In this pair, the shortest-path result is sensitive to weak-edge filtering: requiring at least five synapses removes the four-hop route, and the returned route has different intermediate cell types and one extra hop. At thresholds 10 and 15, the query found no route under its traced-neuron path criteria. This is a graph-structure observation for one endpoint pair, not evidence that a living fly's signal must travel along either route.

## Run the threshold comparison

From the project folder, with a valid neuPrint token set in the terminal:

```cmd
python compare_male_cns_thresholds.py
```

To try a different set of edge filters:

```cmd
python compare_male_cns_thresholds.py --thresholds 1 3 5 8 12 20
```

The script saves `threshold_comparison.csv` and `threshold_comparison.html` under `results/male_cns/`. A missing route at a high threshold is informative: it means no path survived that filter within neuPrint's traced-neuron path search.

## Limitations

- This is one selected pair and a shortest-path query, not a whole-brain simulation.
- Shortest paths describe graph structure; they do not prove that signals follow that route in a living fly.
- Edge weights count synaptic contacts and are not calibrated physiological strengths.
- Cell-type annotations, reconstruction completeness, and query thresholds can affect the result.
- The animated pulse is a schematic visualization, not a neural dynamics model.

## CV description (edit after completing the comparison)

> Built a Python connectomics visualization using Janelia's MaleCNS neuPrint API; queried a visual-to-descending-neuron route and analyzed shortest-path stability under synapse-count filtering. Presented connectome-derived structure separately from the illustrative activity animation.

## Data and attribution

The MaleCNS dataset is released under CC-BY. Cite the dataset and its authors when sharing derived figures or tables. The project code is independent and does not reproduce the full connectome locally.

- [Janelia Male CNS Connectome](https://www.janelia.org/project-team/flyem/male-cns-connectome)
- [MaleCNS download and API instructions](https://male-cns.janelia.org/download/)
- [neuPrint Python query documentation](https://connectome-neuprint.github.io/neuprint-python/docs/queries.html)

