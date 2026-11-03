# MaleCNS visual-to-motor route sensitivity

## Project question

For one annotated visual neuron and one descending neuron in the MaleCNS connectome, does the shortest graph route stay the same when weak connections are excluded?

## Result at a glance

Using the same queried endpoints for every condition (R1-R6 body ID **11139** and DNg13 body ID **11074**), the shortest route changed when the minimum synapse count per edge increased from 1 to 5. No route was returned at thresholds 10 or 15.

### Minimum 1 synapse per edge — 4 hops

```mermaid
flowchart LR
    A[R1-R6] -->|4 synapses| B[L2]
    B -->|5 synapses| C[Dm17]
    C -->|1 synapse| D[5-HTPMPV03]
    D -->|1 synapse| E[DNg13]
```

### Minimum 5 synapses per edge — 5 hops

```mermaid
flowchart LR
    A[R1-R6] -->|6 synapses| B[L2]
    B -->|6 synapses| C[TmY3]
    C -->|11 synapses| D[LPLC4]
    D -->|6 synapses| E[AN06B009]
    E -->|10 synapses| F[DNg13]
```

| Minimum synapses on every edge | Route returned? | Hops |
| ---: | :--- | ---: |
| 1 | Yes | 4 |
| 5 | Yes | 5 |
| 10 | No | — |
| 15 | No | — |

## Interpretation

For this endpoint pair, the four-hop path includes edges with one synapse. Requiring at least five synapses per edge removes that route, and the shortest route returned by neuPrint uses different intermediate cell types and one additional hop. At thresholds 10 and 15, no route was found under the query's traced-neuron path criteria.

This is a result about graph structure and a chosen edge filter. It does not show that neural activity follows either path in a living fly. Synapse counts are not calibrated synaptic strengths, and the filter values are not physiological firing thresholds. “No route found” is limited to this query and its annotations/completeness criteria; it should not be read as proof of no biological communication.

## How it was done

The project queried the MaleCNS v1.0 dataset through neuPrint. It selected a shortest route from R1-R6 to DNg13 at each minimum edge weight, while holding the queried endpoint body IDs fixed. This is a small targeted query; it does not load or simulate the full 166,000-neuron CNS.

The separate HTML pulse animation is a schematic teaching aid. Its timing and node highlights are illustrative, not a model of membrane voltage, neurotransmitter kinetics, or recorded firing.

The showcase page also contains a toy Monte Carlo comparison: it runs 5,000 pulses along each returned route, assigning each edge a pass probability of `1 - exp(-synapse_count / scale)`. The scale is an adjustable, arbitrary parameter. This explores how a hypothetical transmission rule interacts with the two route weight lists; it is not a calibrated neural model and must not be presented as a biological estimate.

## Reproduce

From this project folder, with a current neuPrint API token set privately in the terminal:

```cmd
python compare_male_cns_thresholds.py
```

The script writes a detailed CSV and interactive HTML chart under `results/male_cns/`. Use `python compare_male_cns_thresholds.py --thresholds 1 3 5 8 12 20` to explore other filters. Do not commit or share your API token.

## CV-ready description

> Built a Python connectomics analysis using Janelia's MaleCNS neuPrint API; queried a visual-to-descending-neuron route, evaluated shortest-path sensitivity to synapse-count filtering, and added an interactive Monte Carlo toy model while distinguishing graph data from uncalibrated simulation assumptions.

## Data source and attribution

The MaleCNS dataset is licensed CC-BY. Cite the dataset and its authors when presenting this analysis. See the [Janelia Male CNS Connectome page](https://www.janelia.org/project-team/flyem/male-cns-connectome) and [official download/API instructions](https://male-cns.janelia.org/download/).

