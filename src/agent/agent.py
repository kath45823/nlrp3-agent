from openai import OpenAI
import json
from src.agent.tools import fetch_compounds, fetch_similar_compounds, dock_compound

tools = [
    {
        "type": "function", 
        "function": {
            "name": "fetch_compounds",
            "description": (
                "Fetch an initial pool of drug-like small-molecule compounds from ChEMBL to screen "
                "against NLRP3. Returns a list of SMILES strings for candidate molecules that pass "
                "basic drug-likeness filters (Lipinski's rule of five). Call this once at the start "
                "of a screening campaign to get your initial set of compounds to evaluate."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function", 
        "function": {
            "name": "fetch_similar_compounds",
            "description": (
                "Fetch compounds structurally similar to a given reference compound from ChEMBL "
                "(70% Tanimoto similarity). Returns a list of SMILES strings. Use this to explore "
                "chemical space around a promising hit: when a compound docks well, call this with "
                "that compound's SMILES to find related molecules that may also be strong binders. "
                "This is how you investigate a promising scaffold in more depth."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "ref_smi": {
                        "type": "string",
                        "description": (
                            "The SMILES string of the reference compound to find similar molecules to. "
                            "Typically a compound that has already docked well and is worth exploring around."
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