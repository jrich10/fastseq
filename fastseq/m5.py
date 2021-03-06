# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/00_m5.ipynb (unless otherwise specified).

__all__ = ['add_days', 'interpolate_w_starting_nan', 'get_prices', 'csv_gen', 'to_contained_series']

# Cell
from fastcore.all import *
from fastcore.imports import *
from fastai2.basics import *
from fastai2.data.transforms import *
from fastai2.tabular.core import *
from .data.all import *
from .core import *
from .data.all import *

# Cell
def add_days(df_sales, days = 28*2, fill = -1):
    for i in range(days):
        df_sales['d_'+str(i+1914)] = fill
    return df_sales

# Cell
@delegates(pd.Series.interpolate)
def interpolate_w_starting_nan(s, **kwargs):
    if s.iloc[0] != s.iloc[0]:
        for i,o in enumerate(s != s):
            if not o:
                s.iloc[0] = s.iloc[i]
                break
    return s.interpolate(**kwargs)

# Cell
def get_prices(df_price, store_id, item_id, method = 'linear'):
    _df = df_price[df_price['store_id'] == store_id]
    _df = _df[_df['item_id'] == item_id]
    _df['wm_yr_wk'] = _df['wm_yr_wk'].astype(int)
    _df.index = _df['wm_yr_wk']
    p = dict(_df['sell_price'])
    wm_yr_wk = pd.Series({i:p[i] if i in p else np.nan for i in range(11100,11622)})
    wm_yr_wk = interpolate_w_starting_nan(wm_yr_wk, method = method)
    return wm_yr_wk

# Cell
def _get_price_s(row, df_price):
    p = get_prices(df_price, row['store_id'], row['item_id'])
    dct = {'store_id':row['store_id'],'item_id':row['item_id']}
#     for i in range(1,1970):
    dct.update({'d_'+str(i): p[d2wk['d_'+str(i)]] for i in range(1,1970)})
    return dct

# Cell
import csv
def csv_gen(file):
    with open(file, 'r') as f:
        reader = csv.reader(f)
        header = next(reader)
        for row in reader:
            yield {k:v for k,v in zip(header,row)}

# Cell
def _slice_series(dct, s_slice=None, add_zeros = 28*2):
    s_slice = ifnone(s_slice, slice(6,None))
    return [float(o) for k,o in dct.items() if ('d_' in k or 'F' in k)]+[0]*add_zeros
# @delegates(_to_series)
def to_contained_series(dct, series_column_name = 'sales', **kwargs):
    data={k:v for k,v in dct.items() if ('d_' not in k and 'F' not in k)}
    data[series_column_name] = _slice_series(dct, **kwargs)
    return data