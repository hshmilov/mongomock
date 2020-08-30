import logging

from axonius.types.enforcement_classes import EntitiesResult
from axonius.consts.plugin_consts import GUI_PLUGIN_NAME
from reports.action_types.action_type_base import ActionTypeBase, generic_success, EntityResult

logger = logging.getLogger(f'axonius.{__name__}')

FIELD_TYPE_ENUM = [{
    'name': 'field_value',
    'title': 'String'
}, {
    'name': 'field_on',
    'title': 'Boolean'
}]


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
                    'name': 'conditional',
                    'title': 'Field type',
                    'type': 'string',
                    'enum': FIELD_TYPE_ENUM,
                    'default': 'field_value'
                },
                {
                    'name': 'field_value',
                    'title': 'Field value',
                    'type': 'string'
                },
                {
                    'name': 'field_on',
                    'title': 'Field value',
                    'type': 'bool',
                    'enum': [{
                        'name': True,
                        'title': 'Yes'
                    }, {
                        'name': False,
                        'title': 'No'
                    }],
                    'default': True,
                }
            ],
            'required': [
                'field_name', 'conditional', 'field_value', 'field_on'
            ],
            'type': 'array'
        }

    @staticmethod
    def default_config() -> dict:
        return {
            'field_name': '',
            'conditional': 'field_value',
            'field_value': '',
            'field_on': True
        }

    def _run(self) -> EntitiesResult:
        if not self._internal_axon_ids:
            return []

        field_type = self._config.get('conditional', FIELD_TYPE_ENUM[0]['name'])
        field_content = self._config[field_type]
        field_name = self._config['field_name']
        custom_data = {
            'data': {
                field_name: field_content,
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

        error = response.json().get('message', {}).get(field_name, '')
        if 'Wrong type' in error:
            alternate_type = next(filter(lambda x: x['name'] != field_type, FIELD_TYPE_ENUM))['title']
            error = f'Cannot add custom field - \'{field_name}\' already exists as \'{alternate_type}\''
        return [EntityResult(x, False, error) for x in self._internal_axon_ids]
