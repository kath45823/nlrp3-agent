import requests 

query_params = {
    'target_chembl_id': 'CHEMBL1741208', 
    'standard_type': 'IC50', 
    'assay_type': 'B', 
    'format': 'json',
    'limit': 1000
}

response = requests.get('https://www.ebi.ac.uk/chembl/api/data/activity', params=query_params)
data = response.json()
chembl_data = []

for a in data["activities"]:
    smiles = a["canonical_smiles"]
    pic50 = a["pchembl_value"]

    if smiles is None or pic50 is None: 
        continue

    chembl_data.append({'smiles': smiles, 'pIC50': pic50})

print(len(chembl_data))

