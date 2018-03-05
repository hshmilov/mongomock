"""
This is a default test we do just to check that our testing system works.
The following will be run by pytest.
"""

# we're actually testing ExecutionCorrelatorEngineBase here
from axonius.execution_correlator_engine_base import _find_contradictions, UNAVAILABLE_CMD_OUTPUT
from execution_correlator.engine import ExecutionCorrelatorEngine
import execution_correlator.engine as CE
import logging
import sys
from promise import Promise

from axonius.correlator_base import CorrelationResult, WarningResult
from axonius.consts.plugin_consts import PLUGIN_UNIQUE_NAME

correlator_logger = logging.getLogger()
correlator_logger.setLevel(logging.DEBUG)

ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter(' [Correlator] %(message)s')
ch.setFormatter(formatter)
correlator_logger.addHandler(ch)


def correlate(devices_db, executor=None, cmds=None, parse_results=None):
    def _executor(action_type, axon_id, data_for_action=None):
        if action_type == 'execute_shell':
            if executor:
                return executor(axon_id, data_for_action['shell_commands'])
            return None

    def default_get_remote_plugin_correlation_cmds(plugin_unique_name):
        print(f"default_get_remote_plugin_correlation_cmds: {plugin_unique_name}")
        return {}

    def default_parse_correlation_results(plugin_name, r):
        result = r['result']
        os = r['os']
        print(f"default_parse_correlation_results: {plugin_name}: {result}, {os}")
        if result == '':
            return None
        return result

    correlator = ExecutionCorrelatorEngine(_executor, cmds or default_get_remote_plugin_correlation_cmds,
                                           parse_results or default_parse_correlation_results, logger=correlator_logger)
    from datetime import timedelta
    CE.EXECUTE_TIMEOUT = timedelta(seconds=3)

    return correlator.correlate(devices_db)


def stupid_executor_fail(axon_id, shell_cmd):
    print(f"stupid_executor_fail: {axon_id} {shell_cmd}")
    return Promise.reject(Exception("Not working execution"))


def windows_unique_cmd_generator(plugin_unique_name):
    return {
        "Windows": f"{plugin_unique_name}"
    }


def join_with_order(execution_result, cmd_shell):
    cmd_shell = list(cmd_shell.values())[0]  # the list of operations for "Windows".
    # The following assumes we only have one command.
    result_ordered = [
        {
            "status": "ok",
            "data": execution_result.get(x, UNAVAILABLE_CMD_OUTPUT)
        } for x in cmd_shell]
    return result_ordered


def run_all():
    test_empty_correlation()
    test_no_correlations()
    test_simple_logic_correlation()
    test_execution_correlation()
    test_execution_nonexistent_device_nocorrelation()
    test_execution_nonexistent_device_deduction_correlation()
    test_partial_cmds_execution_correlation()
    test_multi_adapter_execution_correlation()
    test_execution_strongly_unbound_with()

    test_find_just_contradictions_no_contradictions()
    test_find_just_contradictions_with_contradictions()
    test_execution_correlation_contradiction()


def test_empty_correlation():
    devices = []
    assert len(list(correlate(devices, executor=stupid_executor_fail))) == 0


def test_no_correlations():
    devices = [
        {
            "internal_axon_id": "axon1",
            "tags": [],
            "adapters": [
                {
                    "plugin_name": "ad_adapter",
                    "plugin_unique_name": "ad_adapter_1",
                    "data": {
                        "os": {
                            "type": "Windows"
                        },
                        "id": "ad1"
                    }
                },
            ]
        },
        {
            "internal_axon_id": "axon2",
            "tags": [],
            "adapters": [
                {
                    "plugin_name": "esx_adapter",
                    "plugin_unique_name": "esx_adapter_1",
                    "data": {
                        "os": {
                            "type": "Windows"
                        },
                        "id": "esx2"
                    }
                }
            ]
        }
    ]
    assert len(list(correlate(devices, executor=stupid_executor_fail))) == 0

    print("Now, with smarter executor:\n\n")

    def smart_executor(axon_id, shell_cmd):
        associated_adapter = [d for d in devices if d['internal_axon_id'] == axon_id][0]['adapters'][0]
        ad_id = UNAVAILABLE_CMD_OUTPUT
        esx_id = UNAVAILABLE_CMD_OUTPUT
        if associated_adapter['plugin_name'] == 'esx_adapter':
            esx_id = 'esx2'
        if associated_adapter['plugin_name'] == 'ad_adapter':
            ad_id = 'ad1'

        executor_result = join_with_order({'ad_adapter_1': ad_id, 'esx_adapter_1': esx_id}, shell_cmd)
        print(f"smart_executor {executor_result}")

        return Promise.resolve({
            'output': {
                'product': executor_result,
                'result': 'Success',
            },
            'responder': associated_adapter[PLUGIN_UNIQUE_NAME]
        })

    correlations = list(correlate(devices, executor=smart_executor, cmds=windows_unique_cmd_generator))
    print(f"No correlations: {correlations}")
    assert len(correlations) == 0


