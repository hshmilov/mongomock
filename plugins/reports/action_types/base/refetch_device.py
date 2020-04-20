# pylint: disable=protected-access
import logging

from axonius.plugin_base import PluginBase
from axonius.types.enforcement_classes import EntitiesResult, EntityResult
from reports.action_types.action_type_base import ActionTypeBase, add_node_selection, add_node_default


logger = logging.getLogger(f'axonius.{__name__}')


ADAPTERS_NAMES = {'Qualys Cloud Platform': {'name': 'qualys_scans_adapter', 'id_field': 'qualys_id'},
                  'Microsoft System Center Configuration Manager (SCCM)': {'name': 'sccm_adapter',
                                                                           'id_field': 'resource_id'},
                  'McAfee ePolicy Orchestrator (ePO)': {'name': 'epo_adapter', 'id_field': 'name'}
                  }


def do_refetch(current_result, adapter_unique_name, id_field):
    results = []
    for entry in current_result:
        try:
            for adapter_data in entry['adapters']:
                if adapter_data['plugin_unique_name'] == adapter_unique_name:
                    device_id = adapter_data['data'][id_field]
                    client_id = adapter_data['client_used']
                    action_dict = dict()
                    action_dict['device_id'] = device_id
                    action_dict['client_id'] = client_id
                    try:
                        message = PluginBase.Instance._trigger_remote_plugin(
                            adapter_unique_name,
                            job_name='refetch_device',
                            priority=True,
                            blocking=True,
                            data=action_dict
                        ).text
                        res = EntityResult(entry['internal_axon_id'], not message, message or 'Success')
                    except Exception as e:
                        res = EntityResult(entry['internal_axon_id'], False, str(e))
                    results.append(res)
        except Exception:
            logger.exception(f'Failed with entry {entry}')
    return results


class RefetchAction(ActionTypeBase):

    @staticmethod
    def config_schema() -> dict:
        schema = {
            'items': [
                {
                    'name': 'adapter_name',
                    'title': 'Adapter Name',
                    'type': 'string',
                    'enum': list(ADAPTERS_NAMES.keys())
                },
            ],
            'required': [
                'adapter_name'
            ],
            'type': 'array'
        }
        return add_node_selection(schema)

    @staticmethod
    def default_config() -> dict:
        return add_node_default({
            'adapter_name': None
        })

    def _run(self) -> EntitiesResult:
        adapter_name = ADAPTERS_NAMES[self._config['adapter_name']]['name']
        id_field = ADAPTERS_NAMES[self._config['adapter_name']]['id_field']
        adapter_unique_name = self._plugin_base._get_adapter_unique_name(adapter_name, self.action_node_id)
        current_result = self._get_entities_from_view({
            'internal_axon_id': 1,
            'adapters.client_used': 1,
            f'adapters.data.{id_field}': 1,
            'adapters.plugin_unique_name': 1
        })
        return do_refetch(current_result=current_result,
                          adapter_unique_name=adapter_unique_name,
                          id_field=id_field)
