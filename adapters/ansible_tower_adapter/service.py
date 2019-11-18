import logging
from ipaddress import ip_address

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.utils.datetime import parse_date
from axonius.utils.json import from_json
from axonius.clients.rest.connection import RESTConnection, RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from axonius.fields import Field, ListField, datetime
from axonius.smart_json_class import SmartJsonClass

from ansible_tower_adapter.connection import AnsibleTowerConnection
from ansible_tower_adapter.client_id import get_client_id
from ansible_tower_adapter.consts import ANSIBLE_DATA_VARBS_STATIC_MAP, ANSIBLE_IP_ADDRESS_DATA_VARBS


logger = logging.getLogger(f'axonius.{__name__}')

FILTER_LOCALHOST_ADDR = {'0.0.0.0', '127.0.0.1', 'localhost'}
ANSIBEL_VARBS_PREFIX = 'ansible_'


class AnsibleHostAdminUser(SmartJsonClass):
    id = Field(int, 'id')
    username = Field(str, 'username')
    first_name = Field(str, 'first_name')
    last_name = Field(str, 'last_name')


class AnsibleDataVariables(SmartJsonClass):
    name = Field(str, 'Name')
    content = ListField(str, 'Content')


class AnsiblelHostGroups(SmartJsonClass):
    id = Field(int, 'ID')
    name = Field(str, 'Name')


def _parse_admin_audit(device_raw, operation='created_by'):
    try:
        if operation in device_raw.get('summary_fields') \
                and isinstance(device_raw.get('summary_fields').get('operation'), dict):
            admin = device_raw.get('summary_fields')[operation]
            return AnsibleHostAdminUser(id=admin.get('id'),
                                        username=admin.get('username'),
                                        first_name=admin.get('first_name'),
                                        last_name=admin.get('last_name'))
        return None
    except KeyError:
        return None


class AnsibleTowerAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        """
            Indicates if a host is available and should be included in running jobs.
            For hosts that are part of an external inventory, this flag cannot be changed.
            It is set by the inventory sync process.
        """

        enabled = Field(bool, 'Is Enabled')

        ''' An Inventory is a collection of hosts against which jobs may be launched,
            Inventories are divided into groups and these groups contain the actual hosts.
            Groups may be sourced manually, by entering host names into Tower,
            or from one of Ansible Tower’s supported cloud providers.
        '''
        inventory_id = Field(int, 'Inventory ID')
        inventory_name = Field(str, 'Inventory Name')

        device_type = Field(str, 'Device Type')

        created_at = Field(datetime.datetime, 'Creation Time')
        modified_at = Field(datetime.datetime, 'Modification Time')
        # only exits on internal host
        created_by = Field(AnsibleHostAdminUser, 'Created By')
        modified_by = Field(AnsibleHostAdminUser, 'Modified By')

        ec2_block_devices = ListField(AnsibleDataVariables, 'ec2_block_devices')
        datastore = ListField(AnsibleDataVariables, 'datastore')
        resourcepool = ListField(AnsibleDataVariables, 'resourcepool')
        summary = ListField(AnsibleDataVariables, 'summary')
        capability = ListField(AnsibleDataVariables, 'capability')
        guest = ListField(AnsibleDataVariables, 'guest')
        config = ListField(AnsibleDataVariables, 'config')
        runtime = ListField(AnsibleDataVariables, 'runtime')

        groups = ListField(AnsiblelHostGroups, 'Groups')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'), port=80, ssl=False)

    @staticmethod
    def get_connection(client_config):
        connection = AnsibleTowerConnection(domain=client_config['domain'],
                                            verify_ssl=client_config['verify_ssl'],
                                            https_proxy=client_config.get('https_proxy'),
                                            username=client_config['username'],
                                            password=client_config['password'])
        with connection:
            pass
        return connection

    def _connect_client(self, client_config):
        try:
            return self.get_connection(client_config)
        except RESTException as e:
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                client_config['domain'], str(e))
            logger.exception(message)
            raise ClientConnectionException(message)

    @staticmethod
    def _query_devices_by_client(client_name, client_data):
        """
        Get all devices from a specific  domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        with client_data:
            yield from client_data.get_device_list()

    @staticmethod
    def _clients_schema():
        """
        The schema AnsibleTowerAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Ansible Tower Domain',
                    'type': 'string'
                },
                {
                    'name': 'username',
                    'title': 'User Name',
                    'type': 'string'
                },
                {
                    'name': 'password',
                    'title': 'Password',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': 'verify_ssl',
                    'title': 'Verify SSL',
                    'type': 'bool'
                },
                {
                    'name': 'https_proxy',
                    'title': 'HTTPS Proxy',
                    'type': 'string'
                }
            ],
            'required': [
                'domain',
                'username',
                'password',
                'verify_ssl'
            ],
            'type': 'array'
        }

    @staticmethod
    def _get_created_by(device_raw):
        return _parse_admin_audit(device_raw, operation='created_by')

    @staticmethod
    def _get_modified_by(device_raw):
        return _parse_admin_audit(device_raw, operation='modified_by')

    @staticmethod
    def _is_ip_address(ip_addr):
        try:
            ip_address(ip_addr)
            return True
        except ValueError:
            return False

    @staticmethod
    def _is_data_variables_on_map(data_key: str):
        return data_key in ANSIBLE_DATA_VARBS_STATIC_MAP

    @staticmethod
    def _get_inventory_data(device_raw):
        if isinstance((device_raw.get('summary_fields'), device_raw.get('summary_fields').get('inventory')), dict):
            inventory = device_raw.get('summary_fields').get('inventory')
            return inventory.get('id'), inventory.get('name')
        return None, None

    @staticmethod
    def _get_host_groups(groups_raw):
        if isinstance(groups_raw, dict) and groups_raw and 'groups' in groups_raw:
            groups: dict = groups_raw.get('groups')
            for host_group in groups['results']:
                yield AnsiblelHostGroups(id=host_group.get('id'), name=host_group.get('name'))

    def __parse_variables_raw_list_content(self, device, content, field_name):
        """
            can be list of primitive type OR list of dict items
        """

        if self._is_data_variables_on_map(field_name) and content is not None:
            for item in content:
                for (data_name, data_content) in item.items():
                    device[field_name].append(AnsibleDataVariables(name=data_name, content=[data_content]))
        else:
            if not device.does_field_exist(ANSIBEL_VARBS_PREFIX + field_name):
                device.declare_new_field(ANSIBEL_VARBS_PREFIX + field_name, ListField(str, field_name))
            for item in content:
                device[ANSIBEL_VARBS_PREFIX + field_name].append(item)

    def __parse_variables_raw_dict_content(self, device, content, field_name):
        if self._is_data_variables_on_map(field_name):
            for (data_name, data_content) in content.items():
                if data_content:
                    device[field_name].append(AnsibleDataVariables(name=data_name, content=[data_content]))

    def _parse_host_data_variables(self, device, variables_raw):
        try:
            if variables_raw:
                variables: dict = from_json(variables_raw)
                for data in sorted(variables):
                    #
                    #  AVPair Type  - dynamic fields
                    #
                    content = variables.get(data)
                    if isinstance(content, (int, str, bool)):
                        if not device.does_field_exist(ANSIBEL_VARBS_PREFIX + data):
                            device.declare_new_field(ANSIBEL_VARBS_PREFIX + data, Field(type(content), data))
                        device[ANSIBEL_VARBS_PREFIX + data] = content

                    elif isinstance(content, list):
                        self.__parse_variables_raw_list_content(device, content, data)

                    elif content is None:
                        # skipping Null attribute value
                        pass
                    #
                    #  dict Type , static fields .
                    #
                    elif isinstance(content, dict):
                        self.__parse_variables_raw_dict_content(device, content, data)

                    else:
                        logger.error(
                            f'Data Key: {data} '
                            f'Type:{type(content)} is missing on axon ansibel host variables data map ')

        except Exception as e:
            logger.exception(f'fatal error parsing Host {device.name} variables ! ')

    @staticmethod
    def add_ip_address_from_host_varibles(device):
        try:
            attr = device.to_dict()
            for field in ANSIBLE_IP_ADDRESS_DATA_VARBS:
                if attr.get(field):
                    if not any(nic['ips'][0] == attr.get(field) for nic in device.network_interfaces):
                        device.add_nic(ips=[device[field]])
        except AttributeError:
            pass

    @staticmethod
    def set_cloud_id(device):
        try:
            attr = device.to_dict()
            # AMS type
            if 'ec2_id' in attr:
                device.cloud_id = attr.get('ec2_id')
                device.cloud_provider = 'AWS'
            elif 'gce_id' in attr:
                device.cloud_id = attr.get('gce_id')
                device.cloud_provider = 'GCP'
            elif 'deviceId' in attr:
                device.cloud_id = attr.get('deviceId')
                device.cloud_provider = 'azure'

        except Exception:
            logger.exception(f'ERROR mapping cloud ID for device {device.get_raw()}')

    def _create_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            device_id = \
                device_raw.get('id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = str(device_id) + '_' + (device_raw.get('name') or '')

            if not device_raw.get('name'):
                logger.warning(f'Skipping ansible name is null  {device_raw}')
                return None
            # ansibel name can be hostname or ip
            if device_raw.get('name') in FILTER_LOCALHOST_ADDR:
                logger.warning(f'Skipping local host device  {device_raw}')
                return None
            device.name = device_raw.get('name')

            if self._is_ip_address(device.name):
                device.add_nic(ips=[str(device.name)])
            else:
                device.hostname = device.name

            device.device_type = device_raw.get('type')
            device.enabled = device_raw.get('enabled')
            device.description = device_raw.get('description')
            device.inventory_id, device.inventory_name = self._get_inventory_data(device_raw)
            device.created_at = parse_date(device_raw.get('created'))
            device.modified_at = parse_date(device_raw.get('modified'))
            device.created_by = self._get_created_by(device_raw)
            device.first_seen = parse_date(device_raw.get('created'))
            device.modified_by = self._get_modified_by(device_raw)

            try:
                for group in self._get_host_groups(device_raw.get('summary_fields')):
                    device.groups.append(group)
            except Exception:
                logger.exception(f'Problem with parsing host groups  for {device_raw}')

            # Ansible Host variables can by null or a dict of external resources verbs
            self._parse_host_data_variables(device, device_raw.get('variables'))
            self.add_ip_address_from_host_varibles(device)

            try:
                # set cloud_id
                self.set_cloud_id(device)
            except Exception:
                logger.exception(f'Problem with parsing cloud id for {device_raw}')

            return device

        except Exception as e:
            logger.exception(f'Problem with fetching Ansible Tower Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets, AdapterProperty.Manager]