def test_simple_logic_correlation():
    """
    Tests if correlators catches that two devices of different plugin_unique_name are the same
    :return:
    """
    devices = [
        {
            "internal_axon_id": "axon1",
            "tags": [],
            "adapters": [
                {
                    "plugin_name": "ad_adapter",
                    "plugin_unique_name": "ad_adapter_1",
                    "data": {
                        "os": {
                            "type": "Windows"
                        },
                        "id": "ad1"
                    }
                },
            ]
        },
        {
            "internal_axon_id": "axon2",
            "tags": [],
            "adapters": [
                {
                    "plugin_name": "ad_adapter",
                    "plugin_unique_name": "ad_adapter_2",
                    "data": {
                        "os": {
                            "type": "Windows"
                        },
                        "id": "ad2"
                    }
                }
            ]
        },
        {
            "internal_axon_id": "axon3",
            "tags": [],
            "adapters": [
                {
                    "plugin_name": "esx_adapter",
                    "plugin_unique_name": "esx_adapter_2",
                    "data": {
                        "os": {
                            "type": "Windows"
                        },
                        "id": "esx1"
                    }
                },
            ]
        },
        {
            "internal_axon_id": "axon4",
            "tags": [],
            "adapters": [
                {
                    "plugin_name": "ad_adapter",
                    "plugin_unique_name": "ad_adapter_2",
                    "data": {
                        "os": {
                            "type": "Windows"
                        },
                        "id": "ad1"
                    }
                },
            ]
        }
    ]
    results = list(correlate(devices, executor=stupid_executor_fail))
    print(f"RESULTS of execution are: {results}")
    assert len(results) == 1
    result = results[0]
    assert isinstance(result, CorrelationResult)
    assert len(result.associated_adapter_devices) == 2
    (first_name, first_id), (second_name, second_id) = result.associated_adapter_devices
    assert 'ad_adapter_1' == first_name
    assert 'ad_adapter_2' == second_name
    assert first_id == second_id
    print("Now, with smarter executor:\n\n")

    def specific_no_correlation_windows_executor(axon_id, shell_cmd):
        associated_adapter = list([x for x in devices if x['internal_axon_id'] == axon_id][0]['adapters'])[0]
        esx = UNAVAILABLE_CMD_OUTPUT
        ad = UNAVAILABLE_CMD_OUTPUT
        if associated_adapter['plugin_name'] == 'esx_adapter':
            esx = associated_adapter['data']['id']
        if associated_adapter['plugin_name'] == 'ad_adapter':
            ad = associated_adapter['data']['id']

        return Promise.resolve({
            'output': {
                'product': join_with_order({'ad_adapter_1': ad, 'esx_adapter_2': esx, 'ad_adapter_2': ad}, shell_cmd),
                'result': 'Success'
            },
            'responder': associated_adapter[PLUGIN_UNIQUE_NAME]
        })

    results = list(
        correlate(devices, executor=specific_no_correlation_windows_executor, cmds=windows_unique_cmd_generator))
    print(f"RESULTS of execution are: {results}")
    assert len(results) == 1
    result = results[0]
    assert isinstance(result, CorrelationResult)
    assert len(result.associated_adapter_devices) == 2
    (first_name, first_id), (second_name, second_id) = result.associated_adapter_devices
    assert 'ad_adapter_1' == first_name
    assert 'ad_adapter_2' == second_name
    assert first_id == second_id


