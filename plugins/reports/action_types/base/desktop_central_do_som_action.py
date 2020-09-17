import logging

from axonius.types.enforcement_classes import EntitiesResult, EntityResult
from axonius.plugin_base import PluginBase
from reports.action_types.action_type_base import ActionTypeBase, add_node_selection, add_node_default

logger = logging.getLogger(f'axonius.{__name__}')


ADAPTER_NAME = 'desktop_central_adapter'


SOM_ACTIONS = {'Install Agent': 'installagent', 'Uninstall Agent': 'uninstallagent',
               'Remove Computer': 'removecomputer'}


class DesktopCentralSomAction(ActionTypeBase):
    """
    Do a Desktop Central action
    """

    @staticmethod
    def config_schema() -> dict:
        schema = {
            'items': [
                {
                    'name': 'action_name',
                    'title': 'Action type',
                    'type': 'string',
                    'enum': list(SOM_ACTIONS.keys())
                }
            ],
            'required': [
                'action_name'
            ],
            'type': 'array'
        }
        return add_node_selection(schema)

    @staticmethod
    def default_config() -> dict:
        return add_node_default({
            'action_name': 'Install Agent',
        })

    def _run(self) -> EntitiesResult:
        """
        Performs a DesktopCentral action
        :param action: The action to perform (isolate, unisolate, tag_sensor)
        :param entity_type: The entity type
        :param internal_axon_ids: list of axonius devices to isolate
        :return:
        """
        current_result = self._get_entities_from_view({
            'internal_axon_id': 1,
            'adapters.client_used': 1,
            'adapters.data.resource_id': 1,
            'adapters.plugin_name': 1
        })
        # pylint: disable=protected-access
        adapter_unique_name = PluginBase.Instance._get_adapter_unique_name(ADAPTER_NAME, self.action_node_id)
        results = []
        for entry in current_result:
            try:
                found_desktop_central = False
                for adapter_data in entry['adapters']:
                    if adapter_data['plugin_name'] == ADAPTER_NAME:
                        found_desktop_central = True
                        resource_id = adapter_data['data'].get('resource_id')
                        client_id = adapter_data['client_used']
                        desktop_central_response_dict = dict()
                        desktop_central_response_dict['resource_id'] = resource_id
                        desktop_central_response_dict['action'] = SOM_ACTIONS[self._config('action_name')]
                        desktop_central_response_dict['client_id'] = client_id
                        response = PluginBase.Instance.request_remote_plugin('do_som_action', adapter_unique_name,
                                                                             'post', json=desktop_central_response_dict)
                        if response.status_code == 200:
                            res = EntityResult(entry['internal_axon_id'], True, 'Success')
                        elif response.status_code == 500:
                            res = EntityResult(entry['internal_axon_id'], False, response.text)
                        else:
                            res = EntityResult(entry['internal_axon_id'], False, 'Unexpected Error')

                        results.append(res)
                if not found_desktop_central:
                    res = EntityResult(entry['internal_axon_id'], False, 'Not Desktop Central Adapter')
                    results.append(res)
            except Exception:
                logger.exception(f'Failed isolating entry {entry}')
                results.append(EntityResult(entry['internal_axon_id'], False, 'Unexpected Error'))
        return results
