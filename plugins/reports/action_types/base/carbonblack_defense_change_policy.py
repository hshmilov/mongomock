import logging

from axonius.types.enforcement_classes import EntitiesResult
from axonius.types.enforcement_classes import EntityResult
from axonius.plugin_base import PluginBase
from reports.action_types.action_type_base import ActionTypeBase, add_node_selection, add_node_default

logger = logging.getLogger(f'axonius.{__name__}')

ADAPTER_NAME = 'carbonblack_defense_adapter'

# pylint: disable=W0212


class CarbonblackDefenseChangePolicyAction(ActionTypeBase):
    """
    CB Defense Change Policy
    """

    @staticmethod
    def config_schema() -> dict:
        schema = {
            'items': [
                {
                    'name': 'policy_name',
                    'title': 'Policy Name',
                    'type': 'string'
                },
            ],
            'required': [
                'policy_name'
            ],
            'type': 'array'
        }
        return add_node_selection(schema, ADAPTER_NAME)

    @staticmethod
    def default_config() -> dict:
        return add_node_default({
            'policy_name': None
        }, ADAPTER_NAME)

    def _run(self) -> EntitiesResult:
        adapter_unique_name = self._plugin_base._get_adapter_unique_name(
            ADAPTER_NAME, self.action_node_id)
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
                    if adapter_data['plugin_name'] == ADAPTER_NAME:
                        device_id = adapter_data['data']['basic_device_id']
                        client_id = adapter_data['client_used']
                        cb_defense_dict = dict()
                        cb_defense_dict['device_id'] = device_id
                        cb_defense_dict['client_id'] = client_id
                        cb_defense_dict['policy_name'] = self._config['policy_name']
                        response = PluginBase.Instance.request_remote_plugin('change_policy',
                                                                             adapter_unique_name,
                                                                             'post', json=cb_defense_dict)
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