def test_execution_correlation():
    """
    Tests if correlators catches that two devices of different plugin_unique_name are the same
    :return:
    """
    devices = [
        {
            "internal_axon_id": "axon1",
            "tags": [],
            "adapters": [
                {
                    "plugin_name": "ad_adapter",
                    "plugin_unique_name": "ad_adapter_1",
                    "data": {
                        "hostname": "ad1",
                        "os": {
                            "type": "Windows"
                        },
                        "id": "ad1"
                    }
                },
            ]
        },
        {
            "internal_axon_id": "axon2",
            "tags": [],
            "adapters": [
                {
                    "plugin_name": "esx_adapter",
                    "plugin_unique_name": "esx_adapter_1",
                    "data": {
                        "hostname": "esx1",
                        "os": {
                            "type": "Windows"
                        },
                        "id": "esx1"
                    }
                },
            ]
        },
    ]

    def specific_correlation_windows_executor(axon_id, shell_cmd):
        associated_adapter = list([x for x in devices if x['internal_axon_id'] == axon_id][0]['adapters'])[0]
        esx = UNAVAILABLE_CMD_OUTPUT
        ad = UNAVAILABLE_CMD_OUTPUT
        if associated_adapter['plugin_name'] == 'esx_adapter':
            esx = associated_adapter['data']['id']
            ad = 'ad1'
        if associated_adapter['plugin_name'] == 'ad_adapter':
            ad = associated_adapter['data']['id']

        return Promise.resolve({
            'output': {'product': join_with_order({'ad_adapter_1': ad, 'esx_adapter_1': esx}, shell_cmd),
                       'result': 'Success'
                       },
            'responder': associated_adapter[PLUGIN_UNIQUE_NAME]
        })

    results = list(
        correlate(devices, executor=specific_correlation_windows_executor, cmds=windows_unique_cmd_generator))
    print(f"RESULTS of execution are: {results}")
    assert len(results) == 1
    result = results[0]
    assert isinstance(result, CorrelationResult)
    assert len(result.associated_adapter_devices) == 2
    (first_name, first_id), (second_name, second_id) = result.associated_adapter_devices
    assert 'esx_adapter_1' == first_name
    assert 'ad_adapter_1' == second_name
    assert first_id == 'esx1'
    assert second_id == 'ad1'


def test_execution_nonexistent_device_nocorrelation():
    """
    Tests if correlators catches that two devices of different plugin_unique_name are the same
    :return:
    """
    devices = [
        {
            "internal_axon_id": "axon1",
            "tags": [],
            "adapters": [
                {
                    "plugin_name": "ad_adapter",
                    "plugin_unique_name": "ad_adapter_1",
                    "data": {
                        "hostname": "ad1",
                        "os": {
                            "type": "Windows"
                        },
                        "id": "ad1"
                    }
                },
            ]
        },
        {
            "internal_axon_id": "axon2",
            "tags": [],
            "adapters": [
                {
                    "plugin_name": "esx_adapter",
                    "plugin_unique_name": "esx_adapter_1",
                    "data": {
                        "hostname": "esx1",
                        "os": {
                            "type": "Windows"
                        },
                        "id": "esx1"
                    }
                },
            ]
        },
    ]

    def specific_correlation_windows_executor(axon_id, shell_cmd):
        associated_adapter = list([x for x in devices if x['internal_axon_id'] == axon_id][0]['adapters'])[0]
        esx = UNAVAILABLE_CMD_OUTPUT
        ad = UNAVAILABLE_CMD_OUTPUT
        if associated_adapter['plugin_name'] == 'esx_adapter':
            esx = associated_adapter['data']['id']
            ad = 'ad5'
        if associated_adapter['plugin_name'] == 'ad_adapter':
            ad = associated_adapter['data']['id']

        return Promise.resolve({
            'output': {'product': join_with_order({'ad_adapter_1': ad, 'esx_adapter_1': esx}, shell_cmd),
                       'result': 'Success'
                       },
            'responder': associated_adapter[PLUGIN_UNIQUE_NAME]
        })

    results = list(
        correlate(devices, executor=specific_correlation_windows_executor, cmds=windows_unique_cmd_generator))
    print(f"RESULTS of execution are: {results}")
    assert len(results) == 0


