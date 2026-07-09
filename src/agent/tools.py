import requests
from urllib.parse import quote
from vina import Vina
from rdkit import Chem
from rdkit.Chem import rdDistGeom
from meeko import MoleculePreparation
from meeko import PDBQTWriterLegacy
from src.data_processing.parse_pdb import get_coords
from src.agent.filter_compounds import filter_compounds

COORDS = get_coords()


def prepare_ligand(smi):
    mol = Chem.MolFromSmiles(smi)
    if mol is None:
        return None

    frags = Chem.GetMolFrags(mol, asMols=True)
    if len(frags) > 1:
        mol = max(frags, key=lambda m: m.GetNumAtoms())

    mol_h = Chem.AddHs(mol)
    params = rdDistGeom.ETKDG()
    status = rdDistGeom.EmbedMolecule(mol_h, params)
    if status == -1:
        print("ERROR: Cannot convert SMILES string to 3D Molecule.")
        return None

    mk_prep = MoleculePreparation()
    molsetup_list = mk_prep(mol_h)

    if len(molsetup_list) == 0:
        return None
    if len(molsetup_list) > 1:
        print(f"WARNING: {smi} produced {len(molsetup_list)} setups, using first")

    pdbqt_string, is_ok, error_msg = PDBQTWriterLegacy.write_string(molsetup_list[0])
    if not is_ok:
        return None

    return pdbqt_string


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

    data = chembl_data[:MAX_COMPOUNDS]
    return filter_compounds(data)


def fetch_similar_compounds(ref_smi):
    ref_smi_url = quote(ref_smi, safe="")
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
            f"https://www.ebi.ac.uk/chembl/api/data/similarity/{ref_smi_url}/70",
            params=query_params,
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

    data = chembl_data[:MAX_COMPOUNDS]
    return filter_compounds(data)


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
