import logging

from axonius.types.enforcement_classes import EntityResult
from axonius.plugin_base import PluginBase

logger = logging.getLogger(f'axonius.{__name__}')

ADAPTER_NAME = 'cybereason_adapter'

# pylint: disable=W0212


def cybereason_action(action_name, current_result, node_id):
    adapter_unique_name = PluginBase.Instance._get_adapter_unique_name(ADAPTER_NAME, node_id)
    results = []
    for entry in current_result:
        try:
            for adapter_data in entry['adapters']:
                if adapter_data['plugin_name'] == ADAPTER_NAME:
                    pylum_id = adapter_data['data']['pylum_id']
                    client_id = adapter_data['client_used']
                    cybereason_response_dict = dict()
                    cybereason_response_dict['pylum_id'] = pylum_id
                    cybereason_response_dict['client_id'] = client_id
                    response = PluginBase.Instance.request_remote_plugin(action_name, adapter_unique_name,
                                                                         'post', json=cybereason_response_dict)
                    if response.status_code == 200:
                        res = EntityResult(entry['internal_axon_id'], True, 'Success')
                    elif response.status_code == 500:
                        res = EntityResult(entry['internal_axon_id'], False, response.data.message)
                    else:
                        res = EntityResult(entry['internal_axon_id'], False, 'Unexpected Error')

                    results.append(res)
        except Exception:
            logger.exception(f'Failed isolating entry {entry}')
            results.append(EntityResult(entry['internal_axon_id'], False, 'Unexpected Error'))
    return results