def test_execution_nonexistent_device_deduction_correlation():
    """
    Tests if correlators catches that two devices of different plugin_unique_name are the same
    :return:
    """
    devices = [
        {
            "internal_axon_id": "axon1",
            "tags": [],
            "adapters": [
                {
                    "plugin_name": "ad_adapter",
                    "plugin_unique_name": "ad_adapter_1",
                    "data": {
                        "hostname": "ad1",
                        "os": {
                            "type": "Windows"
                        },
                        "id": "ad1"
                    }
                },
            ]
        },
        {
            "internal_axon_id": "axon2",
            "tags": [],
            "adapters": [
                {
                    "plugin_name": "esx_adapter",
                    "plugin_unique_name": "esx_adapter_1",
                    "data": {
                        "hostname": "esx1",
                        "os": {
                            "type": "Windows"
                        },
                        "id": "esx1"
                    }
                },
            ]
        },
        {
            "internal_axon_id": "axon3",
            "tags": [],
            "adapters": [
                {
                    "plugin_name": "aws_adapter",
                    "plugin_unique_name": "aws_adapter_1",
                    "data": {
                        "hostname": "aws1",
                        "os": {
                            "type": "Windows"
                        },
                        "id": "aws1"
                    }
                },
            ]
        },
    ]

    all_adapter_devices = [adapter for adapters in devices for adapter in adapters['adapters']]

    def specific_correlation_windows_executor(axon_id, shell_cmd):
        associated_adapters = list([x for x in devices if x['internal_axon_id'] == axon_id][0]['adapters'])
        first_adapter = associated_adapters[-1]  # last adapter :D

        response = {adapter[PLUGIN_UNIQUE_NAME]: UNAVAILABLE_CMD_OUTPUT for adapter in all_adapter_devices}
        response.update({adapter[PLUGIN_UNIQUE_NAME]: adapter['data']['id'] for adapter in associated_adapters})

        if axon_id in ('axon1', 'axon2'):
            response['aws_adapter_1'] = 'aws5'

        return Promise.resolve({
            'output': {'product': join_with_order(response, shell_cmd),
                       'result': "Success"},
            'responder': first_adapter[PLUGIN_UNIQUE_NAME]
        })

    results = list(
        correlate(devices, executor=specific_correlation_windows_executor, cmds=windows_unique_cmd_generator))
    print(f"RESULTS of execution are: {results}")
    assert len(results) == 1
    result = results[0]
    assert isinstance(result, CorrelationResult)
    assert result.reason == "NonexistentDeduction"
    assert len(result.associated_adapter_devices) == 2
    (first_name, first_id), (second_name, second_id) = result.associated_adapter_devices
    assert ('esx_adapter_1' == first_name and 'ad_adapter_1' == second_name and
            first_id == 'esx1' and second_id == 'ad1') or \
           ('ad_adapter_1' == first_name and 'esx_adapter_1' == second_name and
            first_id == 'ad1' and second_id == 'esx1')


