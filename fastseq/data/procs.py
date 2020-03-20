# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/04_data.procs.ipynb (unless otherwise specified).

__all__ = ['CatProc']

# Cell
from .external import *
from .load import *
from .core import *
from ..core import *
from fastcore.all import *
from fastcore.imports import *
from fastai2.basics import *
from fastai2.data.transforms import *
from fastai2.tabular.core import *
from .all import *
from typing import List
import orjson

# Cell
class CatProc():
    def __init__(self, path, num_of_workers = None, vocab = None, o2i = None):
        if vocab is None and o2i is None:
            vocab, o2i = make_vocab(path)
        self.meta = get_meta(path)
        self.f = CatMultiTfm(vocab = vocab, o2i = o2i)
        self.num_of_workers = num_of_workers

    def __call__(self, files:List[Path]):
        return multithread_f(self._setup, files, self.num_of_workers)
#         r = []
#         for f in files:
#             r.append(self._setup(f))
#         return r

    def _setup(self, f:Path):
        ts = get_ts_datapoint(f)
        tsm = json2TSMulti(ts, 0, self.meta['col_names']['ts_con_names'][0], ts['_length']-1, 1, self.meta)
        tsm = self.f(tsm)
        for i, cat in enumerate(ts['ts_cat']):
            test_eq(len(tsm[2][i]), len(ts['ts_cat'][cat]))
            ts['ts_cat'][cat] = [o.item() for o in tsm[2][i]]
        for i, cat in enumerate(ts['cat']):
            ts['cat'][cat] = tsm[3][i].item()
        open(f,'wb').write(orjson.dumps(dict(ts)))
        return f
