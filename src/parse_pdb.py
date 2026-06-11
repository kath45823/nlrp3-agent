from pdbfixer import PDBFixer
from openmm.app import PDBFile

with open('data/9GU4.cif', 'r') as f:
    fixer = PDBFixer(pdbxfile=f)

fixer.findMissingResidues()
fixer.findNonstandardResidues()
fixer.replaceNonstandardResidues()
fixer.removeHeterogens(False)
fixer.findMissingAtoms()
fixer.addMissingAtoms()
fixer.addMissingHydrogens(7.4)

with open('data/9GU4-cleaned.pdb', 'w') as f:
    PDBFile.writeFile(fixer.topology, fixer.positions, f)