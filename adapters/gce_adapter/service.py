import ipaddress
import json
import logging
import datetime
from typing import List

from google.oauth2 import service_account
from googleapiclient import discovery
from libcloud.compute.drivers.gce import GCEFirewall
from libcloud.compute.providers import get_driver
from libcloud.compute.types import NodeState, Provider

from axonius.clients.rest.connection import RESTConnection
from axonius.smart_json_class import SmartJsonClass

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.devices.device_adapter import DeviceAdapter, DeviceRunningState
from axonius.fields import Field, ListField, JsonStringFormat
from axonius.utils.files import get_local_config_file
from axonius.utils.json_encoders import IgnoreErrorJSONEncoder
from axonius.utils.datetime import parse_date
from axonius.utils.parsing import format_subnet

logger = logging.getLogger(f'axonius.{__name__}')

GCE_ENDPOINT_FOR_REACHABILITY_TEST = f'https://www.googleapis.com/discovery/v1/apis/compute/v1/rest'

POWER_STATE_MAP = {
    NodeState.STOPPED: DeviceRunningState.TurnedOff,
    NodeState.RUNNING: DeviceRunningState.TurnedOn,
    NodeState.SUSPENDED: DeviceRunningState.Suspended,
    NodeState.STOPPING: DeviceRunningState.ShuttingDown,
    NodeState.ERROR: DeviceRunningState.Error,
    NodeState.MIGRATING: DeviceRunningState.Migrating,
    NodeState.REBOOTING: DeviceRunningState.Rebooting,
    NodeState.STARTING: DeviceRunningState.StartingUp,
}


class GceTag(SmartJsonClass):
    gce_key = Field(str, 'GCE Key')
    gce_value = Field(str, 'GCE Value')


class GceFirewallRule(SmartJsonClass):
    type = Field(str, 'Allowed / Denied', enum=['Allowed', 'Denied'])
    protocol = Field(str, 'Protocol')
    ports = ListField(str, 'Ports')     # Ports can also be a range like 50-60 so it can't be int


class GceFirewall(SmartJsonClass):
    name = Field(str, 'Firewall Name')
    direction = Field(str, 'Direction', enum=['INGRESS', 'EGRESS'])
    priority = Field(int, 'Priority')
    match = ListField(str, 'Matched By')
    source_ranges = ListField(str, 'Source ranges', converter=format_subnet, json_format=JsonStringFormat.subnet)
    source_tags = ListField(str, 'Source tags')
    source_service_accounts = ListField(str, 'Source service accounts')
    destination_ranges = ListField(str, 'Destination ranges',
                                   converter=format_subnet, json_format=JsonStringFormat.subnet)
    target_ranges = ListField(str, 'Target ranges', converter=format_subnet, json_format=JsonStringFormat.subnet)
    target_tags = ListField(str, 'Target tags')
    target_service_accounts = ListField(str, 'Target service accounts')
    rules = ListField(GceFirewallRule, 'Rules')


