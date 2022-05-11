# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/11_vision.models.xresnet.ipynb (unless otherwise specified).


from __future__ import annotations


__all__ = ['init_cnn', 'XResNet', 'xresnet18', 'xresnet34', 'xresnet50', 'xresnet101', 'xresnet152', 'xresnet18_deep',
           'xresnet34_deep', 'xresnet50_deep', 'xresnet18_deeper', 'xresnet34_deeper', 'xresnet50_deeper', 'se_kwargs1',
           'se_kwargs2', 'se_kwargs3', 'g0', 'g1', 'g2', 'g3', 'xse_resnet18', 'xse_resnext18', 'xresnext18',
           'xse_resnet34', 'xse_resnext34', 'xresnext34', 'xse_resnet50', 'xse_resnext50', 'xresnext50',
           'xse_resnet101', 'xse_resnext101', 'xresnext101', 'xse_resnet152', 'xsenet154', 'xse_resnext18_deep',
           'xse_resnext34_deep', 'xse_resnext50_deep', 'xse_resnext18_deeper', 'xse_resnext34_deeper',
           'xse_resnext50_deeper']

# Cell
#nbdev_comment from __future__ import annotations
from ...torch_basics import *
try: from torchvision.models.utils import load_state_dict_from_url
except ModuleNotFoundError: from torch.hub import load_state_dict_from_url

# Cell
def init_cnn(m):
    if getattr(m, 'bias', None) is not None: nn.init.constant_(m.bias, 0)
    if isinstance(m, (nn.Conv1d,nn.Conv2d,nn.Conv3d,nn.Linear)): nn.init.kaiming_normal_(m.weight)
    for l in m.children(): init_cnn(l)

