from static_correlator_engine import StaticCorrelatorEngine

import logging
import sys

from axonius.correlator_base import CorrelationResult
from axonius.consts.plugin_consts import PLUGIN_UNIQUE_NAME

correlator_logger = logging.getLogger()
correlator_logger.setLevel(logging.DEBUG)

ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter(' [Correlator] %(message)s')
ch.setFormatter(formatter)
correlator_logger.addHandler(ch)


def correlate(devices):
    res = list(StaticCorrelatorEngine(correlator_logger).correlate(devices))
    print(res)
    return res


def run_all():
    test_empty()
    test_no_correlation()
    test_rule1_correlation()
    test_rule1_os_contradiction()


def test_empty():
    assert len(correlate([])) == 0


def test_no_correlation():
    devices = [
        {
            'tags': [],
            'adapters': [
                {
                    'plugin_name': 'ad1',
                    PLUGIN_UNIQUE_NAME: 'ad1',
                    'data': {
                        'id': "idad1",
                        'OS': {
                            'bitness': 32,
                            'distribution': 'Ubuntu',
                            'type': 'Linux'
                        },
                        'hostname': "ubuntuLolol",  # Capital letter in in purpose
                        'network_interfaces': [{
                            'MAC': 'mymac',
                            'IP': [
                                '1.1.1.2'
                            ]
                        }
                        ]
                    }
                }
            ],
        },
        {
            'tags': [],
            'adapters': [
                {
                    'plugin_name': 'ad2',
                    PLUGIN_UNIQUE_NAME: 'ad2',
                    'data': {
                        'id': "idad2",
                        'OS': {
                            'bitness': 32,
                            'distribution': 'Ubuntu',
                            'type': 'Linux'
                        },
                        'hostname': "ubuntulolol",
                        'network_interfaces': [{
                            'MAC': 'mymac',
                            'IP': [
                                '1.1.1.1'
                            ]
                        }
                        ]
                    }
                }
            ]
        },
        {
            'tags': [],
            'adapters': [
                {
                    'plugin_name': 'ad3',
                    PLUGIN_UNIQUE_NAME: 'ad3',
                    'data': {
                        'id': "idad3",
                        'OS': {
                            'bitness': 32,
                            'distribution': 'Ubuntu',
                            'type': 'NotLinux'
                        },
                        'hostname': "ubuntulolol",
                        'network_interfaces': [{
                            'MAC': 'mymac',
                            'IP': [
                                '1.1.1.1'
                            ]
                        }
                        ]
                    }
                }
            ]
        },
        {
            'tags': [],
            'adapters': [
                {
                    'plugin_name': 'ad4',
                    PLUGIN_UNIQUE_NAME: 'ad4',
                    'data': {
                        'id': "idad4",
                        'OS': {
                            'bitness': 32,
                            'distribution': 'Ubuntu',
                            'type': 'NotLinux'
                        },
                        'hostname': "nothostname",
                        'network_interfaces': [{
                            'MAC': 'mymac',
                            'IP': [
                                '1.1.1.1'
                            ]
                        }
                        ]}
                }
            ]
        }
    ]
    results = correlate(devices)
    assert len(results) == 0


def test_rule1_correlation():
    """
    Test a very simple correlation that should happen
    because IP+HOSTNAME+OS
    :return:
    """
    devices = [
        {
            'tags': [],
            'adapters': [
                {
                    'plugin_name': 'ad',
                    PLUGIN_UNIQUE_NAME: 'ad1',
                    'data': {
                        'id': "idad1",
                        'OS': {
                            'bitness': 32,
                            'distribution': 'Ubuntu',
                            'type': 'Linux'
                        },
                        'hostname': "ubuntuLolol",  # Capital letter in in purpose
                        'network_interfaces': [{
                            'MAC': 'mymac',
                            'IP': [
                                '1.1.1.1'
                            ]
                        }
                        ]}
                }
            ],
        },
        {
            'tags': [],
            'adapters': [
                {
                    'plugin_name': 'esx',
                    PLUGIN_UNIQUE_NAME: 'esx1',
                    'data': {
                        'id': "idesx1",
                        'OS': {
                            'bitness': 32,
                            'distribution': 'Ubuntu',
                            'type': 'Linux'
                        },
                        'hostname': "ubuntulolol",
                        'network_interfaces': [{
                            'MAC': 'mymac',
                            'IP': [
                                '1.1.1.1'
                            ]
                        }
                        ]
                    }
                }
            ]
        }
    ]
    results = correlate(devices)
    assert len(results) == 1

    result = results[0]
    assert isinstance(result, CorrelationResult)
    assert len(result.associated_adapter_devices) == 2
    (first_name, first_id), (second_name, second_id) = result.associated_adapter_devices
    assert (('ad1' == first_name and 'esx1' == second_name) or
            ('ad1' == second_name and 'esx1' == first_name))
    assert (('idad1' == first_id and 'idesx1' == second_id) or
            ('idad1' == second_id and 'idesx1' == first_id))


def test_rule1_os_contradiction():
    """
    Test a very simple correlation that should happen
    because IP+HOSTNAME+OS
    :return:
    """
    devices = [
        {
            'internal_axon_id': 'Mark_you_destroyed_our_life',
            'tags': [],
            'adapters': [
                {
                    'plugin_name': 'ad',
                    PLUGIN_UNIQUE_NAME: 'ad1',
                    'data': {
                        'id': "idad1",
                        'OS': {
                            'bitness': 32,
                            'distribution': 'Ubuntu',
                            'type': 'Linux'
                        },
                        'hostname': "ubuntuLolol",  # Capital letter in in purpose
                        'network_interfaces': [{
                            'MAC': 'mymac',
                            'IP': [
                                '1.1.1.1'
                            ]
                        }
                        ]
                    }
                }
            ],
        },
        {
            'internal_axon_id': 'Mark_you_destroyed_our_life2',
            'tags': [],
            'adapters': [
                {
                    'plugin_name': 'esx',
                    PLUGIN_UNIQUE_NAME: 'esx1',
                    'data': {
                        'id': "idesx1",
                        'OS': {
                            'bitness': 32,
                            'distribution': 'Ubuntu',
                            'type': 'NotLinux'
                        },
                        'hostname': "ubuntulolol",
                        'network_interfaces': [{
                            'MAC': 'mymac',
                            'IP': [
                                '1.1.1.1'
                            ]
                        }
                        ]}
                },
                {
                    'plugin_name': 'aws',
                    PLUGIN_UNIQUE_NAME: 'aws1',
                    'data': {
                        'id': "idaws1",
                        'OS': {
                            'bitness': 32,
                            'distribution': 'Ubuntu',
                            'type': 'Linux'
                        },
                        'hostname': "ubuntulolol",
                        'network_interfaces': [{
                            'MAC': 'mymac',
                            'IP': [
                                '1.1.1.1'
                            ]
                        }
                        ]
                    }
                }
            ]
        }
    ]
    results = correlate(devices)
    assert len(results) == 0
