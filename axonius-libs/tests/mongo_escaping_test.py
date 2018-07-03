from axonius.utils.mongo_escaping import *
import random


def test_escaping():
    cases = ["a.b", "a..b", "a...d", "a.#;b", "a#;.b"]
    for case in cases:
        assert unescape_key(escape_key(case)) == case, case
        assert '.' not in escape_key(case)


def test_escaping_random():
    for x in range(1000):
        case = ''.join(random.choice(list(TABLE.keys()) + list(TABLE.values())) for _ in range(20))
        assert unescape_key(escape_key(case)) == case, case
        assert '.' not in escape_key(case)


def test_recursive_escaping():
    d = {"a.b": {"c.d": "aaa", "x.k": [1, 2, 3]}, 55: "aa"}
    escaped = escape_dict(d)
    for key in escaped:
        if isinstance(key, str):
            assert '.' not in key, key

        value = escaped[key]
        if isinstance(value, dict):
            for k in value:
                assert '.' not in k


def test_similar_names():
    d = {
        "a.b": 1,
        "a##b": 2
    }
    escaped_d = escape_dict(dict(d))
    assert len(d) == len(escaped_d)


def test_fractions():
    d = {
        1.5: "asd"
    }
    assert str(list(escape_dict(d).keys())[0]) != "1.5"


if __name__ == '__main__':
    import pytest

    pytest.main(["mongo_escaping_test.py"])
