import logging

from axonius.types.enforcement_classes import EntityResult
from axonius.plugin_base import PluginBase
from axonius.types.enforcement_classes import EntitiesResult
from reports.action_types.action_type_base import ActionTypeBase, add_node_selection, add_node_default, generic_fail

logger = logging.getLogger(f'axonius.{__name__}')


ADAPTER_NAME = 'epo_adapter'
APPLY_LIST = ['Add tag', 'Remove tag']


class EpoTagAction(ActionTypeBase):
    """
    Tag an EPO response device
    """

    @staticmethod
    def config_schema() -> dict:
        schema = {
            'items': [
                {
                    'name': 'tag_name',
                    'title': 'Tag name',
                    'type': 'string'
                },
                {
                    'name': 'apply',
                    'title': 'Add or remove tag',
                    'type': 'string',
                    'enum': APPLY_LIST
                }
            ],
            'required': [
                'tag_name',
                'apply'
            ],
            'type': 'array'
        }
        return add_node_selection(schema)

    @staticmethod
    def default_config() -> dict:
        return add_node_default({
            'tag_name': None,
            'apply': 'Add tag'
        })

    # pylint: disable=protected-access
    def _run(self) -> EntitiesResult:
        """
        Performs an EPO action
        :param action: The action to perform (isolate, unisolate, tag_sensor)
        :param entity_type: The entity type
        :param internal_axon_ids: list of axonius devices to isolate
        :return:
        """
        if self._config['apply'] not in APPLY_LIST:
            return generic_fail(self._internal_axon_ids, reason=f'Bad tag action')
        apply = self._config['apply'] == 'Add tag'
        response_dict = {'tag_name': self._config['tag_name'], 'apply': apply}
        machine_names = {}
        action_name = 'tag_devices'
        adapter_unique_name = PluginBase.Instance._get_adapter_unique_name(ADAPTER_NAME, self.action_node_id)
        current_result = self._get_entities_from_view({
            'adapters.data.name': 1,
            'internal_axon_id': 1,
            'adapters.client_used': 1,
            'adapters.plugin_name': 1,
        })
        results = []
        for entry in current_result:
            try:
                for adapter_data in entry['adapters']:
                    if adapter_data['plugin_name'] == ADAPTER_NAME:
                        name = adapter_data['data'].get('name')
                        client_id = adapter_data['client_used']
                        if client_id not in machine_names:
                            machine_names[client_id] = []
                        machine_names[client_id].append(name)
                results.append(EntityResult(entry['internal_axon_id'], True, 'success'))
            except Exception:
                logger.exception(f'Failed adding nic entry {entry}')
                results.append(EntityResult(entry['internal_axon_id'], False, 'Unexpected Error'))

        response_dict['machine_names'] = machine_names
        response = self._plugin_base.request_remote_plugin(action_name, adapter_unique_name,
                                                           'post', json=response_dict)
        if response.status_code == 200:
            return results
        if response.status_code == 500:
            return generic_fail(self._internal_axon_ids, reason=response.data.message)
        return generic_fail(self._internal_axon_ids)
