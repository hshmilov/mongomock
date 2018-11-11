import itertools
import uuid

from axonius.consts.plugin_consts import PLUGIN_UNIQUE_NAME, PLUGIN_NAME
from axonius.devices.device_adapter import NETWORK_INTERFACES_FIELD, IPS_FIELD, MAC_FIELD, OS_FIELD
from axonius.types.correlation import CorrelationResult
from static_correlator.engine import StaticCorrelatorEngine
import datetime


def correlate(devices):
    return list(StaticCorrelatorEngine().correlate(devices))


def test_empty():
    assert len(correlate([])) == 0


def get_raw_tag(associated_adapter_unique_name, associated_adapter_name, associated_adapter_id, hostname=None,
                network_interfaces=None, os=None):
    generated_unique_name = str(uuid.uuid1())
    generate_name = str(uuid.uuid1())
    return {
        "association_type": "Tag",
        "associated_adapters": [
            [
                associated_adapter_unique_name, associated_adapter_id
            ]
        ],
        "associated_adapter_plugin_name": associated_adapter_name,
        "name": generated_unique_name,
        "data": {
            "hostname": hostname,
            OS_FIELD: os,
            NETWORK_INTERFACES_FIELD: network_interfaces,
        },
        "type": "adapterdata",
        "entity": "devices",
        "action_if_exists": "update",
        PLUGIN_UNIQUE_NAME: generated_unique_name,
        "plugin_name": generate_name
    }


def get_raw_device(plugin_name=None, hostname=None, network_interfaces=None, os=None, serial=None,
                   tag_data=None, last_seen=None, domain=None, device_id=None, more_params=None):
    if last_seen is None:
        last_seen = datetime.datetime.now()
    last_seen = last_seen.replace(tzinfo=None)
    generated_unique_name = str(uuid.uuid1()) if plugin_name is None else plugin_name + "0"
    generate_name = str(uuid.uuid1()) if plugin_name is None else plugin_name
    generated_id = device_id if device_id else str(uuid.uuid1())
    val = {
        'internal_axon_id': uuid.uuid1(),
        'tags': [],
        'adapters': [
            {
                'plugin_name': generate_name,
                PLUGIN_UNIQUE_NAME: generated_unique_name,
                'data': {
                    'id': generated_id,
                    OS_FIELD: os,
                    'hostname': hostname,
                    NETWORK_INTERFACES_FIELD: network_interfaces,
                    'device_serial': serial,
                    'last_seen': last_seen,
                    'domain': domain
                }
            }
        ],
    }
    # Updating other user defined params
    more_params = more_params if more_params is not None else []
    for (param_name, param_data) in more_params:
        val['adapters'][0]['data'][param_name] = param_data
    # Updating tag data
    if tag_data:
        val['tags'] = [get_raw_tag(generated_unique_name, generate_name, generated_id, *data) for data in tag_data]
    return val


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
    last_correlation_result = ''
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
        else:
            if result.data['Reason']:
                last_correlation_result = result.data['Reason']
    assert intended_correlations == intended, f"last correlation result: {last_correlation_result}"


def test_rule_domain_hostname_correlation():
    """
    Checking domain + host name
    :return:
    """
    device1 = get_raw_device(hostname="ubuntuLolol",
                             os={'bitness': 32,
                                 'distribution': 'Ubuntu',
                                 'type': 'Linux'},
                             domain='TEST',
                             network_interfaces=[{MAC_FIELD: 'myma324c',
                                                  IPS_FIELD: ['1.1.1.2']}])
    device2 = get_raw_device(hostname="ubuntulolol",
                             os={'bitness': 32,
                                 'distribution': 'Ubuntu',
                                 'type': 'Linux'},
                             domain='Test',
                             network_interfaces=[{MAC_FIELD: 'mymac',
                                                  IPS_FIELD: ['1.1.1.1']}])
    assert_success(correlate([device1, device2]), [device1, device2], 'They have the same hostname and domain', 1)


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


