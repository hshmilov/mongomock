from axonius.consts.plugin_consts import PLUGIN_UNIQUE_NAME
from axonius.correlator_base import CorrelatorBase
from axonius.devices.device_adapter import NETWORK_INTERFACES_FIELD, OS_FIELD
from axonius.entities import EntityType
from axonius.utils.files import get_local_config_file

from static_correlator.engine import StaticCorrelatorEngine


class StaticCorrelatorService(CorrelatorBase):
    def __init__(self, *args, **kwargs):
        super().__init__(get_local_config_file(__file__), *args, **kwargs)

        self._correlation_engine = StaticCorrelatorEngine()
        self._activate('execute')

    def get_entities_from_ids(self, entities_ids=None):
        if entities_ids is None:
            match = {}
        else:
            match = {
                'internal_axon_id': {
                    "$in": entities_ids
                }
            }

        # return devices in the form requested by the StaticCorrelatorEngine, as follows:
        # {
        #     plugin_name: "",
        #     plugin_unique_name: "",
        #     data: {
        #         id: "",
        #         OS: {
        #             type: "",
        #             whatever...
        #         },
        #         hostname: "",
        #         network_interfaces: [
        #             {
        #                 IP: ["127.0.0.1", ...],
        #                 whatever...
        #             },
        #             ...
        #         ]
        #     }
        # }
        return list(self.devices_db.aggregate([
            {"$match": match},
            {'$project': {
                'adapters': {
                    '$map': {
                        'input': '$adapters',
                        'as': 'adapter',
                        'in': {
                            'plugin_name': '$$adapter.plugin_name',
                            PLUGIN_UNIQUE_NAME: '$$adapter.plugin_unique_name',
                            'data': {
                                'id': '$$adapter.data.id',
                                OS_FIELD: '$$adapter.data.os',
                                'hostname': '$$adapter.data.hostname',
                                NETWORK_INTERFACES_FIELD: '$$adapter.data.network_interfaces',
                                'device_serial': '$$adapter.data.device_serial',
                                'last_seen': '$$adapter.data.last_seen',
                                'bios_serial': '$$adapter.data.bios_serial',
                                'domain': '$$adapter.data.domain'
                            }
                        }
                    }
                },
                'tags': 1
            }}
        ]))

    def _correlate(self, devices: list):
        return self._correlation_engine.correlate(devices)

    @property
    def _entity_to_correlate(self) -> EntityType:
        return EntityType.Devices
