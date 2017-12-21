"""
This is a default test we do just to check that our testing system works.
The following will be run by pytest.
"""

# we're actually testing ExecutionCorrelatorEngineBase here
import logging

import sys
from CarefulExecutionCorrelatorEngine import CarefulExecutionCorrelatorEngine

correlator_logger = logging.getLogger()
correlator_logger.setLevel(logging.DEBUG)

ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter(' [Correlator] %(message)s')
ch.setFormatter(formatter)
correlator_logger.addHandler(ch)


def filterdevices(devices_db, executor=None, cmds=None, parse_results=None):
    def _executor(action_type, axon_id, data_for_action=None):
        if action_type == 'execute_shell':
            if executor:
                return executor(axon_id, data_for_action['shell_command'])
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

    correlator = CarefulExecutionCorrelatorEngine(_executor, cmds or default_get_remote_plugin_correlation_cmds,
                                                  parse_results or default_parse_correlation_results,
                                                  logger=correlator_logger)

    r = list(correlator._prefilter_device(devices_db))
    print(f"len = {len(r)};\n{r}")
    return r


def run_all():
    test_empty()
    test_no_pass()
    test_os_error()
    test_network_error()


def test_empty():
    assert len(filterdevices([])) == 0


def test_no_pass():
    devices = [
        {
            "internal_axon_id": "axon1",
            "tags": [],
            "adapters": [
                {
                    "plugin_name": "ad_adapter",
                    "plugin_unique_name": "ad_adapter_1",
                    "data": {
                        "OS": {
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
                        "OS": {
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
                    "plugin_name": "ad_adapter",
                    "plugin_unique_name": "ad_adapter_2",
                    "data": {
                        "OS": {
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
                        "OS": {
                            "type": "Windows"
                        },
                        "id": "ad1"
                    }
                },
            ]
        }
    ]
    assert len(filterdevices(devices)) == 0


def test_os_error():
    devices = [
        {
            "internal_axon_id": "axon1",
            "tags": [],
            "adapters": [
                {
                    "plugin_name": "ad_adapter",
                    "plugin_unique_name": "ad_adapter_1",
                    "data": {
                        "OS": {
                            "type": "Windows"
                        },
                        "id": "ad1",
                        "network_interfaces": [
                            {
                                "IP": ["1.1.1.1"],
                            }
                        ]
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
                        "OS": {
                            "type": "Windows"
                        },
                        "id": "ad2",
                        "network_interfaces": [
                            {
                                "IP": ["1.1.1.1"],
                            }
                        ]
                    }
                }
            ]
        },
        {
            "internal_axon_id": "axon3",
            "tags": [],
            "adapters": [
                {
                    "plugin_name": "ad_adapter",
                    "plugin_unique_name": "ad_adapter_2",
                    "data": {
                        "OS": {
                            "type": "Windows"
                        },
                        "id": "addd",
                        "network_interfaces": [
                            {
                                "IP": ["1.1.1.1"],
                            }
                        ]
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
                        "OS": {
                            "type": "Windows"
                        },
                        "id": "ad1",
                        "network_interfaces": [
                            {
                                "IP": ["1.1.1.1"],
                            }
                        ]
                    }
                },
            ]
        }
    ]
    assert filterdevices(devices + [{
        "internal_axon_id": "axon5",
        "tags": [],
        "adapters": [
            {
                "plugin_name": "ad_adapter",
                "plugin_unique_name": "ad_adapter_2",
                "data": {
                    "id": "ad1",
                    "network_interfaces": [
                        {
                            "IP": ["1.1.1.1"],
                        }
                    ]
                }
            },
        ]},
        {
            "internal_axon_id": "axon6",
            "tags": [],
            "adapters": [
                {
                    "plugin_name": "ad_adapter",
                    "plugin_unique_name": "ad_adapter_2",
                    "data": {
                        "OS": {
                            "type": "Windows"
                        },
                        "id": "ad1",
                        "network_interfaces": [
                            {
                                "IP": ["1.1.1.1"],
                            }
                        ]
                    }
                },
                {
                    "plugin_name": "ad_adapter",
                    "plugin_unique_name": "ad_adapter_2",
                    "data": {
                        "OS": {
                            "type": "NotWindows"
                        },
                        "id": "ad1",
                        "network_interfaces": [
                            {
                                "IP": ["1.1.1.1"],
                            }
                        ]
                    }
                }
            ]
    }
    ]) == devices


def test_network_error():
    devices = [
        {
            "internal_axon_id": "axon1",
            "tags": [],
            "adapters": [
                {
                    "plugin_name": "ad_adapter",
                    "plugin_unique_name": "ad_adapter_1",
                    "data": {
                        "OS": {
                            "type": "Windows"
                        },
                        "id": "ad1",
                        "network_interfaces": [
                            {
                                "IP": ["1.1.1.1"],
                            }
                        ]
                    }
                },
            ]
        },
    ]
    assert filterdevices(devices + [{
        "internal_axon_id": "axon5",
        "tags": [],
        "adapters": [
            {
                "plugin_name": "ad_adapter",
                "plugin_unique_name": "ad_adapter_2",
                "data": {
                    "id": "ad1",
                    "network_interfaces": [
                        {
                            "IP": ["1.1.1.2"],
                        }
                    ]
                }
            },
        ]},
    ]) == []
