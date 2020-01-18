# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/10_models.nbeats.ipynb (unless otherwise specified).

__all__ = ['linspace', 'Block', 'bias_model', 'BiasBlock', 'LinearD', 'GenericBlock', 'seasonality_model',
           'SeasonalityBlock', 'trend_model', 'TrendBlock', 'select_block', 'NBeatsNet', 'NBeatsTheta',
           'NBeatsBackwards', 'NBeatsTrainer', 'CombinedLoss', 'nbeats_learner']

# Cell
from fastcore.utils import *
from fastcore.imports import *
from fastai2.basics import *
from fastai2.callback.hook import num_features_model
from fastai2.callback.all import *
from fastai2.torch_core import *
from torch.autograd import Variable
from ..all import *

# Cell

def linspace(lookback, horizon):
    lin_space = torch.linspace(
        -lookback, horizon, lookback + horizon
    )
    b_ls = lin_space[:lookback]
    f_ls = lin_space[lookback:]
    return b_ls, f_ls


# Cell
class Block(Module):
    def __init__(self, fnc_f, fnc_b=None):
        sizes = [self.lookback] + self.layers
        ps = ifnone(self.ps, L([0])*len(self.layers))
        actns = [nn.ReLU(inplace=True) for _ in range(len(sizes)-2)] + [None]
        _layers = [LinBnDrop(sizes[i], sizes[i+1], bn=self.use_bn, p=p, act=a)
                       for i,(p,a) in enumerate(zip(ps, actns))]
        self.layers = nn.Sequential(*_layers)
        self.att = LinBnDrop(sizes[-1], 1)
        if self.share_thetas:
            self.theta_f_fc = self.theta_b_fc = LinBnDrop(sizes[-1], self.thetas_dim)
        else:
            self.theta_b_fc = LinBnDrop(sizes[-1], self.thetas_dim)
            self.theta_f_fc = LinBnDrop(sizes[-1], self.thetas_dim)

        b, f = linspace(self.lookback, self.horizon)
        self.backcast_linspace = Variable(b, requires_grad=False).to(self.device)
        self.forecast_linspace = Variable(f, requires_grad=False).to(self.device)
        self.fnc_f = fnc_f
        self.fnc_b = ifnone(fnc_b, fnc_f)
        self.to(self.device)
        self.y_range = getattr(self,'y_range', None)

    def forward(self, x):
        # trend
        x = self.layers(x)
        att = torch.sigmoid(self.att(x))
        theta_b = self.apply_range(self.theta_b_fc(x)) * att
        theta_f = self.apply_range(self.theta_f_fc(x)) * att
        backcast = self.fnc_b(theta_b, self.backcast_linspace)
        forecast = self.fnc_f(theta_f, self.forecast_linspace)
        return {'b':backcast,'f': forecast, 'theta': theta_b + theta_f}

    def apply_range(self, x):
        if self.y_range is None:
            return x
        return (self.y_range[1]-self.y_range[0]) * torch.sigmoid(x) + self.y_range[0]

# Cell
def bias_model(thetas, t):
    r= torch.mm(t[None,:].float().T,thetas[:,0][None,:]).T
    if thetas.shape[-1]==2:
        return r+thetas[:,1][:,None]
    return r

class BiasBlock(Block):
    def __init__(
        self, layers:L, device, thetas_dim=2, lookback=10, horizon=5, use_bn=True, bn_final=False, ps:L=None
    ):
        share_thetas=True
        assert thetas_dim <= 2, f"thetas_dim for BaisBlock must be < than 2, is now {thetas_dim}"
        store_attr(self,"device,layers,thetas_dim,use_bn,ps,lookback,horizon,bn_final,share_thetas" )
        self.layers=L(self.layers[-1])
        super().__init__(bias_model)
        self.to(device)

# Cell
class LinearD(nn.Linear):
    def forward(self, x, *args, **kwargs):
        return super().forward(x)

class GenericBlock(Block):
    def __init__(
        self, layers:L, thetas_dim:int, device, lookback=10, horizon=5, use_bn=True, bn_final=False, ps:L=None, share_thetas=True, y_range=[-.5,.5]
    ):
        store_attr(self,"y_range,device,layers,thetas_dim,use_bn,ps,lookback,horizon,bn_final,share_thetas" )
        super().__init__(LinearD(self.thetas_dim, self.horizon),LinearD(self.thetas_dim, self.lookback))
        self.to(device)


# Cell

