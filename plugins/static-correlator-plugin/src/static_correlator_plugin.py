"""
CorrelatorPlugin.py: A Plugin for the devices correlation process
"""
from static_correlator_engine import StaticCorrelatorEngine
from axonius.correlator_base import CorrelatorBase
from axonius.consts.plugin_consts import PLUGIN_UNIQUE_NAME
from axonius.consts.adapter_consts import SCANNER_FIELD


class StaticCorrelatorPlugin(CorrelatorBase):
    def __init__(self, *args, **kwargs):
        """
        Check AdapterBase documentation for additional params and exception details.
        """
        super().__init__(*args, **kwargs)

        self._correlation_engine = StaticCorrelatorEngine(logger=self.logger)

    def get_devices_from_ids(self, devices_ids=None):
        """
        Virtual by design.
        Gets devices by their axonius ID.
        :param devices_ids:
        :return:
        """
        with self._get_db_connection(True) as db:
            aggregator_db = db[self.get_plugin_by_name('aggregator', verify_single=True)[PLUGIN_UNIQUE_NAME]]
            if devices_ids is None:
                match = {}
            else:
                match = {
                    'internal_axon_id': {
                        "$in": devices_ids
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
            return list(aggregator_db['devices_db'].aggregate([
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
                                    'OS': '$$adapter.data.OS',
                                    SCANNER_FIELD: f'$$adapter.data.{SCANNER_FIELD}',
                                    'hostname': '$$adapter.data.hostname',
                                    'network_interfaces': '$$adapter.data.network_interfaces'
                                }
                            }
                        }
                    },
                    'tags': 1
                }}
            ]))

    def _correlate(self, devices: list):
        """
        Correlate across the whole DB
        :return:
        """
        return self._correlation_engine.correlate(devices)
