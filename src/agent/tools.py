import requests
from urllib.parse import quote
from vina import Vina
from src.data_processing.parse_pdb import get_coords
from src.agent.docking import prepare_ligand
from src.model.chemprop_model import load_model
import torch
from chemprop import data, featurizers, models
import os

CKPT_PATH = os.path.join(os.path.dirname(__file__), "nlrp3-model", "nlrp3_chemprop.ckpt")
MODEL = None
FEATURIZER = featurizers.SimpleMoleculeMolGraphFeaturizer()
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

def predict_pic50(smi):
    model = load_model()

    try:
        dp = data.MoleculeDatapoint.from_smi(smi, [0.0])
    except Exception:
        return None
    
    if dp.mol is None:
        return None

    dset = data.MoleculeDataset([dp], FEATURIZER)
    loader = data.build_dataloader(dset, shuffle=False, batch_size=1, drop_last=False)

    with torch.no_grad():
        for batch in loader:
            bmg, V_d, X_d, *_ = batch
            pred = model(bmg, V_d, X_d)
            return float(pred.numpy().flatten()[0])