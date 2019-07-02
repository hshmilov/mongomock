import logging

from axonius.types.enforcement_classes import EntitiesResult
from axonius.types.enforcement_classes import EntityResult
from axonius.plugin_base import PluginBase
from reports.action_types.action_type_base import ActionTypeBase, add_node_selection, add_node_default

logger = logging.getLogger(f'axonius.{__name__}')

ADAPTER_NAME = 'sentinelone_adapter'

# pylint: disable=W0212


class SentineloneInitiateScanAction(ActionTypeBase):
    """
    SentinelOne InititeScan
    """

    @staticmethod
    def config_schema() -> dict:
        return add_node_selection({}, ADAPTER_NAME)

    @staticmethod
    def default_config() -> dict:
        return add_node_default({
        }, ADAPTER_NAME)

    def _run(self) -> EntitiesResult:
        adapter_unique_name = self._plugin_base._get_adapter_unique_name(ADAPTER_NAME, self.action_node_id)
        current_result = self._get_entities_from_view({
            'internal_axon_id': 1,
            'adapters.client_used': 1,
            'adapters.data.basic_device_id': 1,
            'adapters.plugin_name': 1
        })
        results = []
        for entry in current_result:
            try:
                for adapter_data in entry['adapters']:
                    if adapter_data['plugin_name'] == ADAPTER_NAME \
                            and adapter_data['data'].get('basic_device_id'):
                        device_id = adapter_data['data']['basic_device_id']
                        client_id = adapter_data['client_used']
                        sentinelone_dict = dict()
                        sentinelone_dict['device_id'] = device_id
                        sentinelone_dict['client_id'] = client_id
                        response = PluginBase.Instance.request_remote_plugin('initiate_scan',
                                                                             adapter_unique_name,
                                                                             'post', json=sentinelone_dict)
                        if response.status_code == 200:
                            res = EntityResult(entry['internal_axon_id'], True, 'Success')
                        elif response.status_code == 500:
                            res = EntityResult(entry['internal_axon_id'], False, response.content)
                        else:
                            res = EntityResult(entry['internal_axon_id'], False, 'Unexpected Error')

                        results.append(res)
            except Exception:
                logger.exception(f'Failed with entry {entry}')
        return results
