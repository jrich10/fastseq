# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/02_data.load.ipynb (unless otherwise specified).

__all__ = ['TSDataLoader']

# Cell
from ..core import *
from .external import *
from fastcore.utils import *
from fastcore.imports import *
from fastai2.basics import *
from fastai2.data.transforms import *
from fastai2.tabular.core import *

# Cell
import numpy as np
import pandas as pd

# Cell
@delegates()
class TSDataLoader(TfmdDL):
    def __init__(self, dataset, horizon, lookback=72, step=1, min_seq_len=None, **kwargs):
        self.horizon, self.lookback, self.step = horizon, lookback, step
        self.min_seq_len = ifnone(min_seq_len, lookback)
        self.dataset = [o.float() for o in L(dataset).map(tensor)]
        n = self.make_ids()
        super().__init__(dataset=self.dataset, **kwargs)
        self.n = n
        self.skipped= []

    @delegates(TfmdDL.new)
    def new(self, dataset=None, cls=None, **kwargs):
        res = super().new(dataset, cls, horizon=self.horizon, lookback=self.lookback, step=self.step , **kwargs)
        res.make_ids()
        return res

    def make_ids(self):
        """Make ids if the sequence is shorter than `min_seq_len`, it will drop that sequence."""
        # Slice each time series into examples, assigning IDs to each
        last_id = 0
        n_dropped = 0
        n_needs_padding = 0
        self._ids = {}
        for i, ts in enumerate(self.dataset):
            if isinstance(ts,tuple):
                ts = ts[0] # no idea why they become tuples
            num_examples = (ts.shape[-1] - self.lookback - self.horizon + self.step) // self.step
            # Time series shorter than the forecast horizon need to be dropped.
            if ts.shape[-1] < self.min_seq_len:
                n_dropped += 1
                continue
            # For short time series zero pad the input
            if ts.shape[-1] < self.lookback + self.horizon:
                n_needs_padding += 1
                num_examples = 1
            for j in range(num_examples):
                self._ids[last_id + j] = (i, j * self.step)
            last_id += num_examples

        # Inform user about time series that were too short
        if n_dropped > 0:
            print("Dropped {}/{} time series due to length.".format(
                    n_dropped, len(self.dataset)))

        # Inform user about time series that were short
        if n_needs_padding > 0:
            print("Need to pad {}/{} time series due to length.".format(
                    n_needs_padding, len(self.dataset)))
        # Store the number of training examples
        return int(self._ids.__len__() )

    def shuffle_fn(self, idxs):
#         self.dataset.shuffle()
        return idxs

    def get_id(self, idx):
        # Get time series
        ts_id, lookback_id = self._ids[idx]
        ts = self.dataset[ts_id]
        if isinstance(ts,tuple):
            ts = ts[0] # no idea why they become tuples
        # Prepare input and target. Zero pad if necessary.
        if ts.shape[-1] < self.lookback + self.horizon:
            # If the time series is too short, we zero pad
            x = ts[:, :-self.horizon]
            mean = x.mean()
            x = np.pad(
                x,
                pad_width=((0, 0), (self.lookback - x.shape[-1], 0)),
                mode='constant',
                constant_values=mean
            )
            y = ts[:,-self.lookback + self.horizon:]
            y = np.pad(
                y,
                pad_width=((0, 0), (self.lookback + self.horizon - y.shape[-1], 0)),
                mode='constant',
                constant_values=mean
            )
            assert y.shape == (1,self.lookback+self.horizon), f"{y.shape}\t,{idx}, , 'tsshape':{ts.shape},'ts_id':{ts_id}"
        else:
            x = ts[:,lookback_id:lookback_id + self.lookback]
            y = ts[:,lookback_id:lookback_id + self.lookback + self.horizon]
        return x, y

    def create_item(self, idx):
        if idx>=self.n:
            raise IndexError
        x, y  = self.get_id(idx)
        # TODO remove
#         if (y/x.std()).std()>self.max_std:
#             if idx not in self.skipped:
# #                 print(f"idx: {idx};y.std to high: {(y/x.std()).std()} > {self.max_std}")
#                 self.skipped.append(idx)
#             raise SkipItemException()

        return TSTensorSeq(x),TSTensorSeqy(y)

# Cell

from fastai2.vision.data import get_grid

@typedispatch
def show_batch(x: TensorSeq, y, samples, ctxs=None, max_n=10,rows=None, cols=None, figsize=None, **kwargs):
    if ctxs is None: ctxs = get_grid(min(len(samples), max_n), rows=rows, cols=cols, add_vert=1, figsize=figsize)
    ctxs = show_batch[object](x, y, samples=samples, ctxs=ctxs, max_n=max_n, **kwargs)
    return ctxs

# Cell
@typedispatch
def show_results(x: TensorSeq, y, samples, outs, ctxs=None, max_n=9,rows=None, cols=None, figsize=None, **kwargs):
    if ctxs is None: ctxs = get_grid(min(len(samples), max_n), rows=rows, cols=cols, add_vert=1, figsize=figsize)
    for i in range(len(outs[0])):
        ctxs = [TSTensorSeqy(b ,m='*r', label='pred').show(ctx=c, **kwargs) for b,c,_ in zip(outs.itemgot(i),ctxs,range(max_n))]
    for i in range(len(samples[0])):
        ctxs = [b.show(ctx=c, **kwargs) for b, c, _ in zip(samples.itemgot(i),ctxs,range(max_n))]
    return ctxs