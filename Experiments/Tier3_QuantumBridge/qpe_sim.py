import numpy as np

def fractional_phase(r):
    # ideal measurement returns k/r; we draw one k uniformly
    k=np.random.randint(0,r)
    return k/r

def sample_qpe_distribution(r,shots):
    return np.array([fractional_phase(r) for _ in range(shots)])

def qpe_histogram(r,shots,bins):
    samp=sample_qpe_distribution(r,shots)
    hist,edges=np.histogram(samp,bins=bins,range=(0,1))
    return hist,edges
