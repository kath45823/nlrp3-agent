from src.agent.filter_compounds import filter_compounds
from rdkit import Chem 
from rdkit.Chem import rdDistGeom
from meeko import MoleculePreparation
from meeko import PDBQTWriterLegacy
from vina import Vina
from src.data_processing.parse_pdb import get_coords

def prepare_ligand():
    compounds = filter_compounds()
    test_smi = compounds[0]
    test_mol = Chem.MolFromSmiles(test_smi)
    if test_mol is None: 
        return None

    test_mol_h = Chem.AddHs(test_mol)
    params = rdDistGeom.ETKDG()
    status = rdDistGeom.EmbedMolecule(test_mol_h, params)
    if status == -1:
        print("ERROR: Cannot convert SMILES string to 3D Molecule.")
        return None

    mk_prep = MoleculePreparation()
    molsetup_list = mk_prep(test_mol_h)
    pdbqt_str_list = []

    for molsetup in molsetup_list:
        pdbqt_string, is_ok, error_msg = PDBQTWriterLegacy.write_string(molsetup)
        if is_ok:
            pdbqt_str_list.append(pdbqt_string)
        else:
            print(f"PDBQT write failed: {error_msg}")
    
    return pdbqt_str_list

def get_docking_score():
    pdbqt_str_list = prepare_ligand()
    pdbqt_str = pdbqt_str_list[0]
    v = Vina(sf_name = 'vina')
    coords = get_coords()

    v.set_receptor('data/9GU4-receptor.pdbqt')
    v.set_ligand_from_string(pdbqt_str)
    v.compute_vina_maps(center=[coords[0], coords[1], coords[2]], box_size=[20, 20, 20])
    v.dock(exhaustiveness=8, n_poses=3)

    print(v.energies()[0][0])

get_docking_score()
