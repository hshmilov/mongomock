import logging

from axonius.types.enforcement_classes import EntitiesResult
from reports.action_types.action_type_base import ActionTypeBase, add_node_selection, add_node_default
from reports.action_types.base.carbonblack_defense_utils import do_cb_defense_action

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
                    'title': 'Policy name',
                    'type': 'string'
                },
            ],
            'required': [
                'policy_name'
            ],
            'type': 'array'
        }
        return add_node_selection(schema)

    @staticmethod
    def default_config() -> dict:
        return add_node_default({
            'policy_name': None
        })

    def _run(self) -> EntitiesResult:
        adapter_unique_name = self._plugin_base._get_adapter_unique_name(
            ADAPTER_NAME, self.action_node_id)
        current_result = self._get_entities_from_view({
            'internal_axon_id': 1,
            'adapters.client_used': 1,
            'adapters.data.basic_device_id': 1,
            'adapters.plugin_name': 1
        })
        return do_cb_defense_action(current_result=current_result,
                                    adapter_unique_name=adapter_unique_name,
                                    extra_data={'policy_name': self._config['policy_name']},
                                    action_name='change_policy')
