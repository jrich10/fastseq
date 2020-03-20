# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/11_model.conv.ipynb (unless otherwise specified).

__all__ = ['SeqTabConv', 'emb_sz_rule', 'get_emb_sz', 'dct']

# Cell
from ..core import *
from ..data.external import *
from ..data.load import *
from ..data.core import *
from ..data.procs import *
from fastcore.all import *
from fastcore.imports import *
from fastai2.basics import *
from fastai2.data.transforms import *
from fastai2.tabular.core import *
from fastai2.tabular.model import *
from fastai2.torch_basics import *
from fastai2.callback.all import *
from ..metrics import *

# Cell
class SeqTabConv(Module):
    """Basic model for sequential data."""
    def __init__(self, horizon, lookback, emb_szs = None, emb_szs_ts = None, ts_con_chn = None, con_chn = None,
                 layers = [32, 32], y_range=[-5,10]):
        self.horizon, self.lookback = horizon, lookback
        if emb_szs is not None:
            self.embeds = nn.ModuleList([Embedding(ni, nf) for ni,nf in emb_szs])
            self.n_emb = sum(e.embedding_dim for e in self.embeds)
        else:
            self.n_emb=0

        if emb_szs is None:
            self.embeds_ts = nn.ModuleList([Embedding(ni, nf) for ni,nf in emb_szs_ts])
            self.n_emb_ts = sum(e.embedding_dim for e in self.embeds_ts)
        else:
            self.n_emb_ts=0
        self.conv = ConvLayer(13, 1, ks = 1, ndim=1)
        self.scale = SigmoidRange(*y_range)

    def forward(self, x, ts_con, ts_cat, cat, con):
        if self.n_emb != 0:
            x = [e(cat[:,i]) for i,e in enumerate(self.embeds)]
            cat = torch.cat(x, 1)
            print('emb',cat.shape)

        cat = cat[:,:,None] * torch.ones(ts_con.shape[0],6,ts_con.shape[-1]).to(default_device())
        print(cat.shape)
        con = con[:,:,None] * torch.ones(ts_con.shape[0],0,ts_con.shape[-1]).to(default_device())
        ts = torch.cat([ts_con, ts_cat.float(), cat.float(), con], 1)
        r = self.conv(ts)
        return r

# Cell
def emb_sz_rule(n_cat):
    "Rule of thumb to pick embedding size corresponding to `n_cat`"
    return min(600, round(1.6 * n_cat**0.56))

def _one_emb_sz(classes, n, sz_dict=None):
    "Pick an embedding size for `n` depending on `classes` if not given in `sz_dict`."
    sz_dict = ifnone(sz_dict, {})
    n_cat = len(classes[n])
    sz = sz_dict.get(n, int(emb_sz_rule(n_cat)))  # rule of thumb
    return n_cat,sz

def get_emb_sz(to, sz_dict=None):
    return [_one_emb_sz(to.meta['classes'], key, sz_dict) for key in to.meta['classes'].keys()]

# Cell
dct = make_submision_file(learn)
dct['HOBBIES_1_028_CA_1_validation']