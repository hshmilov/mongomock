import itertools
import uuid

from axonius.correlator_base import CorrelationResult
from axonius.consts.plugin_consts import PLUGIN_UNIQUE_NAME
from axonius.devices.device_adapter import NETWORK_INTERFACES_FIELD, IPS_FIELD, MAC_FIELD, OS_FIELD
from static_correlator.engine import StaticCorrelatorEngine


def correlate(devices):
    return list(StaticCorrelatorEngine().correlate(devices))


def test_empty():
    assert len(correlate([])) == 0


def get_raw_device(hostname=None, network_interfaces=None, os=None, serial=None):
    return {
        'tags': [],
        'adapters': [
            {
                'plugin_name': str(uuid.uuid1()),
                PLUGIN_UNIQUE_NAME: str(uuid.uuid1()),
                'data': {
                    'id': str(uuid.uuid1()),
                    OS_FIELD: os,
                    'hostname': hostname,
                    NETWORK_INTERFACES_FIELD: network_interfaces,
                    'device_serial': serial,
                }
            }
        ],
    }


def test_no_correlation():
    devices = [get_raw_device(hostname="ubuntuLolol",
                              os={'bitness': 32,
                                  'distribution': 'Ubuntu',
                                  'type': 'Linux'},
                              network_interfaces=[{MAC_FIELD: 'mymac',
                                                   IPS_FIELD: ['1.1.1.2']}]),
               get_raw_device(hostname="nothostname",
                              os={'bitness': 32,
                                  'distribution': 'Ubuntu',
                                  'type': 'NotLinux'},
                              network_interfaces=[{MAC_FIELD: 'mymac1',
                                                   IPS_FIELD: ['1.1.1.1']}])
               ]
    results = correlate(devices)
    assert len(results) == 0


def plugin_name(adapter):
    return adapter[PLUGIN_UNIQUE_NAME]


def device_id(adapter):
    return adapter['data']['id']


def assert_correlation(result, adapter1, adapter2):
    assert isinstance(result, CorrelationResult)
    assert len(result.associated_adapters) == 2
    (first_name, first_id), (second_name, second_id) = result.associated_adapters
    assert ((plugin_name(adapter1) == first_name and plugin_name(adapter2) == second_name) or
            (plugin_name(adapter1) == second_name and plugin_name(adapter2) == first_name))
    assert ((device_id(adapter1) == first_id and device_id(adapter2) == second_id) or
            (device_id(adapter1) == second_id and device_id(adapter2) == first_id))


def assert_success(results, device_list, reason, intended):
    intended_correlations = 0
    for result in results:
        if result.data['Reason'] == reason:
            intended_correlations += 1
            correlation_success = False
            adapters = [adapter for device in device_list for adapter in device['adapters']]
            for device1, device2 in itertools.combinations(adapters, 2):
                try:
                    assert_correlation(result, device1, device2)
                    correlation_success = True
                except AssertionError:
                    pass
            assert correlation_success
    assert intended_correlations == intended


def test_rule_ip_hostname_os_correlation():
    """
    Test a very simple correlation that should happen
    because IP+hostname+os
    :return:
    """
    device1 = get_raw_device(hostname="ubuntuLolol",
                             os={'bitness': 32,
                                 'distribution': 'Ubuntu',
                                 'type': 'Linux'},
                             network_interfaces=[{MAC_FIELD: 'myma324c',
                                                  IPS_FIELD: ['1.1.1.1']}])
    device2 = get_raw_device(hostname="ubuntulolol",
                             os={'bitness': 32,
                                 'distribution': 'Ubuntu',
                                 'type': 'Linux'},
                             network_interfaces=[{MAC_FIELD: 'mymac',
                                                  IPS_FIELD: ['1.1.1.1']}])
    assert_success(correlate([device1, device2]), [device1, device2], 'They have the same hostname and IPs', 1)


