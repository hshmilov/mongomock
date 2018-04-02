"""
This is a default test we do just to check that our testing system works.
The following will be run by pytest.
"""

# we're actually testing ExecutionCorrelatorEngineBase here

from careful_execution_correlator.engine import CarefulExecutionCorrelatorEngine


def filterdevices(devices_db, executor=None, cmds=None, parse_results=None):
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

    correlator = CarefulExecutionCorrelatorEngine(_executor, cmds or default_get_remote_plugin_correlation_cmds,
                                                  parse_results or default_parse_correlation_results)

    r = list(correlator._prefilter_device(devices_db))
    print(f"len = {len(r)};\n{r}")
    return r


def run_all():
    test_empty()
    test_no_pass()
    test_no_pass_different_plugin()
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
                    "plugin_name": "active_directory_adapter",
                    "plugin_unique_name": "active_directory_adapter_1",
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
                    "plugin_name": "active_directory_adapter",
                    "plugin_unique_name": "active_directory_adapter_2",
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
                    "plugin_name": "active_directory_adapter",
                    "plugin_unique_name": "active_directory_adapter_2",
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
                    "plugin_name": "active_directory_adapter",
                    "plugin_unique_name": "active_directory_adapter_2",
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
    assert len(filterdevices(devices)) == 0


def test_no_pass_different_plugin():
    devices = [
        {
            "internal_axon_id": "axon1",
            "tags": [],
            "adapters": [
                {
                    "plugin_name": "active_directory_adapter",
                    "plugin_unique_name": "active_directory_adapter_1",
                    "data": {
                        "os": {
                            "type": "Windows"
                        },
                        "network_interfaces": [
                            {
                                "mac": "06:01:01:01:01:01",
                                "ips": ["123.123.123.123"],
                                "ips_raw": [123123]
                            }
                        ],
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
                    "plugin_name": "blat_adapter",
                    "plugin_unique_name": "blat_adapter_2",
                    "data": {
                        "os": {
                            "type": "Windows"
                        },
                        "network_interfaces": [
                            {
                                "mac": "06:01:01:01:01:01",
                                "ips": ["123.123.123.123"],
                                "ips_raw": [123123]
                            }
                        ],
                        "id": "blat_adapter2"
                    }
                }
            ]
        }
    ]
    assert len(filterdevices(devices)) == 0


def test_network_error():
    devices = [
        {
            "internal_axon_id": "axon1",
            "tags": [],
            "adapters": [
                {
                    "plugin_name": "active_directory_adapter",
                    "plugin_unique_name": "active_directory_adapter_1",
                    "data": {
                        "os": {
                            "type": "Windows"
                        },
                        "id": "ad1",
                        "network_interfaces": [
                            {
                                "ips": ["1.1.1.1"],
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
                "plugin_name": "active_directory_adapter",
                "plugin_unique_name": "active_directory_adapter_2",
                "data": {
                    "id": "ad1",
                    "network_interfaces": [
                        {
                            "ips": ["1.1.1.2"],
                        }
                    ]
                }
            },
        ]},
    ]) == []
