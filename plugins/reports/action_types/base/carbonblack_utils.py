from reports.enforcement_classes import EntityResult
from axonius.plugin_base import PluginBase


def carbonblack_action(action_name, current_result):

    results = {}
    for entry in current_result:
        for adapter_data in entry['adapters']:
            if adapter_data['plugin_name'] == 'carbonblack_response_adapter':
                device_id = adapter_data['data']['id']
                client_id = adapter_data['client_used']
                cb_response_dict = dict()
                cb_response_dict['device_id'] = device_id
                cb_response_dict['client_id'] = client_id
                response = PluginBase.Instance.request_remote_plugin(action_name, 'carbonblack_response_adapter',
                                                                     'post', json=cb_response_dict)
                if response.status_code == 200:
                    results[entry['internal_axon_id']] = EntityResult(True, 'Success')
                elif response.status_code == 500:
                    results[entry['internal_axon_id']] = EntityResult(False, response.data.message)
                else:
                    results[entry['internal_axon_id']] = EntityResult(False, 'Unexpected Error')
    return results
