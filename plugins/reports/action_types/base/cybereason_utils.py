from axonius.types.enforcement_classes import EntityResult
from axonius.plugin_base import PluginBase


def cybereason_action(action_name, current_result, malop_id):

    results = []
    for entry in current_result:
        for adapter_data in entry['adapters']:
            if adapter_data['plugin_name'] == 'cybereason_adapter':
                pylum_id = adapter_data['data']['pylum_id']
                client_id = adapter_data['client_used']
                cybereason_response_dict = dict()
                cybereason_response_dict['pylum_id'] = pylum_id
                cybereason_response_dict['malop_id'] = malop_id
                cybereason_response_dict['client_id'] = client_id
                response = PluginBase.Instance.request_remote_plugin(action_name, 'cybereason_adapter',
                                                                     'post', json=cybereason_response_dict)
                if response.status_code == 200:
                    res = EntityResult(entry['internal_axon_id'], True, 'Success')
                elif response.status_code == 500:
                    res = EntityResult(entry['internal_axon_id'], False, response.data.message)
                else:
                    res = EntityResult(entry['internal_axon_id'], False, 'Unexpected Error')

                results.append(res)
    return results
