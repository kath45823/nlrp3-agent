import torch
import numpy as np
from chemprop import data, featurizers, models

MODEL = None
FEATURIZER = featurizers.SimpleMoleculeMolGraphFeaturizer()
CKPT_PATH = "src/model/nlrp3-model/nlrp3_chemprop.ckpt"


def load_model():
    global MODEL
    if MODEL is None:
        MODEL = models.MPNN.load_from_checkpoint(CKPT_PATH)
        MODEL.eval()
    return MODEL


def predict_pic50(smiles):
    model = load_model()

    try:
        dp = data.MoleculeDatapoint.from_smi(smiles, [0.0])
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