def seasonality_model(thetas, t):
    p = thetas.size()[-1]
    assert p < 10, "thetas_dim is too big."
    p1, p2 = (p // 2, p // 2) if p % 2 == 0 else (p // 2, p // 2 + 1)
    s1 = [torch.cos(2 * np.pi * i * t)[None,:] for i in range(p1)] # H/2-1
    s2 = [torch.sin(2 * np.pi * i * t)[None,:] for i in range(p2)]
    S = torch.cat([*s1, *s2])
    return thetas.mm(S)

class SeasonalityBlock(Block):
    def __init__(
        self, layers:L, thetas_dim:int, device, lookback=10, horizon=5, use_bn=True, bn_final=False, ps:L=None, share_thetas=False,y_range=[-.5,.5]
    ):
        store_attr(self,"y_range,device,layers,thetas_dim,use_bn,ps,lookback,horizon,bn_final,share_thetas" )
        super().__init__(seasonality_model )
        self.to(device)

# Cell
def trend_model(thetas, t):
    p = thetas.size()[-1]
    assert p <= 4, "thetas_dim is too big."
    a = [torch.pow(t, i)[None,:] for i in range(p)]
    T = torch.cat(a).float()
    return thetas.mm(T)

class TrendBlock(Block):
    def __init__(
        self, layers:L, device, thetas_dim, lookback=10, horizon=5, use_bn=True, bn_final=False, ps:L=None, share_thetas=False, y_range=[-.05,.05]
    ):
        store_attr(self,"y_range,device,layers,thetas_dim,use_bn,ps,lookback,horizon,bn_final,share_thetas" )
        super().__init__(trend_model)
        self.to(device)

# Cell

# blocks= defaultdict(GenericBlock)
# blocks.update({"seasonality": SeasonalityBlock,
#          "trend": TrendBlock,
#          "generic": GenericBlock})
# blocks_int= {i:v for i,v in enumerate(blocks.items())}
# not pritty but still works better
def select_block(o):
    if isinstance(o,int):
        if o == 0:
            return SeasonalityBlock
        elif o == 1:
            return TrendBlock
        elif o == 2:
            return BaisBlock
        else:
            return GenericBlock
    else:
        if o == 'seasonality':
            return SeasonalityBlock
        elif o == 'trend':
            return TrendBlock
        elif o =='bias':
            return BiasBlock
        else:
            return GenericBlock

# Cell
class NBeatsNet(Module):
    def __init__(
        self,
        device,
        stack_types=('bias', 'trend', 'seaonality'),
        nb_blocks_per_stack=3,
        horizon=5,
        lookback=10,
        thetas_dim=None,
        share_weights_in_stack=False,
        layers= [200,100],
    ):
        super(NBeatsNet, self).__init__()
        thetas_dim = ifnone(thetas_dim,[3 if 'bias' not in o else 2 for o in stack_types  ])
        stack_types= L(stack_types)
        store_attr(self,'device,horizon,lookback,layers,nb_blocks_per_stack,share_weights_in_stack,stack_types,thetas_dim,device')
        self.stacks = []
        self._str = "| N-Beats\n"

        self.bn = BatchNorm(lookback, ndim=2)
        stacks = OrderedDict()
        for stack_id in range(len(self.stack_types)):

            stacks[str(self.stack_types[stack_id]) + str(stack_id)] = self.create_stack(stack_id)
        self.stacks = nn.Sequential(stacks)

    def create_stack(self, stack_id):
        stack_type = self.stack_types[stack_id]
        self._str += f"| --  Stack {stack_type.title()} (#{stack_id}) (share_weights_in_stack={self.share_weights_in_stack})\n"

        blocks = []
        for block_id in range(self.nb_blocks_per_stack):
            block_init = select_block(stack_type)
            if self.share_weights_in_stack and block_id != 0:
                block = blocks[-1]  # pick up the last one when we share weights.
            else:
                block = block_init(
                    layers = self.layers,
                    thetas_dim = self.thetas_dim[stack_id],
                    device = self.device,
                    lookback = self.lookback,
                    horizon = self.horizon,
                )
            self._str += f"     | -- {block}\n"
            blocks.append(block)

        return nn.Sequential(*blocks)

    def forward(self, backcast):
        backcast = backcast.view([-1,backcast.shape[-1]])
        forecast = torch.zeros(
            size=(backcast.size()[0], self.horizon,)
        )  # maybe batch size here.

        dct = defaultdict(dict)
        for stack_id, names in enumerate(self.stacks.named_children()):
            name = names[0]
            for block_id in range(len(self.stacks[stack_id])):
                dct[name+'_'+str(block_id)] = self.stacks[stack_id][block_id](backcast)
                backcast = backcast.to(self.device) - dct[name+'_'+str(block_id)]['b']
                forecast = forecast.to(self.device) + dct[name+'_'+str(block_id)]['f']
        return forecast[:,None,:], backcast[:,None,:], dct



# Cell
from fastai2.data.all import *
from fastai2.optimizer import *
from fastai2.learner import *

# Cell
class NBeatsTheta(Metric):
    "The sqaure of the `theta` for every block. "
    def reset(self):           self.total,self.count = 0.,0
    def accumulate(self, learn):
        bs = find_bs(learn.yb)
        self.total += to_detach(learn.n_beats_trainer.metrics['theta'].mean())*bs
        self.count += bs
    @property
    def value(self): return self.total/self.count if self.count != 0 else None
    @property
    def name(self):  return "theta"

# Cell
class NBeatsBackwards(Metric):
    "The loss according to the `loss_func` on the backwards part of the time-serie."
    def reset(self):           self.total,self.count = 0.,0
    def accumulate(self, learn):
        bs = find_bs(learn.yb)
        self.total += to_detach(learn.n_beats_trainer.metrics['b_loss'].mean())*bs
        self.count += bs
    @property
    def value(self): return self.total/self.count if self.count != 0 else None
    @property
    def name(self):  return "b_loss"

# Cell
class NBeatsTrainer(Callback):
    "`Callback` that adds weights regularization the thetas in N-Beats training."
    def __init__(self, theta=0., b_loss=0.):
        self.theta, self.b_loss = theta, b_loss
        self.metrics = {'theta':tensor([0.]), 'b_loss':tensor([0.])}
        self.b = None

    def begin_train(self):
        self.out = defaultdict(dict)
        self.metrics = {'theta':tensor([0.]), 'b_loss':tensor([0.])}

    def begin_validate(self):
        self.out = defaultdict(dict)
        self.metrics = {'theta':tensor([0.]), 'b_loss':tensor([0.])}

    def after_pred(self):
        self.b = self.pred[1]
        self.pred[2]['total_b'] = self.pred[1]
        self.out = concat_dct(self.pred[2], self.out)
        self.learn.pred = self.pred[0]

    def after_loss(self):
        # theta
        value=tensor([0.])
        for key in self.out.keys():
            if 'bias' not in key and 'total' not in key:
                v = self.out[key]['theta'].float().pow(2).mean()
                if self.theta != 0.:
                    self.learn.loss += self.theta * v.item()
                value = value + v
        self.metrics['theta'] += value.clone().cpu().detach()

        # backwards
        value = self.learn.loss_func(self.b.float(), *self.xb, reduction='mean') #* (1/self.learn.lh)
        if self.b_loss != 0.:
            self.learn.loss += self.b_loss * value.mean()
        self.metrics['b_loss'] += value.sum().clone().detach()

    def theta_means(self):
        print({key:self.out[key]['theta'].float().mean(0) for key in self.out.keys() if 'total' not in key})

# Cell
def CombinedLoss(*losses, ratio:dict=None):
    _ratio = defaultdict(lambda:1.)
    if ratio is not None:
        _ratio.update(ratio)
    ratio = _ratio

    def _inner(pred, truth, *args,**kwargs):
        loss = None
        for _loss in losses:
            if loss is None:
                loss = ratio[_loss.__name__] * _loss(pred, truth, *args,**kwargs)
            else:
                loss += ratio[_loss.__name__] * _loss(pred, truth, *args,**kwargs)
        return loss

    return _inner
#     metrics = L()
#     for _loss in losses:
#         metrics.append(lambda pred, truth, *args,**kwargs: ratio[_loss.__name__] * _loss(pred, truth, *args,**kwargs))
#     print(metrics)


# Cell
from fastai2.basics import *
from ..all import *

@delegates(NBeatsNet.__init__)
def nbeats_learner(dbunch:TSDataBunch, output_channels=None, metrics=None,cbs=None, theta=0., b_loss=0., loss_func=None, **kwargs):
    "Build a N-Beats style learner"
    model = NBeatsNet(
        device = dbunch.train_dl.device,
        horizon = dbunch.train_dl.horizon,
        lookback = dbunch.train_dl.lookback,
        **kwargs
       )

    loss_func = ifnone(loss_func, CombinedLoss(F.mse_loss, smape, ratio = {'smape':.0005}))
    learn = Learner(dbunch, model, loss_func=loss_func, opt_func= Adam,
                    metrics=L(metrics)+L(mae, smape, F.mse_loss, NBeatsTheta(), NBeatsBackwards()),
                    cbs=L(NBeatsTrainer(theta, b_loss))+L(cbs)
                   )
    learn.lh = (learn.dbunch.train_dl.lookback/learn.dbunch.train_dl.horizon)
    return learn