def test_rule_ip_host_os_no_correlation_due_to_ip():
    """
    Test a very simple correlation that should happen
    because IP+hostname+os
    :return:
    """
    device1 = get_raw_device(hostname="ubuntuLolol",
                             os={'bitness': 32,
                                 'distribution': 'Ubuntu',
                                 'type': 'Linux'},
                             network_interfaces=[{MAC_FIELD: 'mymac',
                                                  IPS_FIELD: None}])
    device2 = get_raw_device(hostname="ubuntulolol",
                             os={'bitness': 32,
                                 'distribution': 'Ubuntu',
                                 'type': 'Linux'},
                             network_interfaces=[{MAC_FIELD: 'mymac',
                                                  IPS_FIELD: ['1.1.1.1']}])
    assert_success(correlate([device1, device2]), [device1, device2], 'They have the same hostname and IPs', 0)


def test_rule_ip_host_os_no_correlation_due_to_hostname():
    """
    Test a very simple correlation that should happen
    because IP+hostname+os
    :return:
    """
    device1 = get_raw_device(hostname=None,
                             os={'bitness': 32,
                                 'distribution': 'Ubuntu',
                                 'type': 'Linux'},
                             network_interfaces=[{MAC_FIELD: 'mymac',
                                                  IPS_FIELD: ['1.1.1.1']}])
    device2 = get_raw_device(hostname="ubuntulolol",
                             os={'bitness': 32,
                                 'distribution': 'Ubuntu',
                                 'type': 'Linux'},
                             network_interfaces=[{MAC_FIELD: 'mymac',
                                                  IPS_FIELD: ['1.1.1.1']}])
    assert_success(correlate([device1, device2]), [device1, device2], 'They have the same hostname and IPs', 0)


def test_rule_ip_host_os_no_correlation_due_to_not_net_ifs():
    """
    Test a very simple correlation that should happen
    because IP+hostname+os
    :return:
    """
    device1 = get_raw_device(hostname='ubuntulolol',
                             os={'bitness': 32,
                                 'distribution': 'Ubuntu',
                                 'type': 'Linux'},
                             network_interfaces=[{MAC_FIELD: None,
                                                  IPS_FIELD: ['1.1.1.1']}])
    device2 = get_raw_device(hostname='ubuntulolol',
                             os={'bitness': 32,
                                 'distribution': 'Ubuntu',
                                 'type': 'Linux'},
                             network_interfaces=[])
    assert_success(correlate([device1, device2]), [device1, device2], 'They have the same hostname and IPs', 0)


def test_rule_ip_mac_os_correlation():
    """
    Test a very simple correlation that should happen
    because IP+MAC+os
    :return:
    """
    # hostname must be different otherwise we'll have 2 correlations for the same devices which is filtered
    device1 = get_raw_device(hostname="ubuntsaduLolol",
                             os={'bitness': 32,
                                 'distribution': 'Ubuntu',
                                 'type': 'Linux'},
                             network_interfaces=[{MAC_FIELD: 'AA-BB-CC-11-22-33',
                                                  IPS_FIELD: ['1.1.1.1']}])
    device2 = get_raw_device(hostname="ubuntulolol",
                             os={'bitness': 32,
                                 'distribution': 'Ubuntu',
                                 'type': 'Linux'},
                             network_interfaces=[{MAC_FIELD: 'AA:bb-CC-11-22-33',
                                                  IPS_FIELD: ['1.1.1.1']}])
    assert_success(correlate([device1, device2]), [device1, device2],
                   'They have the same MAC', 1)


def test_rule_ip_hostname_os_succeeds_even_with_domain():
    """
    Test a very simple correlation that should happen
    because IP+hostname+os
    :return:
    """
    device1 = get_raw_device(hostname="ubuntuLolol.local.axonius",
                             os={'bitness': 32,
                                 'distribution': 'Ubuntu',
                                 'type': 'Linux'},
                             network_interfaces=[{MAC_FIELD: 'myma324c',
                                                  IPS_FIELD: ['1.1.1.1']}])
    device2 = get_raw_device(hostname="ubuntulolol",
                             os={'bitness': 32,
                                 'distribution': 'Ubuntu',
                                 'type': 'Linux'},
                             network_interfaces=[{MAC_FIELD: 'mymac',
                                                  IPS_FIELD: ['1.1.1.1']}])
    assert_success(correlate([device1, device2]), [device1, device2], 'They have the same hostname and IPs', 1)


