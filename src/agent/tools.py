import requests
from urllib.parse import quote
from vina import Vina
from src.data_processing.parse_pdb import get_coords
from src.agent.docking import prepare_ligand

COORDS = get_coords()

def fetch_compounds():
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

def fetch_similar_compounds(ref_smi):
    ref_smi_url = quote(ref_smi, safe = '')
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
             f"https://www.ebi.ac.uk/chembl/api/data/similarity/{ref_smi_url}/70", params=query_params
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

def dock_compound(smi):
    pdbqt_str = prepare_ligand(smi)
    if pdbqt_str is None: 
        return 
    v = Vina(sf_name="vina")

    v.set_receptor("data/9GU4-receptor.pdbqt")
    v.set_ligand_from_string(pdbqt_str)
    v.compute_vina_maps(center=list(COORDS), box_size=[20, 20, 20])
    v.dock(exhaustiveness=8, n_poses=3)

    return v.energies()[0][0]