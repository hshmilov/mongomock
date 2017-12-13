from StaticCorrelatorEngine import StaticCorrelatorEngine, CorrelationResult, WarningResult

import logging
import sys

correlator_logger = logging.getLogger()
correlator_logger.setLevel(logging.DEBUG)

ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter(' [Correlator] %(message)s')
ch.setFormatter(formatter)
correlator_logger.addHandler(ch)


def correlate(devices):
    return StaticCorrelatorEngine(correlator_logger).correlate(devices)


def test_correlation():
    devices = [
        {
            'tags': [],
            'adapters': [
                {
                    'plugin_name': 'ad',
                    'plugin_unique_name': 'ad1',
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
            ],
        },
        {
            'tags': [],
            'adapters': [
                {
                    'plugin_name': 'esx',
                    'plugin_unique_name': 'esx1',
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
            ]
        }
    ]
    results = correlate(devices)
    wanted_result = None
    count = 0
    for result in results:
        count += 1
        wanted_result = result
    assert count == 1

    result = wanted_result
    assert isinstance(result, CorrelationResult)
    assert len(result.associated_adapter_devices) == 2
    (first_name, first_id), (second_name, second_id) = result.associated_adapter_devices
    assert (('ad1' == first_name and 'esx1' == second_name) or
            ('ad1' == second_name and 'esx1' == first_name))
    assert (('idad1' == first_id and 'idesx1' == second_id) or
            ('idad1' == second_id and 'idesx1' == first_id))
