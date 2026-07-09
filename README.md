# NLRP3 Inhibitor Discovery Agent

An autonomous computational drug discovery agent that screens small-molecule libraries for candidate inhibitors of **NLRP3**, an inflammasome protein implicated in gout, Alzheimer's disease, atherosclerosis, and a range of other inflammatory conditions.

The system combines a trained bioactivity model, molecular docking, and an LLM-driven agent that orchestrates the screening process — deciding which compounds to evaluate, when to explore promising chemical scaffolds more deeply, and when it has gathered enough strong candidates to stop.

---

## Overview

NLRP3 is a master regulator of the inflammasome. When it misfires — in response to uric acid crystals, cholesterol crystals, or amyloid-beta plaques — it drives runaway inflammation. Blocking NLRP3 is therefore an attractive therapeutic strategy across many diseases at once. This project targets the **NACHT domain's ATP-binding pocket**, the site where the clinical inhibitor MCC950 acts by locking NLRP3 in its inactive conformation.

The pipeline screens drug-like compounds for their predicted ability to bind this pocket, using a cheap-to-expensive cascade: a fast machine-learning activity filter narrows a large pool down to likely-active compounds, and physics-based molecular docking then evaluates how well each survivor fits the binding site.

On top of this validated screening pipeline sits an **agent layer** — an LLM that orchestrates the screen by making genuine runtime decisions rather than following a fixed script.

---

## Target and structure

| Property | Detail |
|---|---|
| Target | NLRP3 (NACHT, LRR and PYD domains-containing protein 3) |
| Binding site | NACHT domain ATP-binding pocket |
| Structure | PDB **9GU4** (2.70 Å, human NLRP3, 2024) |
| Co-crystallized ligands | ADP (confirms autoinhibited conformation) and NP3-253 (inhibitor) |
| Binding box center | x = 17.215, y = 35.494, z = −6.361 (from NP3-253 centroid) |
| Box size | 22 × 22 × 22 Å |

The receptor was prepared by converting the mmCIF structure to PDB, filling missing residues and adding hydrogens at physiological pH, stripping all heteroatoms and waters, and converting to PDBQT format for docking.

---

## Pipeline architecture

The screening pipeline runs as a cascade from cheap, fast filters to expensive, precise evaluation:

**1. Compound fetching** — Drug-like small molecules are retrieved from the ChEMBL database, filtered server-side for Lipinski's Rule of Five compliance.

**2. Bioactivity pre-filtering** — A trained Chemprop model predicts each compound's NLRP3 activity (pIC50). Only compounds predicted to be active (pIC50 ≥ 6.0) proceed, and the pool is narrowed to the top candidates. This cheap filter is what makes docking tractable at scale — it discards likely-inactive compounds before any expensive computation.

**3. Molecular docking** — Surviving compounds are docked into the NACHT pocket with AutoDock Vina, producing a binding affinity score in kcal/mol (more negative = stronger predicted binding).

**4. Ranking** — Compounds are ranked by docking score to produce a final candidate list.

---

## The agent layer

A key design decision in this project was distinguishing where an autonomous agent genuinely adds value versus where a fixed pipeline is the correct, simpler choice.

A fixed pipeline runs the same sequence every time and cannot react to intermediate results. The agent is justified only because drug screening contains **real runtime decisions** whose right answer depends on what the screen discovers along the way:

- **Adaptive stopping** — The agent tracks its results as they arrive and decides when it has enough strong hits to stop, rather than exhaustively docking a fixed number of compounds. This conserves expensive docking computation.

- **Scaffold exploration** — When a compound docks well, the agent can decide to fetch structurally similar compounds (via ChEMBL similarity search) and screen those too — mirroring how medicinal chemists investigate promising chemical series. Which scaffolds get explored depends entirely on what scored well during the run, something impossible to hardcode.