# Cell
class XResNet(nn.Sequential):
    @delegates(ResBlock)
    def __init__(self, block, expansion, layers, p=0.0, c_in=3, n_out=1000, stem_szs=(32,32,64),
                 widen=1.0, sa=False, act_cls=defaults.activation, ndim=2, ks=3, stride=2, **kwargs):
        store_attr('block,expansion,act_cls,ndim,ks')
        if ks % 2 == 0: raise Exception('kernel size has to be odd!')
        stem_szs = [c_in, *stem_szs]
        stem = [ConvLayer(stem_szs[i], stem_szs[i+1], ks=ks, stride=stride if i==0 else 1,
                          act_cls=act_cls, ndim=ndim)
                for i in range(3)]

        block_szs = [int(o*widen) for o in [64,128,256,512] +[256]*(len(layers)-4)]
        block_szs = [64//expansion] + block_szs
        blocks    = self._make_blocks(layers, block_szs, sa, stride, **kwargs)

        super().__init__(
            *stem, MaxPool(ks=ks, stride=stride, padding=ks//2, ndim=ndim),
            *blocks,
            AdaptiveAvgPool(sz=1, ndim=ndim), Flatten(), nn.Dropout(p),
            nn.Linear(block_szs[-1]*expansion, n_out),
        )
        init_cnn(self)

    def _make_blocks(self, layers, block_szs, sa, stride, **kwargs):
        return [self._make_layer(ni=block_szs[i], nf=block_szs[i+1], blocks=l,
                                 stride=1 if i==0 else stride, sa=sa and i==len(layers)-4, **kwargs)
                for i,l in enumerate(layers)]

    def _make_layer(self, ni, nf, blocks, stride, sa, **kwargs):
        return nn.Sequential(
            *[self.block(self.expansion, ni if i==0 else nf, nf, stride=stride if i==0 else 1,
                      sa=sa and i==(blocks-1), act_cls=self.act_cls, ndim=self.ndim, ks=self.ks, **kwargs)
              for i in range(blocks)])

# Cell
def _xresnet(pretrained, expansion, layers, **kwargs):
    # TODO pretrain all sizes. Currently will fail with non-xrn50
    url = 'https://s3.amazonaws.com/fast-ai-modelzoo/xrn50_940.pth'
    res = XResNet(ResBlock, expansion, layers, **kwargs)
    if pretrained: res.load_state_dict(load_state_dict_from_url(url, map_location='cpu')['model'], strict=False)
    return res

def xresnet18 (pretrained=False, **kwargs): return _xresnet(pretrained, 1, [2, 2,  2, 2], **kwargs)
def xresnet34 (pretrained=False, **kwargs): return _xresnet(pretrained, 1, [3, 4,  6, 3], **kwargs)
def xresnet50 (pretrained=False, **kwargs): return _xresnet(pretrained, 4, [3, 4,  6, 3], **kwargs)
def xresnet101(pretrained=False, **kwargs): return _xresnet(pretrained, 4, [3, 4, 23, 3], **kwargs)
def xresnet152(pretrained=False, **kwargs): return _xresnet(pretrained, 4, [3, 8, 36, 3], **kwargs)
def xresnet18_deep  (pretrained=False, **kwargs): return _xresnet(pretrained, 1, [2,2,2,2,1,1], **kwargs)
def xresnet34_deep  (pretrained=False, **kwargs): return _xresnet(pretrained, 1, [3,4,6,3,1,1], **kwargs)
def xresnet50_deep  (pretrained=False, **kwargs): return _xresnet(pretrained, 4, [3,4,6,3,1,1], **kwargs)
def xresnet18_deeper(pretrained=False, **kwargs): return _xresnet(pretrained, 1, [2,2,1,1,1,1,1,1], **kwargs)
def xresnet34_deeper(pretrained=False, **kwargs): return _xresnet(pretrained, 1, [3,4,6,3,1,1,1,1], **kwargs)
def xresnet50_deeper(pretrained=False, **kwargs): return _xresnet(pretrained, 4, [3,4,6,3,1,1,1,1], **kwargs)

# Cell
se_kwargs1 = dict(groups=1 , reduction=16)
se_kwargs2 = dict(groups=32, reduction=16)
se_kwargs3 = dict(groups=32, reduction=0)
g0 = [2,2,2,2]
g1 = [3,4,6,3]
g2 = [3,4,23,3]
g3 = [3,8,36,3]

# Cell
def xse_resnet18(n_out=1000, pretrained=False, **kwargs):   return XResNet(SEBlock,  1, g0, n_out=n_out, **se_kwargs1, **kwargs)
def xse_resnext18(n_out=1000, pretrained=False, **kwargs):  return XResNet(SEResNeXtBlock, 1, g0, n_out=n_out, **se_kwargs2, **kwargs)
def xresnext18(n_out=1000, pretrained=False, **kwargs):     return XResNet(SEResNeXtBlock, 1, g0, n_out=n_out, **se_kwargs3, **kwargs)
def xse_resnet34(n_out=1000, pretrained=False, **kwargs):   return XResNet(SEBlock,  1, g1, n_out=n_out, **se_kwargs1, **kwargs)
def xse_resnext34(n_out=1000, pretrained=False, **kwargs):  return XResNet(SEResNeXtBlock, 1, g1, n_out=n_out, **se_kwargs2, **kwargs)
def xresnext34(n_out=1000, pretrained=False, **kwargs):     return XResNet(SEResNeXtBlock, 1, g1, n_out=n_out, **se_kwargs3, **kwargs)
def xse_resnet50(n_out=1000, pretrained=False, **kwargs):   return XResNet(SEBlock,  4, g1, n_out=n_out, **se_kwargs1, **kwargs)
def xse_resnext50(n_out=1000, pretrained=False, **kwargs):  return XResNet(SEResNeXtBlock, 4, g1, n_out=n_out, **se_kwargs2, **kwargs)
def xresnext50(n_out=1000, pretrained=False, **kwargs):     return XResNet(SEResNeXtBlock, 4, g1, n_out=n_out, **se_kwargs3, **kwargs)
def xse_resnet101(n_out=1000, pretrained=False, **kwargs):  return XResNet(SEBlock,  4, g2, n_out=n_out, **se_kwargs1, **kwargs)
def xse_resnext101(n_out=1000, pretrained=False, **kwargs): return XResNet(SEResNeXtBlock, 4, g2, n_out=n_out, **se_kwargs2, **kwargs)
def xresnext101(n_out=1000, pretrained=False, **kwargs):    return XResNet(SEResNeXtBlock, 4, g2, n_out=n_out, **se_kwargs3, **kwargs)
def xse_resnet152(n_out=1000, pretrained=False, **kwargs):  return XResNet(SEBlock,  4, g3, n_out=n_out, **se_kwargs1, **kwargs)
def xsenet154(n_out=1000, pretrained=False, **kwargs):
    return XResNet(SEBlock, g3, groups=64, reduction=16, p=0.2, n_out=n_out)
def xse_resnext18_deep  (n_out=1000, pretrained=False, **kwargs):  return XResNet(SEResNeXtBlock, 1, g0+[1,1], n_out=n_out, **se_kwargs2, **kwargs)
def xse_resnext34_deep  (n_out=1000, pretrained=False, **kwargs):  return XResNet(SEResNeXtBlock, 1, g1+[1,1], n_out=n_out, **se_kwargs2, **kwargs)
def xse_resnext50_deep  (n_out=1000, pretrained=False, **kwargs):  return XResNet(SEResNeXtBlock, 4, g1+[1,1], n_out=n_out, **se_kwargs2, **kwargs)
def xse_resnext18_deeper(n_out=1000, pretrained=False, **kwargs):  return XResNet(SEResNeXtBlock, 1, [2,2,1,1,1,1,1,1], n_out=n_out, **se_kwargs2, **kwargs)
def xse_resnext34_deeper(n_out=1000, pretrained=False, **kwargs):  return XResNet(SEResNeXtBlock, 1, [3,4,4,2,2,1,1,1], n_out=n_out, **se_kwargs2, **kwargs)
def xse_resnext50_deeper(n_out=1000, pretrained=False, **kwargs):  return XResNet(SEResNeXtBlock, 4, [3,4,4,2,2,1,1,1], n_out=n_out, **se_kwargs2, **kwargs)