def test_rule_ip_hostname_os_fails_on_domains_not_default():
    """
    Test a very simple correlation that should happen
    because IP+hostname+os
    :return:
    """
    device1 = get_raw_device(hostname="ubuntuLolol.local.axonius",
                             os={'bitness': 32,
                                 'distribution': 'Ubuntu',
                                 'type': 'Linux'},
                             network_interfaces=[{MAC_FIELD: 'myma324c',
                                                  IPS_FIELD: ['1.1.1.1']}])
    device2 = get_raw_device(hostname="ubuntulolol.9",
                             os={'bitness': 32,
                                 'distribution': 'Ubuntu',
                                 'type': 'Linux'},
                             network_interfaces=[{MAC_FIELD: 'mymac',
                                                  IPS_FIELD: ['1.1.1.1']}])
    assert_success(correlate([device1, device2]), [device1, device2], 'They have the same hostname and IPs', 0)


def test_rule_ip_hostname_os_fails_hostname_even_after_domain():
    """
    Test a very simple correlation that should happen
    because IP+hostname+os
    :return:
    """
    device1 = get_raw_device(hostname="ubuntuLolol.local.axonius",
                             os={'bitness': 32,
                                 'distribution': 'Ubuntu',
                                 'type': 'Linux'},
                             network_interfaces=[{MAC_FIELD: 'myma324c',
                                                  IPS_FIELD: ['1.1.1.1']}])
    device2 = get_raw_device(hostname="ubuntulolol3.",
                             os={'bitness': 32,
                                 'distribution': 'Ubuntu',
                                 'type': 'Linux'},
                             network_interfaces=[{MAC_FIELD: 'mymac',
                                                  IPS_FIELD: ['1.1.1.1']}])
    assert_success(correlate([device1, device2]), [device1, device2], 'They have the same hostname and IPs', 0)


def test_rule_ip_hostname_os_fails_hostname_with_dot():
    """
    Test a very simple correlation that should happen
    because IP+hostname+os
    :return:
    """
    device1 = get_raw_device(hostname="ubuntuLolol.local.axonius",
                             os={'bitness': 32,
                                 'distribution': 'Ubuntu',
                                 'type': 'Linux'},
                             network_interfaces=[{MAC_FIELD: 'myma324c',
                                                  IPS_FIELD: ['1.1.1.1']}])
    device2 = get_raw_device(hostname="ubuntu.lolol",
                             os={'bitness': 32,
                                 'distribution': 'Ubuntu',
                                 'type': 'Linux'},
                             network_interfaces=[{MAC_FIELD: 'mymac',
                                                  IPS_FIELD: ['1.1.1.1']}])
    assert_success(correlate([device1, device2]), [device1, device2], 'They have the same hostname and IPs', 0)


def test_rule_ip_hostname_os_suceeds_with_default_and_nondefault_domain():
    """
    Test a very simple correlation that should happen
    because IP+hostname+os
    :return:
    """
    device1 = get_raw_device(hostname="ubuntuLolol.local",
                             os={'bitness': 32,
                                 'distribution': 'Ubuntu',
                                 'type': 'Linux'},
                             network_interfaces=[{MAC_FIELD: 'myma324c',
                                                  IPS_FIELD: ['1.1.1.1']}])
    device2 = get_raw_device(hostname="ubuntulolol.axonius",
                             os={'bitness': 32,
                                 'distribution': 'Ubuntu',
                                 'type': 'Linux'},
                             network_interfaces=[{MAC_FIELD: 'mymac',
                                                  IPS_FIELD: ['1.1.1.1']}])
    assert_success(correlate([device1, device2]), [device1, device2], 'They have the same hostname and IPs', 1)


