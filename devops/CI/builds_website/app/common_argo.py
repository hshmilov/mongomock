"""
Common functions for argo tunnel interaction
"""
import requests
import traceback

ARGO_ENDPOINT = 'http://argo.axonius.lan/api'


def create_tunnel(instance_id, private_ip, argo_tunnel):
    """
    Stop the tunnel
    :param instance_id: The name of the instance
    :param private_ip: The private IP of the instance
    :param argo_tunnel: The argo tunnel URL
    """
    try:
        data = {'action': 'create', 'name': instance_id, 'ip': private_ip, 'url': argo_tunnel}
        print(f'Creating argo tunnel for  {instance_id}, with the following tunnel {argo_tunnel}')
        res = requests.post(url=ARGO_ENDPOINT, data=data, verify=False)
        print(f'Created argo tunnel for {instance_id} with the following message {res.text}')
    except Exception:
        traceback.print_exc()
        print(f'Failed sending {data} to {ARGO_ENDPOINT}')


def delete_tunnel(instance_id):
    """
    Stop the tunnel
    :param instance_id: The name of the instance
    """
    try:
        data = {'action': 'delete', 'name': instance_id}
        print(f'Deleting argo tunnel for  {instance_id}')
        res = requests.post(url=ARGO_ENDPOINT, data=data)
        print(f'Deleted argo tunnel for {instance_id} with the following message {res.text}')
    except Exception:
        traceback.print_exc()
        print(f'Failed sending {data} to {ARGO_ENDPOINT}')
