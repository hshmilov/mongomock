from collections.abc import Mapping


class AxoniusDict(Mapping):
    """
    Usage: d = AxoniusDict(mydict); d.get_or_default(key, default)
    """

    def __init__(self, *args, **kw):
        self._storage = dict(*args, **kw)

    def __getitem__(self, key):
        return self._storage[key]

    def __iter__(self):
        return iter(self._storage)

    def __len__(self):
        return len(self._storage)

    def get_or_default(self, key, default=None):
        return self._storage.get(key, default) or default