def test_rule_ip_hostname_os_suceeds_with_default_domains():
    """
    Test a very simple correlation that should happen
    because IP+hostname+os
    :return:
    """
    device1 = get_raw_device(hostname="ubuntuLolol.local",
                             os={'bitness': 32,
                                 'distribution': 'Ubuntu',
                                 'type': 'Linux'},
                             network_interfaces=[{MAC_FIELD: 'myma324c',
                                                  IPS_FIELD: ['1.1.1.1']}])
    device2 = get_raw_device(hostname="ubuntulolol.workgroup",
                             os={'bitness': 32,
                                 'distribution': 'Ubuntu',
                                 'type': 'Linux'},
                             network_interfaces=[{MAC_FIELD: 'mymac',
                                                  IPS_FIELD: ['1.1.1.1']}])
    assert_success(correlate([device1, device2]), [device1, device2], 'They have the same hostname and IPs', 1)


def test_rule_one_is_ad_and_full_hostname():
    """
    Test a very simple correlation that should happen
    because IP+hostname+os
    :return:
    """
    device1 = get_raw_device(hostname="ubuntuLolol.local",
                             os={'bitness': 32,
                                 'distribution': 'Ubuntu',
                                 'type': 'Linux'},
                             network_interfaces=[{MAC_FIELD: 'mym234a324c',
                                                  IPS_FIELD: ['1.1.1.1']}])
    device2 = get_raw_device(hostname="ubuntuLolol.local",
                             os={'bitness': 32,
                                 'distribution': 'Ubuntu',
                                 'type': 'Linux'},
                             network_interfaces=[{MAC_FIELD: 'my234mac',
                                                  IPS_FIELD: ['1.31.1.1']}])
    device1['adapters'][0]['plugin_name'] = 'active_directory_adapter'
    device1['adapters'][0][PLUGIN_UNIQUE_NAME] = 'active_directory_adapter'
    device2['adapters'][0]['plugin_name'] = 'active_directory_adapter'
    device2['adapters'][0][PLUGIN_UNIQUE_NAME] = 'active_directory_adapter'
    assert_success(correlate([device1, device2]), [device1, device2], 'They have the same hostname and one is AD', 1)


def test_rule_one_is_ad_and_full_hostname_fail_on_hostname_even_with_default_domain():
    """
    Test a very simple correlation that should happen
    because IP+hostname+os
    :return:
    """
    device1 = get_raw_device(hostname="ubuntuLolol.local",
                             os={'bitness': 32,
                                 'distribution': 'Ubuntu',
                                 'type': 'Linux'},
                             network_interfaces=[{MAC_FIELD: 'mym234a324c',
                                                  IPS_FIELD: ['1.1.1.1']}])
    device2 = get_raw_device(hostname="ubuntuLolol",
                             os={'bitness': 32,
                                 'distribution': 'Ubuntu',
                                 'type': 'Linux'},
                             network_interfaces=[{MAC_FIELD: 'my234mac',
                                                  IPS_FIELD: ['1.31.1.1']}])
    device1['adapters'][0]['plugin_name'] = 'active_directory_adapter'
    device1['adapters'][0][PLUGIN_UNIQUE_NAME] = 'active_directory_adapter'
    device2['adapters'][0]['plugin_name'] = 'active_directory_adapter'
    device2['adapters'][0][PLUGIN_UNIQUE_NAME] = 'active_directory_adapter'
    assert_success(correlate([device1, device2]), [device1, device2], 'They have the same hostname and one is AD', 0)


def test_positive_serial_correlation():
    device1 = get_raw_device(serial="Some serial")
    device2 = get_raw_device(serial="Some serial")
    assert_success(correlate([device1, device2]), [device1, device2], 'They have the same serial', 1)


def test_positive_serial_correlation_capitaliztion():
    device1 = get_raw_device(serial="xDDDD123DDDDx")
    device2 = get_raw_device(serial="Xdddd123ddddX")
    assert_success(correlate([device1, device2]), [device1, device2], 'They have the same serial', 1)


def test_negative_serial_correlation_simple():
    device1 = get_raw_device()
    device2 = get_raw_device()
    assert_success(correlate([device1, device2]), [device1, device2], 'They have the same serial', 0)


def test_negative_serial_correlation_not_simple():
    device1 = get_raw_device(serial="Some serial1")
    device2 = get_raw_device(serial="Some serial2")
    assert_success(correlate([device1, device2]), [device1, device2], 'They have the same serial', 0)


if __name__ == '__main__':
    import pytest
    pytest.main([__file__])
