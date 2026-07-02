from chemprop import data, featurizers, models
import os

CKPT_PATH = os.path.join(os.path.dirname(__file__), "nlrp3-model", "nlrp3_chemprop.ckpt")
MODEL = None
FEATURIZER = featurizers.SimpleMoleculeMolGraphFeaturizer()

def load_model():
    global MODEL
    if MODEL is None:
        MODEL = models.MPNN.load_from_checkpoint(CKPT_PATH)
        MODEL.eval()
    return MODEL