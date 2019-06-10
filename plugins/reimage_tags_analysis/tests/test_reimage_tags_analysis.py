from datetime import datetime, timedelta
from typing import Iterable, Tuple, List, NamedTuple

from axonius.consts.plugin_consts import PLUGIN_UNIQUE_NAME
from axonius.entities import EntityType
from reimage_tags_analysis.service import ReimageTagsAnalysisService


class ResultsType(NamedTuple):
    entity: EntityType
    identity_by_adapter: List[Tuple[str, str]]  # plugin_unique_name, id
    label: str
    is_enabled: bool
    addition_data: dict


# pylint: disable=W0231
class PluginMock(ReimageTagsAnalysisService):
    def __init__(self, devices_to_return: Iterable[dict]):
        # not calling super!
        self.devices_to_return = devices_to_return
        self.results = []

    def _ReimageTagsAnalysisService__get_devices_from_db(self) -> Iterable[dict]:
        # Overriding private method
        return self.devices_to_return

    def add_label_to_entity(self, entity: EntityType, identity_by_adapter, label, is_enabled=True,
                            additional_data=None):
        self.results.append(ResultsType(entity, identity_by_adapter, label, is_enabled, additional_data))


def perform_test(devices_to_give: Iterable[dict]) -> List[ResultsType]:
    mock = PluginMock(devices_to_give)
    # pylint: disable=W0212
    mock._triggered('execute', None, None)
    return mock.results


def test_sanity():
    assert len(perform_test([])) == 0


MAC_A = 'AA:AA:AA:AA:AA:AA'
UNIQUE_NAME_A = 'UNIQUE_A'
ID_A = 'ID_A'
HOSTNAME_A = 'HOSTNAME_A'

MAC_B = 'BB:BB:BB:BB:BB:BB'
UNIQUE_NAME_B = 'UNIQUE_B'
ID_B = 'ID_B'
HOSTNAME_B = 'HOSTNAME_B'
HOSTNAME_C = 'HOSTNAME_C'

# pylint: disable=C0103
now = datetime.utcnow()
old_threshold = now - timedelta(days=8)
new_threshold = now - timedelta(days=1)


def _create_adapter(plugin_unique_name, id_, mac, hostname, threshold, adapter_properties=None):
    if adapter_properties is None:
        adapter_properties = ['Agent']
    return {
        PLUGIN_UNIQUE_NAME: plugin_unique_name,
        'data': {
            'id': id_,
            'network_interfaces': [
                {
                    'mac': mac
                }
            ],
            'hostname': hostname,
            'last_seen': threshold,
            'adapter_properties': adapter_properties
        }
    }


def test_basic_case():
    # Just one adapter being reimaged
    result = perform_test([
        {
            'adapters': [_create_adapter(UNIQUE_NAME_A, ID_A, MAC_A, HOSTNAME_A, old_threshold)]
        },
        {
            'adapters': [_create_adapter(UNIQUE_NAME_A, ID_B, MAC_A, HOSTNAME_B, new_threshold)]
        }
    ])
    assert len(result) == 1
    result = result[0]
    assert result.entity == EntityType.Devices
    assert result.identity_by_adapter == [(UNIQUE_NAME_A, ID_A)]
    assert result.label == f'Reimaged by {HOSTNAME_B}'
    assert result.is_enabled is True
    assert result.addition_data is None


def test_ignore_non_agent():
    # Make sure it verifies the existence of agent
    result = perform_test([
        {
            'adapters': [_create_adapter(UNIQUE_NAME_A, ID_A, MAC_A, HOSTNAME_A, old_threshold, adapter_properties=[])]
        },
        {
            'adapters': [_create_adapter(UNIQUE_NAME_A, ID_B, MAC_A, HOSTNAME_B, new_threshold)]
        }
    ])
    assert len(result) == 0


def test_verifies_times_old():
    # Make sure it doesn't just accept all old dates
    result = perform_test([
        {
            'adapters': [_create_adapter(UNIQUE_NAME_A, ID_A, MAC_A, HOSTNAME_A, old_threshold)]
        },
        {
            'adapters': [_create_adapter(UNIQUE_NAME_A, ID_B, MAC_A, HOSTNAME_B, old_threshold)]
        }
    ])
    assert len(result) == 0


def test_verifies_times_new():
    # Make sure it doesn't just accept all old dates
    result = perform_test([
        {
            'adapters': [_create_adapter(UNIQUE_NAME_A, ID_A, MAC_A, HOSTNAME_A, new_threshold)]
        },
        {
            'adapters': [_create_adapter(UNIQUE_NAME_A, ID_B, MAC_A, HOSTNAME_B, new_threshold)]
        }
    ])
    assert len(result) == 0


def test_multihostnames():
    # Just one adapter being reimaged
    result = perform_test([
        {
            'adapters': [_create_adapter(UNIQUE_NAME_A, ID_A, MAC_A, HOSTNAME_A, old_threshold)]
        },
        {
            'adapters': [_create_adapter(UNIQUE_NAME_A, ID_B, MAC_A, HOSTNAME_B, new_threshold),
                         _create_adapter(UNIQUE_NAME_A, ID_B, MAC_A, HOSTNAME_C, new_threshold)]
        }
    ])
    assert len(result) == 2

    assert len([
        x
        for x
        in result
        if x.entity == EntityType.Devices and
        x.identity_by_adapter == [(UNIQUE_NAME_A, ID_A)] and
        x.label == f'Reimaged by {HOSTNAME_B}' and
        x.is_enabled is True and
        x.addition_data is None
    ]) == 1

    assert len([
        x
        for x
        in result
        if x.entity == EntityType.Devices and
        x.identity_by_adapter == [(UNIQUE_NAME_A, ID_A)] and
        x.label == f'Reimaged by {HOSTNAME_C}' and
        x.is_enabled is True and
        x.addition_data is None
    ]) == 1
