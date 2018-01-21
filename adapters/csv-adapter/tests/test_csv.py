"""
This is a default test we do just to check that our testing system works.
The following will be run by pytest.
"""


def func(x):
    return x + 1


def test_answer():
    assert func(4) == 5
