import logging

from axonius.types.enforcement_classes import EntitiesResult
from axonius.types.enforcement_classes import EntityResult
from axonius.plugin_base import PluginBase
from reports.action_types.action_type_base import ActionTypeBase

logger = logging.getLogger(f'axonius.{__name__}')

# pylint: disable=W0212


class CarbonblackDefenseChangePolicyAction(ActionTypeBase):
    """
    CB Defense Change Policy
    """

    @staticmethod
    def config_schema() -> dict:
        return {
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

    @staticmethod
    def default_config() -> dict:
        return {
            'policy_name': None
        }

    def _run(self) -> EntitiesResult:
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
                    if adapter_data['plugin_name'] == 'carbonblack_defense_adapter':
                        device_id = adapter_data['data']['basic_device_id']
                        client_id = adapter_data['client_used']
                        cb_defense_dict = dict()
                        cb_defense_dict['device_id'] = device_id
                        cb_defense_dict['client_id'] = client_id
                        cb_defense_dict['policy_name'] = self._config['policy_name']
                        response = PluginBase.Instance.request_remote_plugin('change_policy',
                                                                             'carbonblack_defense_adapter',
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
