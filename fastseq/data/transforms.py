# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/04_data.transforms.ipynb (unless otherwise specified).

__all__ = ['encodes', 'decodes', 'SampleNorm']

# Cell
from fastai2.torch_basics import *
from fastai2.data.all import *
# from pyts.image import GramianAngularField, MarkovTransitionField, RecurrencePlot

# Cell
@ToTensor
def encodes(self,o):
    return tensor(o).float()
@ToTensor
def decodes(self,o)->np.ndarray:
    return np.array(o)

# Cell
from ..all import *

class SampleNorm(Transform):
    as_item = True
    def encodes(self, o:TSeries):
        return (o - o.mean(-1,keepdim = True))/(o.std(-1,keepdim=True) + 1e-8)