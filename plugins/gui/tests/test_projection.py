import random
from typing import Tuple

from axonius.utils.gui_helpers import _normalize_db_projection_for_aggregation


def test_regular():
    a = {
        'tags.data': 1,
        'tags.fun': 1
    }
    _normalize_db_projection_for_aggregation(a)
    assert a == {
        'tags.data': 1,
        'tags.fun': 1
    }


def test_previous_bug():
    a = {
        'tags.data': 1,
        'tags.data.something.asd': 1,
        'tags.data.something': 1,
    }
    _normalize_db_projection_for_aggregation(a)
    assert a == {
        'tags.data': 1
    }


def make_pair(size1: int, size2: int) -> Tuple[dict, dict]:
    base = {}
    for i in range(size1):
        for y in range(size2):
            base[f'base.{i}.{y}'] = 1
    cluttered = {}
    for k, v in base.items():
        cluttered[k] = v
        if random.randint(0, 3) == 1:
            for i in range(random.randint(0, 5)):
                cluttered[f'{k}.{i}'] = v
                for y in range(random.randint(0, 5)):
                    cluttered[f'{k}.{i}.{y}'] = v
                    for z in range(random.randint(0, 5)):
                        cluttered[f'{k}.{i}.{y}.{z}'] = v
        if random.randint(0, 3) == 2:
            cluttered[f'{k}.lol.fun.yay.yay'] = v
    return base, cluttered


def test_fuzz():
    for i in range(100):
        base, cluttered = make_pair(random.randint(0, 7), random.randint(0, 7))
        _normalize_db_projection_for_aggregation(cluttered)
        assert base == cluttered
