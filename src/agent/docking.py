from src.agent.filter_compounds import filter_compounds
from src.data_processing.parse_pdb import get_coords
from rdkit import Chem 
from rdkit.Chem import rdDistGeom
from meeko import MoleculePreparation
from meeko import PDBQTWriterLegacy
from vina import Vina

def prepare_ligand(smi):
    mol = Chem.MolFromSmiles(smi)
    if mol is None: 
        return None

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

def dock_compound(pdbqt_str, coords):
    v = Vina(sf_name = 'vina')

    v.set_receptor('data/9GU4-receptor.pdbqt')
    v.set_ligand_from_string(pdbqt_str)
    v.compute_vina_maps(center=[coords[0], coords[1], coords[2]], box_size=[20, 20, 20])
    v.dock(exhaustiveness=8, n_poses=3)

    return v.energies()[0][0]

def get_docking_scores():
    compounds= filter_compounds()
    results = []
    coords = get_coords()

    for smi in compounds: 
        pdbqt = prepare_ligand(smi)
        if pdbqt is None:
            continue
        try:
            score = dock_compound(pdbqt, coords)
            results.append((smi, score))
        except Exception as e:
            print(f"Docking failed for {smi}: {e}")
            continue
    
    return results 
