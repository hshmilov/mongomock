#!/usr/bin/env python3

import copy

import pytest
from bson.objectid import ObjectId

from axonius.consts.report_consts import (TRIGGERS_DIFF_ADDED,
                                          TRIGGERS_DIFF_REMOVED)
from plugins.reports.service import query_result_diff

RESULTS = [
    {
        '_id': ObjectId('5bd6efa11adb0100160a2fd3'),
        'specific_data': [
            {
                'data': {
                    'id': 'CN=WIN-1AFCDUDUN4T,CN=Computers,DC=TestDomain,DC=test'
                }
            }
        ]
    },
    {
        '_id': ObjectId('5bd6efa11adb0100160a2fd4'),
        'specific_data': [
            {
                'data': {
                    'id': 'CN=Win-Hostname-Mismatch,CN=Computers,DC=TestDomain,DC=test'
                }
            }
        ]
    },
    {
        '_id': ObjectId('5bd6efa11adb0100160a2fd5'),
        'specific_data': [
            {
                'data': {
                    'id': 'CN=EC2AMAZ-61GTBER,CN=Computers,DC=TestDomain,DC=test'
                }
            }
        ]
    },
    {
        '_id': ObjectId('5bd6efa11adb0100160a2fd6'),
        'specific_data': [
            {
                'data': {
                    'id': 'CN=WIN-QM01NAC82NR,CN=Computers,DC=TestDomain,DC=test'
                }
            }
        ]
    },
    {
        '_id': ObjectId('5bd6efa11adb0100160a2fd7'),
        'specific_data': [
            {
                'data': {
                    'id': 'CN=WIN-N5521ORHDL9,CN=Computers,DC=TestDomain,DC=test'
                }
            }
        ]
    },
    {
        '_id': ObjectId('5bd6efa11adb0100160a2fd8'),
        'specific_data': [
            {
                'data': {
                    'id': 'CN=AMAZON-87C533D4,CN=Computers,DC=TestDomain,DC=test'
                }
            }
        ]
    },
    {
        '_id': ObjectId('5bd6efa11adb0100160a2fd9'),
        'specific_data': [
            {
                'data': {
                    'id': 'CN=WIN-VGICH0DQCH7,CN=Computers,DC=TestDomain,DC=test'
                }
            }
        ]
    },
    {
        '_id': ObjectId('5bd6efa11adb0100160a2fda'),
        'specific_data': [
            {
                'data': {
                    'id': 'CN=EC2AMAZ-209VBI7,CN=Computers,DC=TestDomain,DC=test'
                }
            }
        ]
    },
    {
        '_id': ObjectId('5bd6efa11adb0100160a2fdb'),
        'specific_data': [
            {
                'data': {
                    'id': 'CN=WIN-4LGA2ONIDM6,CN=Computers,DC=TestDomain,DC=test'
                }
            }
        ]
    },
    {
        '_id': ObjectId('5bd6efa11adb0100160a2fdc'),
        'specific_data': [
            {
                'data': {
                    'id': 'CN=DCNY1,OU=Domain Controllers,DC=TestDomain,DC=test'
                }
            }
        ]
    },
    {
        '_id': ObjectId('5bd6efa11adb0100160a2fdd'),
        'specific_data': [
            {
                'data': {
                    'id': 'CN=WIN-I8QNMLDIKHR,CN=Computers,DC=TestDomain,DC=test'
                }
            }
        ]
    },
    {
        '_id': ObjectId('5bd6efa11adb0100160a2fde'),
        'specific_data': [
            {
                'data': {
                    'id': 'CN=WIN-D14VSGS3C0G,CN=Computers,DC=TestDomain,DC=test'
                }
            }
        ]
    },
    {
        '_id': ObjectId('5bd6efa11adb0100160a2fdf'),
        'specific_data': [
            {
                'data': {
                    'id': 'CN=TESTWINDOWS7,CN=Computers,DC=TestDomain,DC=test'
                }
            }
        ]
    },
    {
        '_id': ObjectId('5bd6efa11adb0100160a2fe0'),
        'specific_data': [
            {
                'data': {
                    'id': 'CN=22AD,CN=Computers,DC=TestDomain,DC=test'
                }
            }
        ]
    },
    {
        '_id': ObjectId('5bd6efa11adb0100160a2fe1'),
        'specific_data': [
            {
                'data': {
                    'id': 'CN=WIN-76F9735PMOJ,CN=Computers,DC=TestDomain,DC=test'
                }
            }
        ]
    },
    {
        '_id': ObjectId('5bd6efa11adb0100160a2fe2'),
        'specific_data': [
            {
                'data': {
                    'id': 'CN=WINDOWS8,CN=Computers,DC=TestDomain,DC=test'
                }
            }
        ]
    },
    {
        '_id': ObjectId('5bd6efa11adb0100160a2fe3'),
        'specific_data': [
            {
                'data': {
                    'id': 'CN=EC2AMAZ-V8E9DHF,CN=Computers,DC=TestDomain,DC=test'
                }
            }
        ]
    },
    {
        '_id': ObjectId('5bd6efa11adb0100160a2fe4'),
        'specific_data': [
            {
                'data': {
                    'id': 'CN=DESKTOP-MPP10U1,CN=Computers,DC=TestDomain,DC=test'
                }
            }
        ]
    },
    {
        '_id': ObjectId('5bd6efa11adb0100160a2fe5'),
        'specific_data': [
            {
                'data': {
                    'id': 'CN=DC1,OU=Domain Controllers,DC=TestDomain,DC=test'
                }
            }
        ]
    },
    {
        '_id': ObjectId('5bd6efa11adb0100160a2fe6'),
        'specific_data': [
            {
                'data': {
                    'id': 'CN=DC4,OU=Domain Controllers,DC=TestDomain,DC=test'
                }
            }
        ]
    },
    {
        '_id': ObjectId('5bd6efa11adb0100160a2fe7'),
        'specific_data': [
            {
                'data': {
                    'id': 'CN=DC2,OU=Domain Controllers,DC=TestDomain,DC=test'
                }
            }
        ]
    }
]


