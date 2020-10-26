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


# pylint: disable=too-many-return-statements
def is_filter_in_value(value, term, include):
    """
    Check recursively if any string value inside given item, has the current field's filter
    """
    if isinstance(value, str):
        return (term.lower() in value.lower()) == include
    if isinstance(value, int):
        return (term.lower() in str(value)) == include
    if isinstance(value, list):
        if include:
            return any(is_filter_in_value(item, term, include) for item in value)
        return all(is_filter_in_value(item, term, include) for item in value)
    if isinstance(value, dict):
        if include:
            return any(is_filter_in_value(item, term, include) for key, item in value.items())
        return all(is_filter_in_value(item, term, include) for key, item in value.items())
    return False


def filter_value(value, filters):
    for column_filter in filters:
        term = column_filter.get('term', '')
        include = column_filter.get('include', True)
        if isinstance(value, list):
            value = [item for item in value if is_filter_in_value(item, term, include)]
        if isinstance(value, dict):
            # complex field - should check for all it's values an return the whole object only
            # if all sub fields are matching the filter.
            value = {key: item for (key, item) in value.items()
                     if is_filter_in_value(item, term, include)}
        else:
            value = value if is_filter_in_value(value, term, include) else None
    return value


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
