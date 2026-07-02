from src.agent.filter_compounds import filter_compounds
from src.agent.tools import dock_compound
from rdkit import Chem
from rdkit.Chem import rdDistGeom
from meeko import MoleculePreparation
from meeko import PDBQTWriterLegacy


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
