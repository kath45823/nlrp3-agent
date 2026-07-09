from rdkit import Chem
from rdkit.Chem import rdMolAlign
from meeko import PDBQTMolecule, RDKitMolCreate
from vina import Vina
from src.data_processing.parse_pdb import get_coords
from src.agent.tools import prepare_ligand

RECEPTOR_PATH = "data/9GU4-receptor.pdbqt"
BOX_CENTER = list(get_coords())
BOX_SIZE = [20, 20, 20]
CRYSTAL_LIGAND_SDF = "data/9gu4_B_A1IPJ.sdf"
MCC950_SMILES = "CC(C)(C1=COC(=C1)S(=O)(=O)NC(=O)NC2=C3CCCC3=CC4=C2CCC4)O"


def dock_and_get_poses(pdbqt_string):
    v = Vina(sf_name="vina")
    v.set_receptor(RECEPTOR_PATH)
    v.set_ligand_from_string(pdbqt_string)
    v.compute_vina_maps(center=BOX_CENTER, box_size=BOX_SIZE)
    v.dock(exhaustiveness=16, n_poses=10)
    return v


def validate_np3253():
    np3253 = Chem.MolFromMolFile(CRYSTAL_LIGAND_SDF)
    np3253 = Chem.RemoveHs(np3253)
    np3253_smi = Chem.MolToSmiles(np3253)

    pdbqt_str = prepare_ligand(np3253_smi)
    v = dock_and_get_poses(pdbqt_str)

    score = v.energies()[0][0]
    print(f"Best docking score: {score:.2f} kcal/mol")

    # RMSD Validation
    docked_pdbqt = v.poses(n_poses=10)
    pmol = PDBQTMolecule(docked_pdbqt, is_dlg=False, skip_typing=True)
    docked_mols = RDKitMolCreate.from_pdbqt_mol(pmol)
    docked = docked_mols[0]
    docked = Chem.RemoveHs(docked)
 
    best_rmsd = None
    for conf_id in range(docked.GetNumConformers()):
        try:
            rmsd = rdMolAlign.CalcRMS(docked, np3253, prbId=conf_id)
        except Exception:
            rmsd = rdMolAlign.GetBestRMS(docked, np3253)
        if best_rmsd is None or rmsd < best_rmsd:
            best_rmsd = rmsd
 
    print(f"Best pose RMSD: {best_rmsd:.2f} A")


def validate_mcc950():
    pdbqt_str = prepare_ligand(MCC950_SMILES)
    v = dock_and_get_poses(pdbqt_str)

    score = v.energies()[0][0]
    print(f"Best docking score: {score:.2f} kcal/mol")


if __name__ == "__main__":
    validate_np3253()
    validate_mcc950()
