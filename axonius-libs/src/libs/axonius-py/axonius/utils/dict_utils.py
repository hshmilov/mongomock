import copy
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
        if isinstance(default, dict):
            default = AxoniusDict(default)
        return self._storage.get(key, default) or default


def is_filter_in_value(value, filters):
    """
    Check recursively if any string value inside given item, has the current field's filter
    """
    if isinstance(value, str):
        return all((f['term'].lower() in value.lower()) == f['include'] if isinstance(f, dict) and 'term' in f else
                   f.lower() in value.lower()
                   for f in filters)
    if isinstance(value, list):
        return any(is_filter_in_value(item, filters) for item in value)
    if isinstance(value, dict):
        return any(is_filter_in_value(item, filters) for key, item in value.items())
    return False


def make_hash(obj):
    """
    Makes a hash from a dictionary, list, tuple or set to any level, that contains
    only other hashable types (including any lists, tuples, sets, and
    dictionaries).
    """

    if isinstance(obj, (set, tuple, list)):
        return tuple([make_hash(e) for e in obj])
    if not isinstance(obj, dict):
        return hash(obj)

    new_o = copy.deepcopy(obj)
    for k, v in new_o.items():
        new_o[k] = make_hash(v)

    obj_sorted = sorted(new_o.items(), key=lambda x: str(x[0]) if isinstance(x[0], int) else x[0])
    return hash(tuple(frozenset(obj_sorted)))
