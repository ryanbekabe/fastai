# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/02_data.load.ipynb (unless otherwise specified).


from __future__ import annotations


__all__ = ['fa_collate', 'fa_convert', 'SkipItemException', 'collate_error', 'DataLoader']

# Cell
#nbdev_comment from __future__ import annotations
from ..torch_basics import *
from torch.utils.data.dataloader import _MultiProcessingDataLoaderIter,_SingleProcessDataLoaderIter,_DatasetKind
_loaders = (_MultiProcessingDataLoaderIter,_SingleProcessDataLoaderIter)

# Cell
def _wif(worker_id):
    set_num_threads(1)
    info = get_worker_info()
    ds = info.dataset.d
    ds.num_workers,ds.offs = info.num_workers,info.id
    set_seed(info.seed)
    ds.wif()

class _FakeLoader:
    def _fn_noops(self, x=None, *args, **kwargs): return x

    _IterableDataset_len_called,_auto_collation,collate_fn,drop_last = None,False,_fn_noops,False
    _index_sampler,generator,prefetch_factor  = Inf.count,None,2
    dataset_kind = _dataset_kind = _DatasetKind.Iterable

    def __init__(self, d, pin_memory, num_workers, timeout, persistent_workers):
        self.dataset,self.default,self.worker_init_fn = self,d,_wif
        store_attr('d,pin_memory,num_workers,timeout,persistent_workers')

    def __iter__(self): return iter(self.d.create_batches(self.d.sample()))

    @property
    def multiprocessing_context(self): return (None,multiprocessing)[self.num_workers>0]

    @contextmanager
    def no_multiproc(self):
        old_num_workers = self.num_workers
        try:
            self.num_workers = 0
            yield self.d
        finally: self.num_workers = old_num_workers

_collate_types = (ndarray, Tensor, typing.Mapping, str)

# Cell
def fa_collate(t):
    "A replacement for PyTorch `default_collate` which maintains types and handles `Sequence`s"
    b = t[0]
    return (default_collate(t) if isinstance(b, _collate_types)
            else type(t[0])([fa_collate(s) for s in zip(*t)]) if isinstance(b, Sequence)
            else default_collate(t))

# Cell
def fa_convert(t):
    "A replacement for PyTorch `default_convert` which maintains types and handles `Sequence`s"
    return (default_convert(t) if isinstance(t, _collate_types)
            else type(t)([fa_convert(s) for s in t]) if isinstance(t, Sequence)
            else default_convert(t))

# Cell
class SkipItemException(Exception):
    "Raised to notify `DataLoader` to skip an item"
    pass

# Cell
def collate_error(e:Exception, batch):
    "Raises error when the batch could not collate, stating what items in the batch are different sizes and their types"
    err = f'Error when trying to collate the data into batches with fa_collate, at least two tensors in the batch are not the same size.\n\n'
    # we need to iterate through the entire batch and find a mismatch
    length = len(batch[0])
    for idx in range(length): # for each type in the batch
        for i, item in enumerate(batch):
            if i == 0: shape_a, type_a  = item[idx].shape, item[idx].__class__.__name__
            elif item[idx].shape != shape_a:
                shape_b = item[idx].shape
                if shape_a != shape_b:
                    err += f'Mismatch found on axis {idx} of the batch and is of type `{type_a}`:\n\tItem at index 0 has shape: {shape_a}\n\tItem at index {i} has shape: {shape_b}\n\nPlease include a transform in `after_item` that ensures all data of type {type_a} is the same size'
                    e.args = [err]
                    raise

