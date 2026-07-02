from openai import OpenAI
import json
from src.agent.tools import fetch_compounds, fetch_similar_compounds, dock_compound, predict_pic50

tools = [
    {
        "type": "function",
        "function": {
            "name": "fetch_compounds",
            "description": (
                "Fetch an initial pool of drug-like small-molecule compounds to screen against "
                "NLRP3. Returns a list of SMILES strings for candidate molecules that pass basic "
                "drug-likeness filters and have been pre-screened for predicted NLRP3 activity. "
                "Call this once at the start of a screening campaign."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_similar_compounds",
            "description": (
                "Fetch compounds structurally similar to a given reference compound (70% Tanimoto "
                "similarity), pre-screened for predicted NLRP3 activity. Returns a list of SMILES "
                "strings. Use this to explore chemical space around a promising hit: when a compound "
                "docks well, call this with its SMILES to find related molecules that may also be "
                "strong binders. This is how you investigate a promising scaffold in more depth."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "ref_smi": {
                        "type": "string",
                        "description": (
                            "The SMILES string of the reference compound to find similar molecules "
                            "to. Typically a compound that has already docked well."
                        )
                    }
                },
                "required": ["ref_smi"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "dock_compound",
            "description": (
                "Dock a single compound into the NLRP3 NACHT binding pocket using AutoDock Vina and "
                "return its predicted binding affinity in kcal/mol. More negative scores indicate "
                "stronger predicted binding: scores below -8.0 are strong hits, -7 to -8 are moderate, "
                "and above -6 are weak. For reference, the known NLRP3 inhibitor MCC950 scores around "
                "-7.4 in this pocket. Returns null if the compound cannot be prepared for docking. "
                "This is the main tool for evaluating whether a compound binds NLRP3."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "smi": {
                        "type": "string",
                        "description": "The SMILES string of the compound to dock into the NLRP3 pocket."
                    }
                },
                "required": ["smi"]
            }
        }
    }
]

SYSTEM_PROMPT = """You are a computational drug discovery agent screening for small-molecule inhibitors of NLRP3, an inflammasome protein implicated in gout, Alzheimer's, atherosclerosis, and other inflammatory diseases. Your goal is to identify promising candidate compounds that bind to the NACHT domain's ATP-binding pocket, which locks NLRP3 in its inactive state.

## Your tools

- `fetch_compounds`: retrieves a pool of drug-like candidate compounds, already pre-screened for predicted NLRP3 activity. Call this once at the start.
- `dock_compound`: docks a single compound (by SMILES) into the NLRP3 NACHT pocket and returns its binding affinity in kcal/mol. This is your primary evaluation tool.
- `fetch_similar_compounds`: given a reference compound's SMILES, returns structurally similar compounds (also pre-screened for activity). Use this to explore around promising hits.

## Interpreting docking scores

Scores are binding affinities in kcal/mol — more negative means stronger predicted binding:
- Below -8.0: strong hit, promising
- -7.0 to -8.0: moderate binder
- Above -6.0: weak, likely not a real hit

For reference, MCC950 (a known NLRP3 inhibitor) scores around -7.4 in this pocket. A compound scoring better than -7.4 is competitive with a known inhibitor.

## Your workflow

1. Call `fetch_compounds` to get your pre-screened candidate pool.
2. Dock compounds one at a time with `dock_compound`, working through the pool. Track which score well (below -8.0 kcal/mol) — these are your hits.
3. When you find a strong hit, consider calling `fetch_similar_compounds` on it to explore that chemical scaffold, then dock those neighbors too. Promising scaffolds are worth investigating in depth.
4. Continue until you have at least 5 strong hits (below -8.0), OR until you have docked roughly 30 compounds. Do not exhaustively dock the entire pool — stop once you have enough good candidates.

## Decisions you must make

- **When to stop**: after each dock, assess how many strong hits you have. Stop at 5 strong hits or your docking budget. Don't dock indefinitely.
- **When to explore a scaffold**: if a compound docks notably well, decide whether to fetch and dock its structural neighbors to find even better binders in that series.

## Rules

- Never dock the same compound twice — track what you've already scored.
- If `dock_compound` reports a failure, skip that compound and move on.
- Be efficient with docking calls; each one is computationally expensive.

## Final output

When you stop, produce a ranked list of your best candidates (up to 5-10), each with:
- The SMILES string
- Its docking score
- A one-sentence rationale (e.g. "strong binder at -8.6 kcal/mol, better than the MCC950 reference; found by exploring the scaffold of an earlier hit")

Note which hits were found by direct screening versus scaffold exploration. Present the final list clearly as your conclusion."""

client = OpenAI()
messages = [
    {"role": "system", "content": SYSTEM_PROMPT},
    {"role": "user", "content": "Find promising NLRP3 inhibitor candidates."}
]

while True:
    response = client.chat.completions.create(
        model = "gpt-4o",
        messages = messages,
        tools = tools,
        tool_choice = "auto"
    )
    msg = response.choices[0].message
    messages.append(msg)

    if msg.tool_calls is None: 
        print(msg.content)
        break

    for call in msg.tool_calls:
        name = call.function.name
        args = json.loads(call.function.arguments)

        if name == "fetch_compounds":
            result = fetch_compounds()
        elif name == "fetch_similar_compounds":
            result = fetch_similar_compounds(args["ref_smi"])  
        elif name == "dock_compound":
            score = dock_compound(args["smi"])
            result = score if score is not None else "docking failed - compound could not be prepared"
        
        tool_message = {
            "tool_call_id": call.id, 
            "role": "tool",
            "name": name,
            "content": json.dumps(result)
        }

        messages.append(tool_message)