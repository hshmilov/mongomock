import logging

from axonius.types.enforcement_classes import EntitiesResult
from axonius.consts.plugin_consts import GUI_PLUGIN_NAME
from reports.action_types.action_type_base import ActionTypeBase, generic_success, EntityResult

logger = logging.getLogger(f'axonius.{__name__}')


class AddCustomDataAction(ActionTypeBase):
    """
    Add a field and a value (either predefined or custom) to all entities
    """

    @staticmethod
    def config_schema() -> dict:
        return {
            'items': [
                {
                    'name': 'field_name',
                    'title': 'Field name',
                    'type': 'string'
                },
                {
                    'name': 'field_value',
                    'title': 'Field value',
                    'type': 'string'
                }
            ],
            'required': [
                'field_name', 'field_value'
            ],
            'type': 'array'
        }

    @staticmethod
    def default_config() -> dict:
        return {
            'field_name': '',
            'field_value': ''
        }

    def _run(self) -> EntitiesResult:
        if not self._internal_axon_ids:
            return []

        custom_data = {
            'data': {
                self._config['field_name']: self._config['field_value'],
                'id': 'unique'
            },
            'selection': {
                'ids': self._internal_axon_ids,
                'include': True
            }
        }
        response = self._plugin_base.request_remote_plugin(f'enforcements/{self._entity_type.value}/custom',
                                                           GUI_PLUGIN_NAME,
                                                           method='post',
                                                           json=custom_data)
        if response.status_code == 200:
            return generic_success(self._internal_axon_ids)

        error = response.json().get('message', {}).get(self._config['field_name'], '')
        return [EntityResult(x, False, error) for x in self._internal_axon_ids]
