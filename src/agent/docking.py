from src.agent.filter_compounds import filter_compounds
from src.agent.tools import dock_compound


# Base Pipeline
def get_docking_scores():
    compounds = filter_compounds()
    results = []

    for smi in compounds:
        try:
            score = dock_compound(smi)
            results.append((smi, score))
        except Exception as e:
            print(f"Docking failed for {smi}: {e}")
            continue

    return results