The agent is implemented directly with the LLM provider's tool-calling API (no heavyweight agent framework), keeping the reasoning loop transparent. It exposes three tools — `fetch_compounds`, `fetch_similar_compounds`, and `dock_compound` — each mapping to a genuine decision. Quantitative operations (scoring, ranking) are deliberately kept in deterministic code rather than trusted to the LLM, since sorting and arithmetic are exactly what language models do unreliably.

---

## Validation

The docking setup was validated by **redocking known ligands** and confirming it reproduces their established binding — a standard, rigorous test of a docking protocol. The receptor, binding box, and docking parameters were verified before any screening results were trusted.

| Validation | Result | Interpretation |
|---|---|---|
| NP3-253 redocking score | **−10.14 kcal/mol** | Strong binding, as expected for the co-crystallized inhibitor |
| NP3-253 pose RMSD to crystal | **1.98 Å** | Below the 2.0 Å threshold — docking reproduces the true crystal binding mode |
| MCC950 docking score | **−8.79 kcal/mol** | Strong binding for a structurally distinct known inhibitor |

The **1.98 Å RMSD** is the headline validation result. Redocking the co-crystallized ligand NP3-253 and recovering its crystal pose to within 2 Å confirms that the docking protocol correctly reproduces known binding — meaning the receptor preparation, binding box coordinates, and docking parameters are all sound. The strong, physically reasonable scores for both NP3-253 and the structurally different MCC950 provide additional confidence that the pocket is set up correctly and the pipeline discriminates real binders.

### Bioactivity model

The Chemprop bioactivity model was trained on curated NLRP3 IC50 data from ChEMBL (~700 compounds after cleaning: canonicalization, salt/mixture removal, deduplication by median pIC50, and filtering of extreme values). It was evaluated with a scaffold split, which holds out structurally distinct chemistry in the test set for an honest estimate of generalization to novel compounds.

The model achieves modest absolute accuracy (R² ≈ 0.4, RMSE ≈ 1.0 pIC50 units on the scaffold test set), which reflects a genuine ceiling imposed by the limited quantity of public NLRP3 bioactivity data and inherent assay noise, rather than a modeling flaw. Critically, the model still functions effectively as a **screening pre-filter** — its role in the pipeline is to rank likely-active compounds above inactive ones so docking effort is focused on promising candidates, and it enriches for actives above random. Absolute pIC50 accuracy is less important for this use than ranking ability.

#### Enrichment factor analysis

Because raw accuracy (R²) is not the metric that matters for a pre-filter, the model was evaluated by **enrichment factor** — the metric that directly measures its actual job. Compounds with pIC50 ≥ 6.0 were labeled active (the standard cutoff for a "hit"), and the enrichment factor asks: within the top slice of the model's ranking, how many true actives appear compared to what random selection would yield?

$$\text{EF at top X\%} = \frac{\text{fraction of actives found in the top X\%}}{\text{fraction expected by random chance}}$$

An EF of 1.0 means the model is no better than random; higher values mean the model concentrates true actives near the top of its ranking.

| Metric | Value | Interpretation |
|---|---|---|
| EF at top 1% | **3.23** | Actives appear at ~3.2× the random rate in the top 1% |
| EF at top 5% | **1.94** | ~1.9× enrichment in the top 5% |
| EF at top 10% | **1.94** | ~1.9× enrichment in the top 10% |

Every value is above 1.0, confirming the model ranks true actives above inactives better than chance at every level — exactly the behavior needed for a screening pre-filter. The enrichment is strongest at the very top of the ranking (3.2× in the top 1%) and dilutes toward random as the net widens, which is the expected and desirable pattern for a working model. These results confirm that despite modest absolute accuracy, the model does its actual job — prioritizing promising compounds for the expensive docking stage — well enough to be useful. (The top-1% figure is computed over a small test set and is therefore indicative; the more stable top-10% enrichment is the better number to rely on.)

---

## Tech stack