def test_rule_ip_hostname_special_osx():
    """
    Test a very simple correlation that should happen
    because IP+hostname+os. We should use only the hostname before the '.' because of special correlation rule for OS X
    :return:
    """
    device1 = get_raw_device(hostname="ubuntuLololwithextra.con",
                             os={'bitness': 32,
                                 'distribution': 'Ubuntu',
                                 'type': 'OS X'},
                             network_interfaces=[{MAC_FIELD: 'myma324c',
                                                  IPS_FIELD: ['1.1.1.1']}])
    device2 = get_raw_device(plugin_name='active_directory_adapter',
                             hostname="ubuntulololwith.co.il.local",
                             os={'bitness': 32,
                                 'distribution': 'Ubuntu',
                                 'type': 'OS X'},
                             network_interfaces=[{MAC_FIELD: 'mymac',
                                                  IPS_FIELD: ['1.1.1.1']}])
    assert_success(correlate([device1, device2]), [device1, device2], 'They have the same hostname and IPs', 1)


def test_no_correlation_special_osx():
    """
    Test a very simple correlation that should happen
    because IP+hostname+os. We should use only the hostname before the '.' because of special correlation rule for OS X
    :return:
    """
    device1 = get_raw_device(hostname="ubuntuLololwithextra.con",
                             os={'bitness': 32,
                                 'distribution': 'Ubuntu',
                                 'type': 'Linux'},
                             network_interfaces=[{MAC_FIELD: 'myma324c',
                                                  IPS_FIELD: ['1.1.1.1']}])
    device2 = get_raw_device(hostname="ubuntulolol.co.il.local",
                             os={'bitness': 32,
                                 'distribution': 'Ubuntu',
                                 'type': 'OS X'},
                             network_interfaces=[{MAC_FIELD: 'mymac',
                                                  IPS_FIELD: ['1.1.1.1']}])
    results = correlate([device1, device2])
    assert len(results) == 0


