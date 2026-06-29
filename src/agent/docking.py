from src.agent.filter_compounds import filter_compounds
from rdkit import Chem 
from rdkit.Chem import rdDistGeom
from meeko import MoleculePreparation
from meeko import PDBQTWriterLegacy

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
    
    print(pdbqt_str_list)

prepare_ligand()
