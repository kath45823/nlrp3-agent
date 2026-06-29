import requests
from src.model.chemprop_model import predict_pic50 

def get_data():
    query_params = {
        "format": "json",
        "limit": 1000,
        "molecule_properties__num_ro5_violations": 0,
        "molecule_type": "Small molecule",
    }

    chembl_data = []
    offset = 0
    MAX_COMPOUNDS = 2000

    while len(chembl_data) < MAX_COMPOUNDS:
        query_params["offset"] = offset
        response = requests.get(
            "https://www.ebi.ac.uk/chembl/api/data/molecule", params=query_params
        )
        data = response.json()
        total = data["page_meta"]["total_count"]

        for m in data["molecules"]:
            struct = m["molecule_structures"]
            if not struct: 
                continue

            smiles = struct["canonical_smiles"]

            if smiles is None:
                continue

            chembl_data.append(smiles)

        offset += 1000
        if offset >= total:
            break

    return chembl_data[:MAX_COMPOUNDS]

def filter_compounds():
    data = get_data()
    filtered_compounds = []
    
    for smiles in data: 
        score = predict_pic50(smiles)
        if score >= 6: 
            filtered_compounds.append((smiles, score))

    sorted_compounds = sorted(filtered_compounds, key = lambda elt: elt[1], reverse = True)
    sorted_compounds = sorted_compounds[:100]
    top_compounds = [smi for smi, sc in sorted_compounds]

    return top_compounds