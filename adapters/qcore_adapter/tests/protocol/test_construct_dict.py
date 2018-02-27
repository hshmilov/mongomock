import pytest
from qcore_adapter.protocol.build_helpers.construct_dict import dict_filter


def test_remove_none():
    d1 = {'a': [None, 1, 2, 3], 'b': None, 'c': {'d': 5, 'e': None}}
    d2 = dict_filter(d=d1, remove_predicate=lambda v: v is None)
    assert d1 == d2
    assert d1 == {'a': [None, 1, 2, 3], 'c': {'d': 5}}


if __name__ == '__main__':
    pytest.main([__file__])
