# Does fly brain wiring shape signal spread?

A reproducible computational neuroscience project exploring signal propagation in the adult *Drosophila* connectome. The project uses public FlyWire FAFB v783 connectivity and adapts leaky integrate-and-fire (LIF) model choices from Shiu et al. (2024).

> **Scope:** The reported simulations use small, strongest-link two-hop subnetworks. They are not whole-brain simulations and do not measure real neural activity. A full-connectome analysis is the next development phase.

## Question

In a sampled visual circuit around a cholinergic cM15 neuron, does measured wiring recruit more simulated downstream activity than degree-preserving rewired wiring?

## Current result

Across 10 paired trials at each of three nested sample sizes, the measured wiring produced more active downstream neurons in all 30 pairs. The mean paired gain was 22.7, 29.6, and 50.8 active neurons for samples containing 412, 1,338, and 2,600 neurons. As a share of sampled neurons, the gain was 5.5%, 2.2%, and 2.0%, respectively. The result is specific to the chosen neuron, sampling rule, and simplified model; it is not biological evidence.

![Measured and rewired network comparison at three sample sizes](results/lif/sample_size_sensitivity.png)

See the [preliminary report](results/PRELIMINARY_REPORT.md), [sensitivity summary table](results/lif/sample_size_sensitivity.csv), and per-size comparison plots in `results/lif/`.

## Reproduce

### Requirements

Python 3.11 or newer is recommended. Install the listed packages:

```powershell
python -m pip install -r requirements.txt
```

### Data setup

Large connectome and annotation files are intentionally not stored in this repository. Download the v783 files from the [Shiu et al. model repository](https://github.com/philshiu/Drosophila_brain_model) and put them at:

- `data/Connectivity_783.parquet`
- `data/Completeness_783.csv`
- `data/annotations/neuron_annotations.tsv`

The FlyWire connectome data have separate terms from this repository's code; see [DATA_LICENSE.md](DATA_LICENSE.md). Use the data for noncommercial purposes and provide the required attribution.

### Run the paired sample-size study

From the project directory:

```powershell
python run_sensitivity.py --runs 10
```

This builds 50×10, 100×20, and 150×30 strongest-link samples, runs paired measured/rewired simulations with matched stimulus seeds, and writes summary tables and plots under `results/lif/`. Run `python run_project.py` for the default 100×20 analysis.

## Project layout

- `simulate_visual_hub.py` — streams the large connectivity table in batches and simulates sampled circuits.
- `male_cns_visual_motor.py` / `compare_male_cns_thresholds.py` — query and visualize a MaleCNS visual-to-motor route and compare shortest paths under edge-weight filters.
- `MALECNS_PROJECT_NOTE.md` — beginner-friendly explanation, limitations, attribution, and a draft CV description for the MaleCNS extension.
- `simulate_whole_brain.py` — experimental full-v783 LIF pilot that streams connections into disk-backed numeric arrays and adds Brian2 synapses in bounded chunks. It may still need several GB of available memory and can be slow on the NumPy backend.
- `run_sensitivity.py` — automates three sample sizes.
- `run_project.py` / `run_project.bat` — one-command default pipeline / Windows launcher.
- `analyze_connectome.py`, `label_hubs.py`, `compare_superclasses.py`, `inspect_visual_hubs.py` — connectome structure and annotation analyses.
- `summarize_spikes.py`, `compare_network_conditions.py` — summarize and compare simulation results.
- `reference-model/` — upstream Shiu et al. model source files with its license notice.
- `results/` — report, plots, and compact summary outputs; large raw inputs and event-level outputs are excluded.

## New direction: animate a MaleCNS visual-to-motor pathway

The current project uses the adult female FlyWire dataset. To explore the newer male CNS connectome, `male_cns_visual_motor.py` makes a small targeted query to Janelia's neuPrint service for a shortest route from an R1-R6 visual neuron to a DNg13 descending neuron. It then creates a self-contained interactive HTML animation and a CSV of the queried route. The wiring and synapse counts come from MaleCNS; the moving pulse is an illustrative model, not measured neural activity.

Install the added dependencies if needed:

```powershell
python -m pip install neuprint-python plotly
```

Create a neuPrint account and API token at [neuPrint](https://neuprint.janelia.org/). Keep the token private and set it only in your local terminal. In PowerShell:

```powershell
$env:NEUPRINT_TOKEN = 'paste-your-token-here'
python male_cns_visual_motor.py
```

In Command Prompt, use:

```cmd
set "NEUPRINT_TOKEN=paste-your-token-here"
python male_cns_visual_motor.py
```

Open `results/male_cns/male_cns_visual_motor.html` in a browser. If no route is found with the default minimum edge weight, try `python male_cns_visual_motor.py --min-weight 1`. Then compare the same selected endpoints under several connection filters:

```powershell
python compare_male_cns_thresholds.py
```

Open `results/male_cns/threshold_comparison.html` to inspect the routes; the accompanying CSV lists each route and its edge weights. The script queries at most a few candidate cell pairs for the first route and does not download the full connectome. Generated route files are ignored by Git. See [MALECNS_PROJECT_NOTE.md](MALECNS_PROJECT_NOTE.md) for the study question, interpretation, limitations, and a CV-ready description.

The MaleCNS dataset is licensed CC-BY; cite the dataset and authors when sharing derived results. See [DATA_LICENSE.md](DATA_LICENSE.md) and the [official download page](https://male-cns.janelia.org/download/).

See [MALECNS_RESULTS.md](MALECNS_RESULTS.md) for the observed route comparison, interpretation, reproducibility steps, and a CV-ready summary. The interactive chart and detailed CSV are generated locally under `results/male_cns/` and are excluded from Git; the key results are reproduced in the Markdown report for GitHub readers.

A self-contained, no-install showcase page is available at [`docs/index.html`](docs/index.html). Open it in a browser for a compact visual overview of the project; it contains no API token and needs no server or external JavaScript libraries.

## Experimental full-brain attempt (resource-heavy)

The earlier FlyWire v783 data contain connectivity for about 138,639 neurons and more than 15 million directed neuron-pair connections. `simulate_whole_brain.py` is an experimental full-brain Brian2 attempt. It exceeded available memory on the project computer in previous runs. It remains here for future optimization; the targeted MaleCNS demo above is the practical next step on a memory-limited laptop.

If you specifically want to retry the full FlyWire run later, it can be started with:

```powershell
python simulate_whole_brain.py --duration-ms 200
```

This is a resource-intensive exploratory run, and it may still fail or take a long time. The small-subnetwork result remains a baseline, not a claim that full-brain scaling is solved.

## Sources and attribution

- Shiu et al. (2024), “A Drosophila computational brain model reveals sensorimotor processing,” *Nature*. [Paper](https://doi.org/10.1038/s41586-024-07763-9) · [Code](https://github.com/philshiu/Drosophila_brain_model)
- Dorkenwald et al. (2024), “Neuronal wiring diagram of an adult brain,” *Nature*. [Paper](https://doi.org/10.1038/s41586-024-07558-y)
- Schlegel et al. (2024), “Whole-brain annotation and multi-connectome cell typing of Drosophila,” *Nature*. [Paper](https://doi.org/10.1038/s41586-024-07686-5)
- FlyWire public release v783 [data and citation guidelines](https://join.flywire.ai/guidelines)

This is an independent educational project and is not affiliated with or endorsed by Google DeepMind, FlyWire, Princeton University, or the authors of the reference model.