def test_partial_cmds_execution_correlation():
    """
    Tests if correlators catches that two devices of different plugin_unique_name are the same
    :return:
    """
    devices = [
        {
            "internal_axon_id": "axon1",
            "tags": [],
            "adapters": [
                {
                    "plugin_name": "ad_adapter",
                    "plugin_unique_name": "ad_adapter_1",
                    "data": {
                        "hostname": "ad1",
                        "os": {
                            "type": "Windows"
                        },
                        "id": "ad1"
                    }
                },
            ]
        },
        {
            "internal_axon_id": "axon2",
            "tags": [],
            "adapters": [
                {
                    "plugin_name": "esx_adapter",
                    "plugin_unique_name": "esx_adapter_1",
                    "data": {
                        "hostname": "esx1",
                        "os": {
                            "type": "Windows"
                        },
                        "id": "esx1"
                    }
                },
                {
                    "plugin_name": "aws_adapter",
                    "plugin_unique_name": "aws_adapter_1",
                    "data": {
                        "os": {
                            "type": "Windows"
                        },
                        "id": "aws1"
                    }
                },
            ]
        },
    ]

    all_adapter_devices = [adapter for adapters in devices for adapter in adapters['adapters']]

    def specific_correlation_windows_executor(axon_id, shell_cmd):
        associated_adapters = list([x for x in devices if x['internal_axon_id'] == axon_id][0]['adapters'])
        first_adapter = associated_adapters[0]  # first adapter :D

        response = {adapter[PLUGIN_UNIQUE_NAME]: UNAVAILABLE_CMD_OUTPUT for adapter in all_adapter_devices}
        response.update({adapter[PLUGIN_UNIQUE_NAME]: adapter['data']['id'] for adapter in associated_adapters})
        if first_adapter['plugin_name'] == 'ad_adapter':
            response['aws_adapter_1'] = 'aws1'

        output = join_with_order(response, shell_cmd)
        responder = first_adapter[PLUGIN_UNIQUE_NAME]

        print(f"test_partial_cmds execution: {output} for responder {responder} (cmd = {shell_cmd})")

        return Promise.resolve({
            'output': {
                'product': output,
                'result': "Success"},
            'responder': responder
        })

    def windows_some_unique_cmd_generator(plugin_unique_name):
        if plugin_unique_name == 'aws_adapter_1':
            return {
                "Windows": f"{plugin_unique_name}"
            }
        return {}

    results = list(
        correlate(devices, executor=specific_correlation_windows_executor, cmds=windows_some_unique_cmd_generator))
    print(f"RESULTS of execution are: {results}")
    assert len(results) == 1
    result = results[0]
    assert isinstance(result, CorrelationResult)
    assert len(result.associated_adapter_devices) == 2
    (first_name, first_id), (second_name, second_id) = result.associated_adapter_devices
    assert 'ad_adapter_1' == first_name
    assert 'aws_adapter_1' == second_name
    assert first_id == 'ad1'
    assert second_id == 'aws1'


def test_multi_adapter_execution_correlation():
    """
    Tests if correlators catches that two devices of different plugin_unique_name are the same
    :return:
    """
    devices = [
        {
            "internal_axon_id": "axon1",
            "tags": [],
            "adapters": [
                {
                    "plugin_name": "ad_adapter",
                    "plugin_unique_name": "ad_adapter_1",
                    "data": {
                        "hostname": "ad1",
                        "os": {
                            "type": "Windows"
                        },
                        "id": "ad1"
                    }
                },
            ]
        },
        {
            "internal_axon_id": "axon2",
            "tags": [],
            "adapters": [
                {
                    "plugin_name": "esx_adapter",
                    "plugin_unique_name": "esx_adapter_1",
                    "data": {
                        "hostname": "esx1",
                        "os": {
                            "type": "Windows"
                        },
                        "id": "esx1"
                    }
                },
                {
                    "plugin_name": "aws_adapter",
                    "plugin_unique_name": "aws_adapter_1",
                    "data": {
                        "hostname": "aws1",
                        "os": {
                            "type": "Windows"
                        },
                        "id": "aws1"
                    }
                },
            ]
        },
    ]

    all_adapter_devices = [adapter for adapters in devices for adapter in adapters['adapters']]

    def specific_correlation_windows_executor(axon_id, shell_cmd):
        associated_adapters = list([x for x in devices if x['internal_axon_id'] == axon_id][0]['adapters'])
        first_adapter = associated_adapters[-1]  # last adapter :D

        response = {adapter[PLUGIN_UNIQUE_NAME]: UNAVAILABLE_CMD_OUTPUT for adapter in all_adapter_devices}
        response.update({adapter[PLUGIN_UNIQUE_NAME]: adapter['data']['id'] for adapter in associated_adapters})
        if first_adapter['plugin_name'] == 'aws_adapter':
            response['ad_adapter_1'] = 'ad1'

        return Promise.resolve({
            'output': {'product': join_with_order(response, shell_cmd),
                       'result': 'Success'},
            'responder': first_adapter[PLUGIN_UNIQUE_NAME]
        })

    results = list(
        correlate(devices, executor=specific_correlation_windows_executor, cmds=windows_unique_cmd_generator))
    print(f"RESULTS of execution are: {results}")
    assert len(results) == 1
    result = results[0]
    assert isinstance(result, CorrelationResult)
    assert len(result.associated_adapter_devices) == 2
    (first_name, first_id), (second_name, second_id) = result.associated_adapter_devices
    assert 'aws_adapter_1' == first_name
    assert 'ad_adapter_1' == second_name
    assert first_id == 'aws1'
    assert second_id == 'ad1'