def test_rule_ip_no_hostame_yes_mac_correlation():
    """
    Test a very simple correlation that should happen
    because IP+hostname+os
    :return:
    """
    device1 = get_raw_device(hostname="ubuntuLolol",
                             os={'bitness': 32,
                                 'distribution': 'Ubuntu',
                                 'type': 'Linux'},
                             network_interfaces=[{MAC_FIELD: '11111111',
                                                  IPS_FIELD: ['1.1.1.2']}],
                             last_seen=datetime.datetime.now().replace(tzinfo=None) - datetime.timedelta(days=40))
    device2 = get_raw_device(hostname="ubuntulolol",
                             os={'bitness': 32,
                                 'distribution': 'Ubuntu',
                                 'type': 'Linux'},
                             network_interfaces=[{MAC_FIELD: '11111111',
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
    device1 = get_raw_device(os={'bitness': 32,
                                 'distribution': 'Ubuntu',
                                 'type': 'Linux'},
                             network_interfaces=[{MAC_FIELD: 'AA-BB-CC-11-22-33',
                                                  IPS_FIELD: ['1.1.1.1']}])
    device2 = get_raw_device(os={'bitness': 32,
                                 'distribution': 'Ubuntu',
                                 'type': 'Linux'},
                             network_interfaces=[{MAC_FIELD: 'AA:bb-CC-11-22-33',
                                                  IPS_FIELD: ['1.1.1.1']}])
    assert_success(correlate([device1, device2]), [device1, device2],
                   'They have the same MAC', 1)


def test_rule_ip_mac_os_correlation_old():
    """
    Test a very simple correlation that should happen
    because IP+MAC+os
    :return:
    """
    # hostname must be different otherwise we'll have 2 correlations for the same devices which is filtered
    device1 = get_raw_device(os={'bitness': 32,
                                 'distribution': 'Ubuntu',
                                 'type': 'Linux'},
                             network_interfaces=[{MAC_FIELD: 'AA-BB-CC-11-22-33',
                                                  IPS_FIELD: ['1.1.1.1']}],
                             last_seen=datetime.datetime.now().replace(tzinfo=None) - datetime.timedelta(days=40))
    device2 = get_raw_device(os={'bitness': 32,
                                 'distribution': 'Ubuntu',
                                 'type': 'Linux'},
                             network_interfaces=[{MAC_FIELD: 'AA:bb-CC-11-22-33',
                                                  IPS_FIELD: ['1.1.1.1']}])
    assert_success(correlate([device1, device2]), [device1, device2],
                   'They have the same MAC', 0)


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
    device1['adapters'][0][PLUGIN_UNIQUE_NAME] = 'active_directory_adapter1'
    device2['adapters'][0]['plugin_name'] = 'active_directory_adapter'
    device2['adapters'][0][PLUGIN_UNIQUE_NAME] = 'active_directory_adapter2'
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


def test_simple_tag_correlation():
    network_interfaces = [{MAC_FIELD: "mymac"}]

    device1 = get_raw_device(tag_data=[[None, network_interfaces]])
    device2 = get_raw_device(network_interfaces=network_interfaces)
    assert_success(correlate([device1, device2]), [device1, device2], 'They have the same MAC', 1)


def test_no_tag_self_correlation():
    network_interfaces = [{MAC_FIELD: "mymac"}]
    device1 = get_raw_device(network_interfaces=network_interfaces, tag_data=[[None, network_interfaces]])
    assert_success(correlate([device1]), [device1], 'They have the same MAC', 0)


def test_no_tag_self_correlation2():
    network_interfaces = [{MAC_FIELD: "mymac"}]

    # creating a device with 2 adapters (no MAC)
    # and 5 tags (all with the same MAC): 3 are to the first adapter, 2 are to the second
    # no correlation should occur because they are all the same axonius device
    device1 = get_raw_device(
        tag_data=[[None, network_interfaces], [None, network_interfaces], [None, network_interfaces]])
    device1['adapters'].append({
        'plugin_name': 'pn',
        PLUGIN_UNIQUE_NAME: 'pun',
        'data': {
            'id': 'id1',
        }
    })
    device1['tags'].append({
        "association_type": "Tag",
        "associated_adapters": [
            [
                'pun', 'id1'
            ]
        ],
        "associated_adapter_plugin_name": 'pn',
        "name": 'some_name',
        "data": {
            NETWORK_INTERFACES_FIELD: network_interfaces,
        },
        "type": "adapterdata",
        "entity": "devices",
        "action_if_exists": "update",
    })
    device1['tags'].append({
        "association_type": "Tag",
        "associated_adapters": [
            [
                'pun', 'id1'
            ]
        ],
        "associated_adapter_plugin_name": 'pn',
        "name": 'some_name2',
        "data": {
            NETWORK_INTERFACES_FIELD: network_interfaces,
        },
        "type": "adapterdata",
        "entity": "devices",
        "action_if_exists": "update",
    })
    assert_success(correlate([device1]), [device1], 'They have the same MAC', 0)


def test_no_zero_mac():
    """
    Test that zero-macs aren't correlated
    """
    device1 = get_raw_device(network_interfaces=[{MAC_FIELD: '000000000000',
                                                  IPS_FIELD: ['1.1.1.1']}])
    device2 = get_raw_device(network_interfaces=[{MAC_FIELD: '000000000000',
                                                  IPS_FIELD: ['1.1.1.1']}])
    assert_success(correlate([device1, device2]), [device1, device2], 'They have the same MAC', 0)


def test_no_mac_with_hostname_contradiction():
    """
    Test that macs aren't correlated if hostname contradicts
    """
    device1 = get_raw_device(network_interfaces=[{MAC_FIELD: '121212121212',
                                                  IPS_FIELD: ['1.1.1.1']}],
                             hostname="host1",
                             plugin_name="adapter_test")
    device2 = get_raw_device(network_interfaces=[{MAC_FIELD: '121212121212',
                                                  IPS_FIELD: ['1.1.1.1']}],
                             hostname="host2",
                             plugin_name="adapter_test")
    assert_success(correlate([device1, device2]), [device1, device2], 'They have the same MAC', 0)


def test_contradiction_rules_per_hostname():
    device1 = get_raw_device(serial="Some serial", hostname="A")
    device2 = get_raw_device(serial="Some serial", hostname="B")
    assert_success(correlate([device1, device2]), [device1, device2], 'They have the same serial', 0)


def test_rule_correlate_cloud_instances():
    device1 = get_raw_device(more_params=[("cloud_provider", "SomeCloudProvider"), ("cloud_id", "SomeCloudId")])
    device2 = get_raw_device(more_params=[("cloud_provider", "someCloudProvider"), ("cloud_id", "someCloudId")])
    assert_success(correlate([device1, device2]), [device1, device2], 'They are the same cloud instance', 1)


def test_rule_correlate_ad_sccm_id():
    device1 = get_raw_device(plugin_name='active_directory_adapter', device_id='SomeDeviceId')
    device2 = get_raw_device(plugin_name='sccm_adapter', device_id='SomeDeviceId')
    assert_success(correlate([device1, device2]), [device1, device2], 'They have the same ID and one is AD and the '
                                                                      'second is SCCM', 1)


def test_rule_correlate_ad_azure_ad():
    device1 = get_raw_device(plugin_name='active_directory_adapter', device_id='SomeDeviceId',
                             more_params=[("ad_name", "ofir")])
    device2 = get_raw_device(plugin_name='azure_ad_adapter', device_id='SomeDeviceId',
                             more_params=[("azure_display_name", "Ofir")])
    assert_success(correlate([device1, device2]), [device1, device2], 'They have the same display name', 1)


def test_rule_correlate_with_juniper():
    device1 = get_raw_device(plugin_name='junos_adapter', device_id='SomeDeviceId',
                             more_params=[("name", "ofir")])
    device2 = get_raw_device(plugin_name='juniper_adapter', device_id='SomeDeviceId',
                             more_params=[("name", "Ofir"), ('device_type', 'Juniper Space Device')])
    assert_success(correlate([device1, device2]), [device1, device2], 'Juniper devices with same asset name', 1)


def test_rule_correlate_hostname_user():
    device1 = get_raw_device(plugin_name='junos_adapter', device_id='SomeDeviceId', hostname="Ofir",
                             more_params=[("last_used_users", ["ofir"])])
    device2 = get_raw_device(plugin_name='juniper_adapter', device_id='SomeDeviceId', hostname="ofir",
                             more_params=[("last_used_users", ["Ofir"]), ('device_type', 'Juniper Space Device')])
    assert_success(correlate([device1, device2]), [device1, device2], 'They have the same hostname and LastUsedUser', 1)


def test_rule_correlate_asset_host():
    device1 = get_raw_device(plugin_name='aws_adapter', device_id='SomeDeviceId',
                             network_interfaces=[{IPS_FIELD: ['1.1.1.1']}],
                             more_params=[("name", "Ofir")])
    device2 = get_raw_device(plugin_name='esx_adapter', device_id='SomeDeviceId',
                             network_interfaces=[{IPS_FIELD: ['1.1.1.1']}],
                             more_params=[("name", "Ofir"), ('device_type', 'Juniper Space Device')])
    assert_success(correlate([device1, device2]), [device1, device2], 'They have the same Asset name', 1)


def test_rule_correlate_hostname_deep_security():
    device1 = get_raw_device(plugin_name='deep_security_adapter', device_id='SomeDeviceId', hostname="ofir",
                             network_interfaces=[{IPS_FIELD: ['1.1.1.1']}],
                             more_params=[("name", "Ofir")])
    device2 = get_raw_device(plugin_name='esx_adapter', device_id='SomeDeviceId', hostname="ofir",
                             more_params=[("name", "Ofir"), ('device_type', 'Juniper Space Device')])
    assert_success(correlate([device1, device2]), [device1, device2], 'They have the same hostname '
                                                                      'and one is DeepSecurity', 1)


def test_rule_correlate_ip_linux_illusive():
    device1 = get_raw_device(plugin_name='illusive_adapter', device_id='SomeDeviceId',
                             network_interfaces=[{IPS_FIELD: ['1.1.1.1']}], os={'type': 'linux'})
    device2 = get_raw_device(plugin_name='esx_adapter', device_id='SomeDeviceId', hostname="ofir",
                             network_interfaces=[{IPS_FIELD: ['1.1.1.1']}], os={'type': 'linux'})
    assert_success(correlate([device1, device2]), [device1, device2], 'They have the same IP one is Illusive '
                                                                      'and They are Linux', 1)


def test_rule_correlate_splunk_vpn_hostname():
    device1 = get_raw_device(plugin_name='splunk_adapter', device_id='SomeDeviceId', hostname="ofir",
                             more_params=[("splunk_source", "VPN")])
    device2 = get_raw_device(plugin_name='splunk_adapter', device_id='SomeDeviceId2', hostname="ofir",
                             network_interfaces=[{IPS_FIELD: ['1.1.1.1']}], os={'type': 'linux'},
                             more_params=[("splunk_source", "VPN")])
    assert_success(correlate([device1, device2]), [device1, device2], 'They have the same Normalized hostname '
                                                                      'and both are Splunk VPN', 1)


def test_no_correlation_if_ad_present():
    device1 = get_raw_device(
        plugin_name='blat_plugin',
        hostname="ubuntuLolol",
        os={'bitness': 32,
            'distribution': 'Ubuntu',
            'type': 'Linux'},
        domain='TEST',
        network_interfaces=[{MAC_FIELD: 'myma324c',
                             IPS_FIELD: ['1.1.1.2']}])
    device1['adapters'].append({
        PLUGIN_NAME: 'active_directory',
        PLUGIN_UNIQUE_NAME: 'active_directory_1',
        'data': {
            'id': 'lala1'
        }
    })
    device2 = get_raw_device(hostname="ubuntulolol",
                             os={'bitness': 32,
                                 'distribution': 'Ubuntu',
                                 'type': 'Linux'},
                             domain='Test',
                             network_interfaces=[{MAC_FIELD: 'mymac',
                                                  IPS_FIELD: ['1.1.1.1']}])
    device2['adapters'].append({
        PLUGIN_NAME: 'active_directory',
        PLUGIN_UNIQUE_NAME: 'active_directory_1',
        'data': {
            'id': 'lala2'
        }
    })
    assert_success(correlate([device1, device2]), [device1, device2], 'They have the same hostname and domain', 0)


def test_correlation_if_ad_present_and_only_it_gets():
    device1 = get_raw_device(
        plugin_name='active_directory',
        hostname="ubuntuLolol",
        os={'bitness': 32,
            'distribution': 'Ubuntu',
            'type': 'Linux'},
        domain='TEST',
        network_interfaces=[{MAC_FIELD: 'myma324c',
                             IPS_FIELD: ['1.1.1.2']}])
    device1['adapters'].append({
        PLUGIN_NAME: 'blat_adapter',
        PLUGIN_UNIQUE_NAME: 'blat_adapter_1',
        'data': {
            'id': 'lala1',
            'hostname': 'blat',
            'network_interfaces': [{MAC_FIELD: 'mymac',
                                    IPS_FIELD: ['1.1.1.1']}]
        }
    })
    device2 = get_raw_device(
        plugin_name='active_directory',
        hostname="ubuntulolol",
        os={'bitness': 32,
            'distribution': 'Ubuntu',
            'type': 'Linux'},
        domain='Test',
        network_interfaces=[{MAC_FIELD: 'mymac',
                             IPS_FIELD: ['1.1.1.1']}])
    device2['adapters'].append({
        PLUGIN_NAME: 'blat_adapter',
        PLUGIN_UNIQUE_NAME: 'blat_adapter_1',
        'data': {
            'id': 'lala2',
            'hostname': 'blat',
            'network_interfaces': [{MAC_FIELD: 'mymac',
                                    IPS_FIELD: ['1.1.1.1']}]
        }
    })
    res = list(correlate([device1, device2]))
    assert len(res) == 1


if __name__ == '__main__':
    import pytest

    pytest.main([__file__])
