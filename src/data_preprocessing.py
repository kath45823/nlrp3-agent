import requests 
import pandas as pd
from rdkit import Chem
from rdkit.Chem.SaltRemover import SaltRemover

def get_data():
    query_params = {
        'target_chembl_id': 'CHEMBL1741208', 
        'standard_type': 'IC50', 
        'assay_type': 'B', 
        'format': 'json',
        'limit': 1000
    }

    chembl_data = []
    offset = 0

    while True: 
        query_params['offset'] = offset
        response = requests.get('https://www.ebi.ac.uk/chembl/api/data/activity', params=query_params)
        data = response.json()
        total = data['page_meta']['total_count']

        for a in data["activities"]:
            smiles = a["canonical_smiles"]
            pic50 = a["pchembl_value"]

            if smiles is None or pic50 is None: 
                continue

            chembl_data.append({'smiles': smiles, 'pIC50': float(pic50)})
        
        offset += 1000
        if offset >= total: 
            break

    df = pd.DataFrame(chembl_data)
    df.to_csv('data/chembl_data.csv', index=False)
    return df

def remove_salts(smiles):
    remover = SaltRemover()
    mol = Chem.MolFromSmiles(smiles)
    if mol is None: 
        return None
    stripped_mol = remover.StripMol(mol)
    return Chem.MolToSmiles(stripped_mol)

def clean_data():
    df = get_data()
    df['smiles'] = df['smiles'].apply(lambda s: Chem.MolToSmiles(Chem.MolFromSmiles(s)))
    df = df.dropna(subset=['smiles'])
    df['smiles'] = df['smiles'].apply(remove_salts)
    df = df.dropna(subset=['smiles'])
    df = df[~df['smiles'].str.contains(r'\.')]
    df = df.groupby('smiles')['pIC50'].median().reset_index()
    return df 