def test_find_just_contradictions_no_contradictions():
    devices = [
        {
            "internal_axon_id": "axon1",
            "tags": [],
            "adapters": [
                {
                    "plugin_name": "ad_adapter",
                    "plugin_unique_name": "ad_adapter_1",
                    "data": {
                        "hostname": "ad1",
                        "os": {
                            "type": "Windows"
                        },
                        "id": "ad1"
                    }
                },
                {
                    "plugin_name": "esx_adapter",
                    "plugin_unique_name": "esx_adapter_1",
                    "data": {
                        "hostname": "esx1",
                        "os": {
                            "type": "Windows"
                        },
                        "id": "esx1"
                    }
                }
            ]
        },
        {
            "internal_axon_id": "axon2",
            "tags": [],
            "adapters": [
                {
                    "plugin_name": "ad_adapter",
                    "plugin_unique_name": "ad_adapter_1",
                    "data": {
                        "hostname": "ad2",
                        "os": {
                            "type": "Windows"
                        },
                        "id": "ad2"
                    }
                },
                {
                    "plugin_name": "esx_adapter",
                    "plugin_unique_name": "esx_adapter_1",
                    "data": {
                        "hostname": "esx2",
                        "os": {
                            "type": "Windows"
                        },
                        "id": "esx2"
                    }
                }
            ]
        }
    ]
    assert len(list(_find_contradictions(devices, {}))) == 0
    assert len(list(_find_contradictions(devices,
                                         {
                                             0: ('responder', {
                                                 'some_plugin': 'some_id1'
                                             }),
                                             1: ('responder', {
                                                 'some_plugin': 'some_id2'
                                             })
                                         }
                                         ))) == 0
    assert len(list(_find_contradictions(devices,
                                         {
                                             0: ('responder', {
                                                 'ad_adapter': 'ad1',
                                                 'esx_adapter': 'esx1',
                                             }),
                                             1: ('responder', {
                                                 'ad_adapter': 'ad2',
                                                 'esx_adapter': 'esx2'
                                             })
                                         }
                                         ))) == 0


def test_find_just_contradictions_with_contradictions():
    devices = [
        {
            "internal_axon_id": "axon1",
            "tags": [],
            "adapters": [
                {
                    "plugin_name": "ad_adapter",
                    "plugin_unique_name": "ad_adapter_1",
                    "data": {
                        "hostname": "ad1",
                        "os": {
                            "type": "Windows"
                        },
                        "id": "ad1"
                    }
                },
                {
                    "plugin_name": "esx_adapter",
                    "plugin_unique_name": "esx_adapter_1",
                    "data": {
                        "hostname": "esx1",
                        "os": {
                            "type": "Windows"
                        },
                        "id": "esx1"
                    }
                }
            ]
        }
    ]
    execution_results = {
        0: ('responder', {
            'ad_adapter': 'ad3',
        })
    }
    contradictions_found = list(_find_contradictions(devices, execution_results))
    print(f"Found contradictions: {contradictions_found}")
    assert len(contradictions_found) == 1
    contra = contradictions_found[0]
    assert isinstance(contra, WarningResult)
    assert contra.notification_type == 'CORRELATION_CONTRADICTION'
    assert len(execution_results) == 0


