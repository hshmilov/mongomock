import logging

from axonius.types.enforcement_classes import EntityResult
from axonius.plugin_base import PluginBase


logger = logging.getLogger(f'axonius.{__name__}')

ADAPTER_NAME = 'carbonblack_defense_adapter'


def do_cb_defense_action(current_result, adapter_unique_name, extra_data, action_name):
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
                    cb_defense_dict['extra_data'] = extra_data
                    cb_defense_dict['action_name'] = action_name
                    response = PluginBase.Instance.request_remote_plugin('do_action',
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