def test_not_changed():
    diff_dict = query_result_diff(RESULTS, RESULTS)
    assert diff_dict[TRIGGERS_DIFF_ADDED] == []
    assert diff_dict[TRIGGERS_DIFF_REMOVED] == []


def test_above():
    new_cycle = copy.deepcopy(RESULTS)
    old_cycle = copy.deepcopy(RESULTS)

    added_object = old_cycle.pop()

    diff_dict = query_result_diff(new_cycle, old_cycle)
    assert diff_dict[TRIGGERS_DIFF_ADDED] == [added_object]


def test_below():
    new_cycle = copy.deepcopy(RESULTS)
    old_cycle = copy.deepcopy(RESULTS)

    old_object = new_cycle.pop()

    diff_dict = query_result_diff(new_cycle, old_cycle)
    assert diff_dict[TRIGGERS_DIFF_REMOVED] == [old_object]


def test_correlation():
    new_cycle = copy.deepcopy(RESULTS)
    old_cycle = copy.deepcopy(RESULTS)

    fake_old_object = {'data': {'id': 'myfakeid'}}
    old_cycle[-1]['specific_data'].append(fake_old_object)

    fake_new_object = {'data': {'id': 'myfakeid2'}}
    new_cycle[0]['specific_data'].append(fake_new_object)

    diff_dict = query_result_diff(new_cycle, old_cycle)
    assert diff_dict[TRIGGERS_DIFF_ADDED] == []
    assert diff_dict[TRIGGERS_DIFF_REMOVED] == []

    old = old_cycle.pop(-1)

    diff_dict = query_result_diff(new_cycle, old_cycle)
    assert diff_dict[TRIGGERS_DIFF_ADDED] == [new_cycle[-1]]
    assert diff_dict[TRIGGERS_DIFF_REMOVED] == []

    new_cycle.pop(0)

    diff_dict = query_result_diff(new_cycle, old_cycle)
    assert diff_dict[TRIGGERS_DIFF_ADDED] == [new_cycle[-1]]
    assert diff_dict[TRIGGERS_DIFF_REMOVED] == [old_cycle[0]]


if __name__ == '__main__':
    pytest.main([__file__])