# pylint: disable=too-many-instance-attributes
class GceAdapter(AdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        project_id = Field(str, 'Project ID')
        image = Field(str, 'Device image')
        size = Field(str, 'Google Device Size')
        creation_time_stamp = Field(datetime.datetime, 'Creation Time Stamp')
        cluster_name = Field(str, 'GCE Cluster Name')
        cluster_uid = Field(str, 'GCE Cluster Unique ID')
        cluster_location = Field(str, 'GCE Cluster Location')
        gce_tags = ListField(GceTag, 'GCE Metadata Tags')
        gce_labels = ListField(GceTag, 'GCE labels')
        gce_network_tags = ListField(str, 'GCE Network Tags')
        service_accounts = ListField(str, 'GCE Service Accounts')
        firewalls = ListField(GceFirewall, 'GCE Firewalls')

    def __init__(self):
        super().__init__(get_local_config_file(__file__))

    def _get_client_id(self, client_config):
        auth_file = json.loads(self._grab_file_contents(client_config['keypair_file']))
        return auth_file['client_id'] + '_' + auth_file['project_id']

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(GCE_ENDPOINT_FOR_REACHABILITY_TEST)

    def _connect_client(self, client_config):
        try:
            auth_file = json.loads(self._grab_file_contents(client_config['keypair_file']))

            # Check access
            credentials = service_account.Credentials.from_service_account_info(
                auth_file,
                scopes=['https://www.googleapis.com/auth/cloudplatformprojects.readonly']
            )
            service = discovery.build('cloudresourcemanager', 'v1', credentials=credentials)
            request = service.projects().list()
            try:
                response = request.execute()
            except Exception as re:
                logger.exception(f'Failure listing projects')
                if 'cloud resource manager api has not been used in project' in str(re).lower():
                    raise ClientConnectionException(f'Cloud Resource Manager API is not enabled.')
                raise
            projects = response.get('projects') or []
            if not projects:
                raise ClientConnectionException(f'No projects found. Please check the service account permissions')
            return auth_file
        except Exception as e:
            client_id = self._get_client_id(client_config)
            logger.error(f'Failed to connect to client {client_id}')
            raise ClientConnectionException(f'Error: {e}')

    @staticmethod
    def __get_firewalls(provider):
        try:
            # Libcloud does not support 'disabled' firewalls so we have to do this ourselves
            response = provider.connection.request('/global/firewalls', method='GET').object
            # Libcloud also does not support destRanges so we have to support that as well.
            firewalls = []
            for f in response.get('items', []):
                if f.get('disabled'):
                    continue
                fw = provider._to_firewall(f)   # pylint: disable=protected-access
                if f.get('destinationRanges'):
                    fw.extra['destinationRanges'] = f.get('destinationRanges')
                firewalls.append(fw)
            return firewalls
        except Exception:
            logger.exception(f'Can not get firewalls')
            return []

    def _query_devices_by_client(self, client_name, client_data):
        auth_json = client_data
        try:
            credentials = service_account.Credentials.\
                from_service_account_info(auth_json,
                                          scopes=['https://www.googleapis.com/auth/cloudplatformprojects.readonly'])
            service = discovery.build('cloudresourcemanager', 'v1', credentials=credentials)
            request = service.projects().list()
            while request is not None:
                response = request.execute()
                for project in response['projects']:
                    try:
                        provider = get_driver(Provider.GCE)(
                            auth_json['client_email'],
                            auth_json['private_key'],
                            project=project.get('projectId')
                        )
                        firewalls = self.__get_firewalls(provider)
                        for device_raw in provider.list_nodes():
                            yield device_raw, project.get('projectId'), firewalls
                    except Exception:
                        logger.exception(f'Problem with project {project}')
                request = service.projects().list_next(previous_request=request, previous_response=response)
        except Exception:
            provider = get_driver(Provider.GCE)(
                auth_json['client_email'],
                auth_json['private_key'],
                project=auth_json['project_id']
            )
            firewalls = self.__get_firewalls(provider)
            for device_raw in provider.list_nodes():
                yield device_raw, auth_json['project_id'], firewalls

    @staticmethod
    def _clients_schema():
        return {
            'items': [
                {
                    'name': 'keypair_file',
                    'title': 'JSON Key pair for the service account',
                    'description': 'The binary contents of the JSON keypair file',
                    'type': 'file',
                },
            ],
            'required': [
                'keypair_file'
            ],
            'type': 'array'
        }

    # pylint: disable=too-many-branches, too-many-statements, too-many-locals, too-many-nested-blocks
    def create_device(self, raw_device_data, project_id, firewalls: List[GCEFirewall]):
        device = self._new_device_adapter()
        device.id = raw_device_data.id
        device.cloud_provider = 'GCP'
        device.cloud_id = device.id
        device.project_id = project_id
        try:
            device.power_state = POWER_STATE_MAP.get(raw_device_data.state,
                                                     DeviceRunningState.Unknown)
        except Exception:
            logger.exception(f'Coudn\'t get power state for {str(raw_device_data)}')
        try:
            device.figure_os(raw_device_data.image)
        except Exception:
            logger.exception(f'Coudn\'t get os for {str(raw_device_data)}')
        try:
            device.name = raw_device_data.name
        except Exception:
            logger.exception(f'Coudn\'t get name for {str(raw_device_data)}')
        try:
            device.add_nic(ips=raw_device_data.private_ips)
        except Exception:
            logger.exception(f'Coudn\'t get ips for {str(raw_device_data)}')
        try:
            public_ips = raw_device_data.public_ips
            if public_ips:
                for ip in public_ips:
                    if ip:
                        device.add_nic(ips=[ip])
                        device.add_public_ip(ip)
        except Exception:
            logger.exception(f'Problem getting public IP for {str(raw_device_data)}')
        try:
            device.image = raw_device_data.image
        except Exception:
            logger.exception(f'Problem getting image for {str(raw_device_data)}')
        try:
            device.size = raw_device_data.size
        except Exception:
            logger.exception(f'Problem getting data size for {str(raw_device_data)}')
        try:
            device.creation_time_stamp = parse_date(raw_device_data.extra.get('creationTimestamp'))
        except Exception:
            logger.exception(f'Problem getting creation time for {str(raw_device_data)}')
        try:
            for item in (raw_device_data.extra.get('metadata').get('items') or []):
                if item.get('key') == 'cluster-name':
                    device.cluster_name = item.get('value')
                elif item.get('key') == 'cluster-uid':
                    device.cluster_uid = item.get('value')
                elif item.get('key') == 'cluster-location':
                    device.cluster_location = item.get('value')
                else:
                    try:
                        gce_key = item.get('key')
                        gce_value = item.get('value')
                        device.gce_tags.append(GceTag(gce_key=gce_key, gce_value=gce_value))
                    except Exception:
                        logger.exception(f'Problem getting extra tags for {raw_device_data}')
        except Exception:
            logger.exception(f'Problem getting cluster info for {str(raw_device_data)}')

        try:
            for key, value in (raw_device_data.extra.get('labels') or {}).items():
                device.gce_labels.append(GceTag(gce_key=key, gce_value=value))
        except Exception:
            logger.exception(f'Problem adding gce labels to instance')

        gce_network_tags = []
        try:
            gce_network_tags = raw_device_data.extra.get('tags') or []
            device.gce_network_tags = gce_network_tags
        except Exception:
            logger.exception(f'Can not get gce network tags for instance')

        device_service_accounts = []
        try:
            device.service_accounts = []
            service_accounts_raw = raw_device_data.extra.get('serviceAccounts')
            if isinstance(service_accounts_raw, list) and service_accounts_raw:
                for service_account_raw in service_accounts_raw:
                    try:
                        if service_account_raw.get('email'):
                            device_service_accounts.append(service_account_raw.get('email'))
                    except Exception:
                        logger.exception(f'Problem with service account {service_account_raw}')

            device.service_accounts = device_service_accounts
        except Exception:
            logger.exception(f'Problem adding Service Accounts')

        # Try to find matching firewalls
        try:
            # Matching can be done by ip, service account, or tag.
            instance_ips = list(raw_device_data.private_ips) + list(raw_device_data.public_ips)
            instance_networks = []
            for network_interface in (raw_device_data.extra.get('networkInterfaces') or []):
                if network_interface.get('network'):
                    instance_networks.append(network_interface.get('network').split('/')[-1])
            device.firewalls = []
            for fw in firewalls:
                # Validate that this instance is in the network the fw is valid for
                if fw.network.name not in instance_networks:
                    continue
                matched_by = []
                # We are searching for a match in all rules.
                # As explain in https://cloud.google.com/vpc/docs/firewalls, in both ingress and egress fw's the target
                # talks about the instances in the network.

                if not fw.target_ranges and not fw.target_tags and not fw.target_service_accounts:
                    matched_by.append(f'All instances in network')
                else:
                    for instance_ip in instance_ips:
                        for subnet in (fw.target_ranges or []):
                            try:
                                if '/' not in subnet:
                                    subnet += '/32'  # its a regular ip, lets add a subnet suffix
                                if ipaddress.ip_address(instance_ip) in ipaddress.ip_network(subnet):
                                    matched_by.append(f'Instance IP {instance_ip}')
                            except Exception:
                                logger.exception(f'Could not match by ingress ip/subnet')

                    for network_tag in gce_network_tags:
                        if network_tag in (fw.target_tags or []):
                            matched_by.append(f'Network tag {network_tag}')

                    for gce_service_account in device_service_accounts:
                        if gce_service_account in (fw.target_service_accounts or []):
                            matched_by.append(f'Service Account {gce_service_account}')

                if matched_by:
                    rules = []
                    for rule in (fw.allowed or []):
                        rules.append(GceFirewallRule(
                            type='Allowed',
                            protocol=rule.get('IPProtocol'),
                            ports=rule.get('ports') or []
                        ))
                    for rule in (fw.denied or []):
                        rules.append(GceFirewallRule(
                            type='Denied',
                            protocol=rule.get('IPProtocol'),
                            ports=rule.get('ports') or []
                        ))

                    source_ranges = [f'{tr}/32' if '/' not in tr else tr for tr in (fw.source_ranges or [])]
                    target_ranges = [f'{tr}/32' if '/' not in tr else tr for tr in (fw.target_ranges or [])]
                    destination_ranges = [f'{tr}/32' if '/' not in tr else tr for tr in
                                          (fw.extra.get('destinationRanges') or [])]
                    device.firewalls.append(GceFirewall(
                        name=fw.name,
                        direction=fw.direction or 'INGRESS',    # if not specified, documentation says its ingress.
                        priority=fw.priority,
                        match=matched_by,
                        source_ranges=source_ranges,
                        source_tags=fw.source_tags or [],
                        source_service_accounts=fw.source_service_accounts or [],
                        destination_ranges=destination_ranges,
                        target_ranges=target_ranges,
                        target_tags=fw.target_tags or [],
                        target_service_accounts=fw.target_service_accounts or [],
                        rules=rules
                    ))

                    # Add to a generic table
                    if fw.direction == 'EGRESS':
                        targets = destination_ranges
                    else:
                        # must be ingress according to gcp docs
                        targets = source_ranges + (fw.source_tags or []) + (fw.source_service_accounts or [])
                        targets = targets if targets else 'ALL'

                    for target in targets:
                        for rule in rules:
                            try:
                                protocol = rule.protocol
                            except Exception:
                                protocol = ''

                            try:
                                ports = rule.ports
                            except Exception:
                                ports = []

                            # No ports. Its important to still have None here
                            # or otherwise we won't have the rule at all
                            ports = ports if ports else [None]

                            for port in ports:
                                try:
                                    from_port, to_port = port.split('-')
                                except Exception:
                                    # Assume this is just a number and not a range
                                    from_port, to_port = port, port

                                try:
                                    if fw.direction.upper() in ['INGRESS', 'EGRESS']:
                                        direction = fw.direction.upper()
                                    else:
                                        direction = None
                                except Exception:
                                    direction = None
                                device.add_firewall_rule(
                                    name=fw.name,
                                    source='GCE Firewall Rule',
                                    type='Allow' if rule.type == 'Allowed' else 'Deny',
                                    direction=direction,
                                    target=target,
                                    protocol=protocol,
                                    from_port=from_port,
                                    to_port=to_port
                                )
        except Exception:
            logger.exception(f'Could not parse matching firewalls for instance')

        try:
            # some fields might not be basic types
            # by using IgnoreErrorJSONEncoder with JSON encode we verify that this
            # will pass a JSON encode later by mongo
            device.set_raw(json.loads(json.dumps(raw_device_data.__dict__, cls=IgnoreErrorJSONEncoder)))
        except Exception:
            logger.exception(f'Can\'t set raw for {str(device.id)}')
        return device

    def _parse_raw_data(self, devices_raw_data):
        for raw_device_data, project_id, firewalls in iter(devices_raw_data):
            try:
                device = self.create_device(raw_device_data, project_id, firewalls)
                yield device
            except Exception:
                logger.exception(f'Got exception for raw_device_data: {raw_device_data}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets, AdapterProperty.Cloud_Provider]