| Layer | Tools |
|---|---|
| Structure prep | PDBFixer (OpenMM), ADFR Suite, PyMOL |
| Docking | AutoDock Vina, Meeko (ligand prep) |
| Cheminformatics | RDKit |
| Bioactivity model | Chemprop (D-MPNN), PyTorch |
| Data sources | ChEMBL |
| Agent | LLM tool-calling (OpenAI-compatible API; Gemini Flash) |
| Language | Python 3.11 |

---

## Project structure

```
nlrp3-agent/
├── data/                          # structures, prepared receptor, ligands, ChEMBL data
│   ├── 9GU4.cif                   # raw crystal structure
│   ├── 9GU4-cleaned.pdb           # cleaned receptor
│   ├── 9GU4-receptor.pdbqt        # docking-ready receptor
│   ├── 9gu4_B_A1IPJ.sdf           # NP3-253 crystal pose (box coords + validation)
│   └── chembl_data.csv            # bioactivity training data
├── src/
│   ├── agent/
│   │   ├── agent.py               # LLM agent loop and tool dispatch
│   │   ├── tools.py               # fetch_compounds, fetch_similar_compounds
│   │   └── filter_compounds.py    # Chemprop activity pre-filter
│   ├── data_processing/
│   │   └── parse_pdb.py           # binding box centroid extraction
│   ├── model/
│   │   ├── chemprop_model_training.ipynb   # model development + evaluation
│   │   └── chemprop_model.py      # trained model inference (predict_pic50)
│   └── validation/
│       └── docking_validation.py  # redocking RMSD + score validation
├── main.py                        # entry point — runs the full project
├── requirements.txt               # Python dependencies
└── README.md
```

---

## Running the project

The entire project runs from a single entry point:

```bash
python main.py
```

This executes the full workflow — fetching and pre-filtering compounds, docking, and running the agent-orchestrated screen.

### Setup

**1. Create the environment**

```bash
conda create -n nlrp3 python=3.11
conda activate nlrp3
```

**2. Install conda-only dependencies**

A few cheminformatics packages install most reliably through conda rather than pip:

```bash
conda install -c conda-forge rdkit
```

**3. Install the remaining dependencies from requirements.txt**

```bash
pip install -r requirements.txt
```

**4. Set your Gemini API key**

The agent uses the Gemini API (free tier). Create a key at [Google AI Studio](https://aistudio.google.com), then create an `.env` file in the project root:

```
GEMINI_API_KEY=your-key-here
```

The project reads the key from the `GEMINI_API_KEY` environment variable — it must be set before running, or the agent will fail to authenticate.

To validate the docking setup independently:

```bash
python -m src.validation.docking_validation
```

---

## Design notes and honest limitations

This project was built with an emphasis on doing the science correctly and being honest about what each component can and cannot claim.

- **The docking pipeline is rigorously validated** (1.98 Å redocking RMSD), so binding scores it produces are trustworthy relative rankings.

- **The bioactivity model is a deliberately-scoped pre-filter**, not a precise activity oracle. Its modest R² reflects the real limits of available public NLRP3 data, and it is used for ranking (its strength) rather than exact prediction.

- **The agent adds value only where genuine decisions exist** — adaptive stopping and scaffold exploration. Quantitative scoring and ranking are kept in deterministic code, since those are operations language models perform unreliably.

- **Docking scores estimate binding, not efficacy.** Top hits from this pipeline are computational starting points that would require experimental validation (synthesis, biochemical assays, and beyond) before being considered genuine leads. The value of the pipeline is in dramatically narrowing the search space, not in producing finished drugs.

---

## Future work

- Hit-list characterization: scaffold diversity clustering and novelty analysis versus known NLRP3 inhibitors.
- Expanded screening library (scaling from a development-sized pool to a larger production screen).
- ADMET assessment of top hits (toxicity, metabolic stability, permeability) via pretrained models.
- Extending the agent to natural-language screening constraints (e.g. "avoid reactive functional groups").