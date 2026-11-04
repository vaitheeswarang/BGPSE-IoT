import numpy as np
from bgpse.stats import holm

def test_holm():
    x=holm(np.array([0.01,0.02,0.5])); assert (x>=0).all() and (x<=1).all()
