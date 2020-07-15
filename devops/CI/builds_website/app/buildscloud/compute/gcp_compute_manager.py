import ipaddress
import contextlib
import traceback
import string
import time
from typing import Dict, List
import requests
import dateutil
import libcloud
import libcloud.compute.drivers.gce
from libcloud.compute.base import Node

from buildscloud.builds_cloud_consts import GCP_DFEAULT_ZONE, GCP_DEFAULT_REGION, CLOUD_KEYS
from haikunator import Haikunator


APPROVED_NODE_CHARACTERS = string.ascii_lowercase + string.digits + '-'


class GCPComputeManager:
    def __init__(self, credentials: dict):
        super().__init__()
        self.__client = libcloud.get_driver(libcloud.DriverType.COMPUTE, libcloud.DriverType.COMPUTE.GCE)(
            credentials['client_email'],
            credentials['private_key'],
            project=credentials['project_id']
        )
        self.subnet_name_to_cidr = dict()

        self.refresh_cache()

    def refresh_cache(self):
        for subnetwork in self.client.ex_list_subnetworks():
            self.subnet_name_to_cidr[subnetwork.name] = subnetwork.cidr

    @property
    def client(self) -> libcloud.compute.drivers.gce.GCENodeDriver:
        return self.__client

    def turn_raw_to_generic(self, node):
        result = {
            'cloud': 'gcp',
            'id': node.extra['name'],
            'image': node.extra['image'],
            'image_id': node.extra['image'],
            'name': node.extra['name'],
            'type': node.extra['machineType'].split('/')[-1],
            'private_ip': node.private_ips[0],
            'state': node.state,
            'tags': node.extra['labels'],
            'launch_date': dateutil.parser.parse(node.extra['creationTimestamp'])
        }

        if node.public_ips:
            result['public_ip'] = node.public_ips[0]

        all_ips = node.private_ips + node.public_ips
        for ip in all_ips:
            for subnetwork_name, subnetwork_cidr in self.subnet_name_to_cidr.items():
                try:
                    if ipaddress.ip_address(ip) in ipaddress.ip_network(subnetwork_cidr):
                        result['subnet'] = subnetwork_name
                        break
                except Exception:
                    # In 'pending' state sometimes the ips are invalid.
                    pass

        return result

    def create_node(
            self,
            name: str,
            num: int,
            instance_type: str,
            image: str,
            key: str,
            network_id: str,
            subnetwork_id: str,
            hard_disk_size_in_gb: int,
            labels: Dict[str, str],
            is_public: bool,
            code: str,
            tunnel: str = '',
            base_instance: str = ''
    ):
        assert not (base_instance and image), 'One should choose from base_instance and image'
        assert not (is_public and num != 1), 'Does not support multiple public instances'

        name = ''.join(c if c in APPROVED_NODE_CHARACTERS else '-' for c in name.lower()) + \
               '-' + str(round(time.time()))
        name = name[:55]
        external_ip = None
        tags = None
        if is_public:
            external_ip = self.client.ex_create_address(f'{name}-000-public-ip', region=GCP_DEFAULT_REGION)
            tags = ['builds-public-machine']

        final_labels = {
            'builds-vm': 'true',
        }
        final_labels.update(labels)

        ex_metadata = {'items': []}
        if key:
            ex_metadata['items'].append({'value': f'ubuntu:{CLOUD_KEYS[key]}', 'key': 'sshKeys'})
        if code:
            ex_metadata['items'].append({'value': code, 'key': 'startup-script'})

        if not ex_metadata['items']:
            ex_metadata = None

        with contextlib.ExitStack() as stack:
            if base_instance:
                node = self.client.ex_get_node(base_instance)
                self.client.ex_stop_node(node)
                storage_volume = self.client.ex_get_volume(base_instance)
                image_gce_object = self.client.ex_create_image(base_instance + 'ts', storage_volume)
                self.client.ex_start_node(node)

                def destroy_no_exceptions(*_):
                    try:
                        self.client.ex_delete_image(image_gce_object)
                    except Exception:
                        print('Failed removing image')
                        traceback.print_exc()
                stack.push(destroy_no_exceptions)

            else:
                image_gce_object = self.client.ex_get_image(image)

            image_full_url = image_gce_object.extra['selfLink']
            image_full_url = image_full_url[len('https://www.googleapis.com/compute/v1/'):]

            ex_disks_gce_struct = [
                {
                    'boot': True,
                    'autoDelete': True,
                    'initializeParams': {
                        'sourceImage': image_full_url,
                        'diskType': f'/zones/{GCP_DFEAULT_ZONE}/diskTypes/pd-ssd',
                    }
                }
            ]

            if hard_disk_size_in_gb:
                ex_disks_gce_struct[0]['initializeParams']['diskSizeGb'] = hard_disk_size_in_gb

            raw = self.client.ex_create_multiple_nodes(
                name,
                instance_type,
                '',
                num,
                location=GCP_DFEAULT_ZONE,
                ex_tags=tags,
                ex_network=network_id,
                ex_subnetwork=subnetwork_id,
                external_ip=external_ip,
                ex_metadata=ex_metadata,
                ex_service_accounts=[{'email': 'default', 'scopes': []}],
                description=f'Created by builds.in.axonius.com',
                ex_on_host_maintenance='MIGRATE',
                ex_automatic_restart=True,
                ex_labels=final_labels,
                ex_disks_gce_struct=ex_disks_gce_struct
            )

            try:
                if tunnel:
                    instance_id = raw[0].name
                    private_ip = raw[0].private_ips[0]
                    ENDPOINT = "http://argo.axonius.lan/api"
                    argo_tunnel = 'https://' + tunnel + '.builds.in.axonius.com'
                    data = {'action': 'create', 'name': instance_id, 'ip': private_ip, 'url': argo_tunnel}
                    try:
                        requests.post(url=ENDPOINT, data=data)
                    except Exception:
                        traceback.print_exc()
                        print(f"Failed sending {data} to {ENDPOINT}")

            except Exception as e:
                print(raw, e)

            for instance in raw:
                if not isinstance(instance, Node):
                    raise ValueError(f'Failed creating: {str(instance)}')

            generic = [{
                'id': raw_item.name,
                'name': raw_item.name,
                'private_ip': raw_item.private_ips[0]
            } for raw_item in raw]
            return generic, raw

    def get_nodes(self, node_id: str, vm_type: str):
        if node_id:
            yield self.turn_raw_to_generic(self.client.ex_get_node(node_id, zone='all'))
            return

        for node in self.client.list_nodes(ex_zone='all', ex_use_disk_cache=True):
            vm_labels = node.extra.get('labels') or {}
            if vm_type and vm_labels.get('vm-type') == vm_type:
                yield self.turn_raw_to_generic(node)

            elif not vm_type and 'vm-type' in vm_labels:
                yield self.turn_raw_to_generic(node)

    def start_node(self, node_id: str):
        label_exist = False
        node = self.client.ex_get_node(node_id, zone='all')
        self.client.ex_start_node(node)
        labels = node.extra.get('labels')
        for label in labels:
            if label[0] == 'argo_tunnel':
                label_exist = True
                break
        if not label_exist:
            haikunator = Haikunator()
            argo_token = haikunator.haikunate(token_length=5, token_hex=True)
            labels.update({'argo_tunnel': argo_token})
            self.client.ex_set_node_labels(node, labels=labels)
            private_ip = node.private_ips[0]
            ENDPOINT = "http://argo.axonius.lan/api"
            argo_tunnel = 'https://' + argo_token + '.builds.in.axonius.com'
            data = {'action': 'create', 'name': node.name, 'ip': private_ip, 'url': argo_tunnel}
            try:
                requests.post(url=ENDPOINT, data=data)
            except Exception:
                traceback.print_exc()
                print(f"Failed sending {data} to {ENDPOINT}")

    def stop_node(self, node_id: str):
        node = self.client.ex_get_node(node_id, zone='all')
        self.client.ex_stop_node(node)

    def terminate_node(self, node_id: str):
        node = self.client.ex_get_node(node_id, zone='all')
        public_ip_name = None
        if node.public_ips:
            public_ip_name = f'{node.name}-public-ip'

        self.client.destroy_node(node)
        if public_ip_name:
            self.client.ex_destroy_address(public_ip_name)

    def terminate_many_nodes(self, nodes_ids: List[str]):
        # Note: This does not handle public ips!
        nodes = []
        failed_nodes = []
        for node_id in nodes_ids:
            try:
                nodes.append(self.client.ex_get_node(node_id, zone='all'))
            except Exception:
                failed_nodes.append(node_id)

        results = self.client.ex_destroy_multiple_nodes(nodes)
        assert all(results), f'Not all nodes are terminated: {results}'
        assert not failed_nodes, f'There are some nodes we could not get: {str(failed_nodes)}'