def test_execution_correlation_contradiction():
    """
    Tests if correlators catches that two devices of different plugin_unique_name are the same
    :return:
    """
    devices = [
        {
            "internal_axon_id": "axon1",
            "tags": [],
            "adapters": [
                {
                    "plugin_name": "ad_adapter",
                    "plugin_unique_name": "ad_adapter_1",
                    "data": {
                        "hostname": "ad1",
                        "os": {
                            "type": "Windows"
                        },
                        "id": "ad1"
                    }
                },
                {
                    "plugin_name": "esx_adapter",
                    "plugin_unique_name": "esx_adapter_1",
                    "data": {
                        "hostname": "esx1",
                        "os": {
                            "type": "Windows"
                        },
                        "id": "esx1"
                    }
                },
                {
                    "plugin_name": "aws_adapter",
                    "plugin_unique_name": "aws_adapter_1",
                    "data": {
                        "hostname": "aws1",
                        "os": {
                            "type": "Windows"
                        },
                        "id": "aws1"
                    }
                },
            ]
        },
    ]

    all_adapter_devices = [adapter for adapters in devices for adapter in adapters['adapters']]

    def specific_correlation_windows_executor(axon_id, shell_cmd):
        associated_adapters = list([x for x in devices if x['internal_axon_id'] == axon_id][0]['adapters'])
        first_adapter = associated_adapters[-1]  # last adapter :D

        response = {adapter[PLUGIN_UNIQUE_NAME]: UNAVAILABLE_CMD_OUTPUT for adapter in all_adapter_devices}
        response.update({adapter[PLUGIN_UNIQUE_NAME]: adapter['data']['id'] for adapter in associated_adapters})

        response['ad_adapter_1'] = 'ad2'
        print(f"Response from test_execution_correlation_contradiction executor: {response}")

        return Promise.resolve({
            'output': {'product': join_with_order(response, shell_cmd),
                       'result': "Success"},
            'responder': first_adapter[PLUGIN_UNIQUE_NAME]
        })

    results = list(
        correlate(devices, executor=specific_correlation_windows_executor, cmds=windows_unique_cmd_generator))
    print(f"RESULTS of execution are: {results}")
    assert len(results) == 1
    result = results[0]
    assert isinstance(result, WarningResult)
    assert result.notification_type == 'CORRELATION_CONTRADICTION'
    assert result.content == ['axon1', 'ad_adapter', 'ad1', 'ad2']


def test_execution_strongly_unbound_with():
    devices = [
        {
            "internal_axon_id": "axon1",
            "tags": [{
                "name": "strongly_unbound_with",
                "data": [['esx_adapter', 'esx1']],
            }],
            "adapters": [
                {
                    "plugin_name": "ad_adapter",
                    "plugin_unique_name": "ad_adapter_1",
                    "data": {
                        "hostname": "ad1",
                        "os": {
                            "type": "Windows"
                        },
                        "id": "ad1"
                    }
                },
            ]
        },
        {
            "internal_axon_id": "axon2",
            "tags": [{
                "name": "strongly_unbound_with",
                "data": [['ad_adapter', 'ad1']],
            }],
            "adapters": [
                {
                    "plugin_name": "esx_adapter",
                    "plugin_unique_name": "esx_adapter_1",
                    "data": {
                        "hostname": "esx1",
                        "os": {
                            "type": "Windows"
                        },
                        "id": "esx1"
                    }
                },
            ]
        },
    ]

    def specific_correlation_windows_executor(axon_id, shell_cmd):
        associated_adapter = list([x for x in devices if x['internal_axon_id'] == axon_id][0]['adapters'])[0]
        esx = UNAVAILABLE_CMD_OUTPUT
        ad = UNAVAILABLE_CMD_OUTPUT
        if associated_adapter['plugin_name'] == 'esx_adapter':
            esx = associated_adapter['data']['id']
            ad = 'ad1'
        if associated_adapter['plugin_name'] == 'ad_adapter':
            ad = associated_adapter['data']['id']

        return Promise.resolve({
            'output': {'product': join_with_order({'ad_adapter_1': ad, 'esx_adapter_1': esx}, shell_cmd),
                       'result': "Success"},
            'responder': associated_adapter[PLUGIN_UNIQUE_NAME]
        })

    results = list(
        correlate(devices, executor=specific_correlation_windows_executor, cmds=windows_unique_cmd_generator))
    print(f"RESULTS of execution are: {results}")
    assert len(results) == 0
