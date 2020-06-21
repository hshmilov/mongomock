# Should be imported from inside the docker and outside the docker
import json

import requests


def read_saas_input_params():
    # example: {'AXONIUS_SAAS_NODE': 'True',
    # 'WEB_URL': 'cust1-f0a4.on.axonius.com',
    # 'TUNNEL_URL': 'tun_cust1-f0a4.on.axonius.com',
    #  'STACK_NAME': 'stack-cust1-f0a4'}
    result = {}
    try:
        params = requests.get('http://169.254.169.254/2009-04-04/user-data', timeout=5).content.decode()
        for param in params.split():
            if '=' in param:
                splitted = param.split('=')
                result[splitted[0].strip()] = splitted[1].strip()
        # To make regular build in AWS boot properly
        if 'AXONIUS_SAAS_NODE' not in result:
            return False
        return result
    except requests.exceptions.Timeout:
        return False
    except Exception as e:
        print(f'Failed to read saas params')
        return result


def is_axonius_saas_instance():
    return read_saas_input_params().get('AXONIUS_SAAS_NODE') == 'True'


def get_web_url():
    return read_saas_input_params().get('WEB_URL')


def get_tunnel_url():
    return read_saas_input_params().get('TUNNEL_URL')


def get_stack_name():
    return read_saas_input_params().get('STACK_NAME')


def get_params_key_id():
    return read_saas_input_params().get('PARAMS_KEY_ARN').split('/')[1]


if __name__ == '__main__':
    if is_axonius_saas_instance():
        print(json.dumps(read_saas_input_params()))
