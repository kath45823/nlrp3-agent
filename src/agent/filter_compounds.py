from src.model.chemprop_model import predict_pic50 
from src.agent.tools import fetch_compounds

def filter_compounds():
    data = fetch_compounds()
    filtered_compounds = []
    
    for smiles in data: 
        score = predict_pic50(smiles)
        if score >= 6: 
            filtered_compounds.append((smiles, score))

    sorted_compounds = sorted(filtered_compounds, key = lambda elt: elt[1], reverse = True)
    sorted_compounds = sorted_compounds[:100]
    top_compounds = [smi for smi, sc in sorted_compounds]

    return top_compounds