# Cell
@funcs_kwargs
class DataLoader(GetAttr):
    _noop_methods = 'wif before_iter after_item before_batch after_batch after_iter'.split()
    for o in _noop_methods: exec(f"def {o}(self, x=None, *args, **kwargs): return x")
    _methods = _noop_methods + 'create_batches create_item create_batch retain \
        get_idxs sample shuffle_fn do_batch create_batch'.split()
    _default = 'dataset'
    def __init__(self, dataset=None, bs=None, num_workers=0, pin_memory=False, timeout=0, batch_size=None,
                 shuffle=False, drop_last=False, indexed=None, n=None, device=None, persistent_workers=False, **kwargs):
        if batch_size is not None: bs = batch_size # PyTorch compatibility
        assert not (bs is None and drop_last)
        if indexed is None: indexed = (hasattr(dataset,'__getitem__')
                                       and not isinstance(dataset, IterableDataset))
        if not indexed and shuffle: raise ValueError("Can only shuffle an indexed dataset (not an iterable one).")
        if n is None:
            try: n = len(dataset)
            except TypeError: pass
        store_attr('dataset,bs,shuffle,drop_last,indexed,n,pin_memory,timeout,device')
        self.rng,self.num_workers,self.offs = random.Random(random.randint(0,2**32-1)),1,0
        if sys.platform == "win32" and IN_NOTEBOOK and num_workers > 0:
            print("Due to IPython and Windows limitation, python multiprocessing isn't available now.")
            print("So `number_workers` is changed to 0 to avoid getting stuck")
            num_workers = 0
        self.fake_l = _FakeLoader(self, pin_memory, num_workers, timeout, persistent_workers=persistent_workers)

    def __len__(self):
        if self.n is None: raise TypeError
        if self.bs is None: return self.n
        return self.n//self.bs + (0 if self.drop_last or self.n%self.bs==0 else 1)

    def get_idxs(self):
        idxs = Inf.count if self.indexed else Inf.nones
        if self.n is not None: idxs = list(itertools.islice(idxs, self.n))
        if self.shuffle: idxs = self.shuffle_fn(idxs)
        return idxs

    def sample(self):
        return (b for i,b in enumerate(self.__idxs) if i//(self.bs or 1)%self.num_workers==self.offs)

    def __iter__(self):
        self.randomize()
        self.before_iter()
        self.__idxs=self.get_idxs() # called in context of main process (not workers/subprocesses)
        for b in _loaders[self.fake_l.num_workers==0](self.fake_l):
            # pin_memory causes tuples to be converted to lists, so convert them back to tuples
            if self.pin_memory and type(b) == list: b = tuple(b)
            if self.device is not None: b = to_device(b, self.device)
            yield self.after_batch(b)
        self.after_iter()
        if hasattr(self, 'it'): del(self.it)

    def create_batches(self, samps):
        if self.dataset is not None: self.it = iter(self.dataset)
        res = filter(lambda o:o is not None, map(self.do_item, samps))
        yield from map(self.do_batch, self.chunkify(res))

    def new(self, dataset=None, cls=None, **kwargs):
        if dataset is None: dataset = self.dataset
        if cls is None: cls = type(self)
        cur_kwargs = dict(dataset=dataset, num_workers=self.fake_l.num_workers, pin_memory=self.pin_memory, timeout=self.timeout,
                          bs=self.bs, shuffle=self.shuffle, drop_last=self.drop_last, indexed=self.indexed, device=self.device)
        for n in self._methods:
            o = getattr(self, n)
            if not isinstance(o, MethodType): cur_kwargs[n] = o
        return cls(**merge(cur_kwargs, kwargs))

    @property
    def prebatched(self): return self.bs is None
    def do_item(self, s):
        try: return self.after_item(self.create_item(s))
        except SkipItemException: return None
    def chunkify(self, b): return b if self.prebatched else chunked(b, self.bs, self.drop_last)
    def shuffle_fn(self, idxs): return self.rng.sample(idxs, len(idxs))
    def randomize(self): self.rng = random.Random(self.rng.randint(0,2**32-1))
    def retain(self, res, b):  return retain_types(res, b[0] if is_listy(b) else b)
    def create_item(self, s):
        if self.indexed: return self.dataset[s or 0]
        elif s is None:  return next(self.it)
        else: raise IndexError("Cannot index an iterable dataset numerically - must use `None`.")
    def create_batch(self, b):
        try: return (fa_collate,fa_convert)[self.prebatched](b)
        except Exception as e:
            if not self.prebatched: collate_error(e,b)
            raise
    def do_batch(self, b): return self.retain(self.create_batch(self.before_batch(b)), b)
    def to(self, device): self.device = device
    def one_batch(self):
        if self.n is not None and len(self)==0: raise ValueError(f'This DataLoader does not contain any batches')
        with self.fake_l.no_multiproc(): res = first(self)
        if hasattr(self, 'it'): delattr(self, 'it')
        return res

# Cell
add_docs(DataLoader, "API compatible with PyTorch DataLoader, with a lot more callbacks and flexibility",
         get_idxs       = "Return a list of indices to reference the dataset. Calls `shuffle_fn` internally if `shuffle=True`.",
         sample         = "Same as `get_idxs` but returns a generator of indices to reference the dataset.",
         create_batches = "Takes output of `sample` as input, and returns batches of data. Does not apply `after_batch`.",
         new            = "Create a new `DataLoader` with given arguments keeping remaining arguments same as original `DataLoader`.",
         prebatched     = "Check if `bs` is None.",
         do_item        = "Combines `after_item` and `create_item` to get an item from dataset by providing index as input.",
         chunkify       = "Used by `create_batches` to turn generator of items (`b`) into batches.",
         shuffle_fn     = "Returns a random permutation of `idxs`.",
         randomize      = "Set's `DataLoader` random number generator state.",
         retain         = "Cast each item of `res` to type of matching item in `b` if its a superclass.",
         create_item    = "Subset of the dataset containing the index values of sample if exists, else next iterator.",
         create_batch   = "Collate a list of items into a batch.",
         do_batch       = "Combines `create_batch` and `before_batch` to get a batch of items. Input is a list of items to collate.",
         to             = "Sets `self.device=device`.",
         one_batch      = "Return one batch from `DataLoader`.",
         wif            = "See pytorch `worker_init_fn` for details.",
         before_iter    = "Called before `DataLoader` starts to read/iterate over the dataset.",
         after_item     = "Takes output of `create_item` as input and applies this function on it.",
         before_batch   = "It is called before collating a list of items into a batch. Input is a list of items.",
         after_batch    = "After collating mini-batch of items, the mini-batch is passed through this function.",
         after_iter     = "Called after `DataLoader` has fully read/iterated over the dataset.")