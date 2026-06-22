from pdbfixer import PDBFixer
from openmm.app import PDBFile
from rdkit import Chem


def parse_pdb_file():
    with open("data/9GU4.cif", "r") as f:
        fixer = PDBFixer(pdbxfile=f)

    fixer.findMissingResidues()
    fixer.findNonstandardResidues()
    fixer.replaceNonstandardResidues()
    fixer.removeHeterogens(False)
    fixer.findMissingAtoms()
    fixer.addMissingAtoms()
    fixer.addMissingHydrogens(7.4)

    with open("data/9GU4-cleaned.pdb", "w") as f:
        PDBFile.writeFile(fixer.topology, fixer.positions, f)


def get_coords():
    mols = Chem.SDMolSupplier("data/9gu4_B_A1IPJ.sdf", removeHs=False)
    mol = mols[0]
    cf = mol.GetConformer()
    pos = cf.GetPositions()
    centroid = pos.mean(axis=0)
    return (centroid[0], centroid[1], centroid[2])
