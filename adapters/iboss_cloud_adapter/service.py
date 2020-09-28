import logging
import base64
import ipaddress
import json

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection, RESTException
from axonius.devices.device_adapter import AGENT_NAMES
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import parse_bool_from_raw, int_or_none
from iboss_cloud_adapter.connection import IbossCloudConnection
from iboss_cloud_adapter.client_id import get_client_id
from iboss_cloud_adapter.structures import IbossCloudDeviceInstance, IbossCloudUserInstance
from iboss_cloud_adapter.consts import NODE_DEVICE, DOMAIN_CONFIG, CLOUD_CONNECTED_DEVICE, STATIC_DEVICE, DYNAMIC_DEVICE
from iboss_cloud_adapter.structures import SubnetPolicy, NodeCollection, DeviceInstance

logger = logging.getLogger(f'axonius.{__name__}')


# pylint: disable=logging-format-interpolation


class IbossCloudAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(IbossCloudDeviceInstance):
        pass

    class MyUserAdapter(IbossCloudUserInstance):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(DOMAIN_CONFIG,
                                                https_proxy=client_config.get('https_proxy'))

    @staticmethod
    def get_connection(client_config):
        connection = IbossCloudConnection(domain=DOMAIN_CONFIG,
                                          verify_ssl=client_config['verify_ssl'],
                                          https_proxy=client_config.get('https_proxy'),
                                          username=client_config['username'],
                                          password=client_config['password'])
        with connection:
            pass  # check that the connection credentials are valid
        return connection

    def _connect_client(self, client_config):
        try:
            return self.get_connection(client_config)
        except RESTException as e:
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                DOMAIN_CONFIG, str(e))
            logger.exception(message)
            raise ClientConnectionException(message)

    @staticmethod
    def _query_devices_by_client(client_name, client_data):
        """
        Get all devices from a specific domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        with client_data:
            yield from client_data.get_device_list()

    @staticmethod
    # pylint: disable=arguments-differ
    def _query_users_by_client(client_name, client_data):
        """
        Get all users from a specific domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        with client_data:
            yield from client_data.get_user_list()

    @staticmethod
    def _clients_schema():
        """
        The schema IbossCloudAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
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
                'username',
                'password',
                'verify_ssl'
            ],
            'type': 'array'
        }

    @staticmethod
    def _fill_iboss_cloud_node_fields(device_raw: dict, instance_type: str, device: MyDeviceAdapter):
        try:
            node_collection = NodeCollection()

            node_collection.machine_id = device_raw.get('machineId')
            node_collection.account_setting_id = device_raw.get('accountSettingId')
            node_collection.node_state = device_raw.get('nodeState')
            node_collection.initializing_message = device_raw.get('initializationMessage')
            node_collection.product_class = device_raw.get('productClass')
            node_collection.product_family = device_raw.get('productFamily')
            node_collection.communication_type = device_raw.get('communicationType')
            node_collection.communicationSelection = device_raw.get('communicationSelection')
            node_collection.watermark = device_raw.get('watermark')
            node_collection.region = device_raw.get('region')
            node_collection.asset_type = device_raw.get('assetType')
            node_collection.asset_id = device_raw.get('assetId')
            node_collection.account_name = device_raw.get('accountName')
            node_collection.account_priority = device_raw.get('accountPriority')
            node_collection.public_url = device_raw.get('publicUrl')
            node_collection.type = instance_type

            device.node_collection = node_collection
        except Exception:
            logger.exception(f'Failed creating node collection instance for device {device_raw}')

    @staticmethod
    def _create_cloud_connected_device(device_raw: dict, instance_type: str, domain: str, device: MyDeviceAdapter):
        try:
            device_id = device_raw.get('agentReference')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = f'{str(device_id)}_{domain or ""}'

            device.first_seen = parse_date(device_raw.get('firstSeen'))
            device.last_seen = parse_date(device_raw.get('lastSeen'))
            device.add_users(username=device_raw.get('username'))
            device.name = device_raw.get('deviceName')
            device.hostname = device_raw.get('deviceName')
            device.add_agent_version(agent=AGENT_NAMES.iboss,
                                     version=device_raw.get('agentVersion'))

            try:
                registration_info = device_raw.get('registrationInfo')
                if registration_info:
                    extra_info = json.loads(base64.b64decode(registration_info).decode('utf-8'))
                    if isinstance(extra_info, dict):
                        ip = extra_info.get('publicIpAddress')
                        try:
                            device.add_public_ip(ip=ip)
                        except Exception:
                            if ip is not None:
                                logger.exception(f'Failed parsing public ip for {instance_type}, got {extra_info}')

                        mac = extra_info.get('macAddress')
                        ips = extra_info.get('privateIpAddress') or []
                        if isinstance(ips, str):
                            ips = [ips]
                        if ip:
                            ips.append(ip)
                        device.add_nic(mac=mac,
                                       ips=ips)

            except Exception:
                logger.exception(f'Failed parsing registration info base64 info of {registration_info}')

            active_device = parse_bool_from_raw(device_raw.get('active'))
            if isinstance(active_device, bool):
                device.device_disabled = not active_device

            os_string = device_raw.get('deviceType')
            device.figure_os(os_string=os_string)

            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Failed creating {instance_type} instance for device {device_raw}')
            return None

    # pylint: disable=too-many-branches, too-many-statements
    def _create_node_device(self, device_raw: dict, instance_type: str, domain: str, device: MyDeviceAdapter):
        try:
            device_id = device_raw.get('cloudNodeId') or device_raw.get('cloudClusterId')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = f'{str(device_id)}_{domain or ""}'

            device.name = device_raw.get('nodeName')
            device.cloud_id = device_raw.get('cloudClusterId')
            device.hostname = device_raw.get('nodeHostName')
            device.description = device_raw.get('description')
            device.bios_version = device_raw.get('currentFirmwareVersion')
            device.last_seen = parse_date(device_raw.get('modifyDate'))
            device.first_seen = parse_date(device_raw.get('initializationDate'))
            device.time_zone = device_raw.get('timeZone')
            device.physical_location = device_raw.get('locationPhysical')

            dns_servers = device_raw.get('adminInterfaceDns') or []
            if isinstance(dns_servers, str):
                dns_servers = [dns_servers]
            if isinstance(device_raw.get('nodeAdminInterfaceDns'), str):
                dns_servers.append(device_raw.get('nodeAdminInterfaceDns'))
            elif isinstance(device_raw.get('nodeAdminInterfaceDns'), list):
                dns_servers.extend(device_raw.get('nodeAdminInterfaceDns'))
            if isinstance(device_raw.get('masterAdminInterfaceDns'), str):
                dns_servers.append(device_raw.get('masterAdminInterfaceDns'))
            elif isinstance(device_raw.get('masterAdminInterfaceDns'), list):
                dns_servers.extend(device_raw.get('masterAdminInterfaceDns'))
            device.dns_servers = list(set(dns_servers))  # No overlap data

            mac = device_raw.get('adminInterfaceMacAddress')
            ips = device_raw.get('adminInterfacePublicIp') or []
            if isinstance(ips, str):
                ips = [ips]
            if isinstance(device_raw.get('publicSystemIp'), str):
                ips.append(device_raw.get('publicSystemIp'))
            elif isinstance(device_raw.get('publicSystemIp'), list):
                ips.extend(device_raw.get('publicSystemIp'))
            if isinstance(device_raw.get('localSystemIp'), str):
                ips.append(device_raw.get('localSystemIp'))
            elif isinstance(device_raw.get('localSystemIp'), list):
                ips.extend(device_raw.get('localSystemIp'))
            if isinstance(device_raw.get('privateIpAddress'), str):
                ips.append(device_raw.get('privateIpAddress'))
            elif isinstance(device_raw.get('privateIpAddress'), list):
                ips.extend(device_raw.get('privateIpAddress'))
            if isinstance(device_raw.get('publicIpAddress'), str):
                ips.append(device_raw.get('publicIpAddress'))
            elif isinstance(device_raw.get('publicIpAddress'), list):
                ips.extend(device_raw.get('publicIpAddress'))
            ips = list(set(ips))  # No overlap data
            device.add_nic(mac=mac, ips=ips)

            related_ips = device_raw.get('clusterControlIp') or []
            if isinstance(related_ips, str):
                related_ips = [related_ips]
            if isinstance(device_raw.get('remoteIp'), str):
                related_ips.append(device_raw.get('remoteIp'))
            elif isinstance(device_raw.get('remoteIp'), list):
                related_ips.extend(device_raw.get('remoteIp'))
            device.set_related_ips(related_ips)

            self._fill_iboss_cloud_node_fields(device_raw, instance_type, device)

            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Failed creating {instance_type} instance for device {device_raw}')
            return None

    @staticmethod
    def _fill_iboss_cloud_device_fields(device_raw: dict, instance_type: str, device: MyDeviceAdapter):
        try:
            device_instance = DeviceInstance()

            device_instance.group_name = device_raw.get('groupName')
            device_instance.group_number = device_raw.get('groupNumber')
            device_instance.is_local_proxy = parse_bool_from_raw(device_raw.get('isLocalProxy'))
            device_instance.is_mobile_client = parse_bool_from_raw(device_raw.get('isMobileClient'))
            device_instance.note = device_raw.get('note')
            device_instance.type = instance_type

            device.device_instance = device_instance
        except Exception:
            logger.exception(f'Failed creating {instance_type} instance for device {device_raw}')

    def _create_device(self, device_raw: dict, policies_by_network: dict, instance_type: str, domain: str,
                       device: MyDeviceAdapter):
        try:
            device_id = device_raw.get('id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = f'{str(device_id)}_{domain or ""}'

            device.name = device_raw.get('computerName')
            device.current_logged_user = device_raw.get('username')

            subnets = []
            subnet_policies = []
            ip = device_raw.get('ipAddress')
            mac = device_raw.get('macAddress')
            for network, policies_list in policies_by_network.items():
                if ipaddress.ip_address(ip) in network:
                    subnets.append(str(network))

                    for policy_dict in policies_list or []:
                        if isinstance(policy_dict, dict):
                            subnet_policy = SubnetPolicy()
                            subnet_policy.id = policy_dict.get('id')
                            subnet_policy.note = policy_dict.get('note')
                            subnet_policy.vlan_id = policy_dict.get('vlanId')
                            subnet_policy.tunnel_type = policy_dict.get('tunnelType')
                            subnet_policy.ip_address = policy_dict.get('ipAddress')

                            subnet_policies.append(subnet_policy)
            device.subnet_policies = subnet_policies
            device.add_nic(mac=mac, ips=[ip], subnets=subnets)

            self._fill_iboss_cloud_device_fields(device_raw, instance_type, device)

            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching IbossCloud Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        """
        Gets raw data and yields Device objects.
        :param devices_raw_data: the raw data we get.
        :return:
        """
        for device_raw, policies_by_network, instance_type, domain in devices_raw_data:
            if not device_raw:
                continue
            try:
                if instance_type == NODE_DEVICE:
                    # noinspection PyTypeChecker
                    device = self._create_node_device(device_raw, instance_type, domain, self._new_device_adapter())
                elif instance_type == CLOUD_CONNECTED_DEVICE:
                    # noinspection PyTypeChecker
                    device = self._create_cloud_connected_device(device_raw, instance_type, domain,
                                                                 self._new_device_adapter())
                else:
                    # noinspection PyTypeChecker
                    device = self._create_device(device_raw, policies_by_network, instance_type, domain,
                                                 self._new_device_adapter())

                if device:
                    yield device
            except Exception:
                logger.exception(f'Problem with fetching IbossCloud Device for {device_raw}')

    @staticmethod
    def _fill_iboss_cloud_user_fields(user_raw: dict, user: MyUserAdapter):
        try:
            user.auth_mode = user_raw.get('authMode')
            user.note = user_raw.get('note')
            user.policy_group = user_raw.get('policyGroup')
            user.policy_group_name = user_raw.get('policyGroupName')
        except Exception:
            logger.exception(f'Failed creating instance for user {user_raw}')

    @staticmethod
    def _fill_iboss_cloud_connected_user_fields(user_raw: dict, user: MyUserAdapter):
        try:
            user.first_seen = parse_date(user_raw.get('firstSeen'))

            try:
                registration_info = user_raw.get('registrationInfo')
                if registration_info:
                    extra_info = json.loads(base64.b64decode(registration_info).decode('utf-8'))
                    if isinstance(extra_info, dict):
                        group_association = extra_info.get('mappedByGroupPolicyLayerNames')
                        if isinstance(group_association, list):
                            user.group_association = group_association
            except Exception:
                logger.exception(f'Failed parsing registration info base64 info of {registration_info}')

        except Exception:
            logger.exception(f'Failed creating instance for cloud connected user {user_raw}')

    @staticmethod
    def _create_dynamic_user(user_raw: dict, domain: str, instance_type: str, user: MyUserAdapter):
        try:
            user_id = user_raw.get('id')
            username = user_raw.get('username')
            if user_id is None or not username:
                logger.warning(f'Bad dynamic user with no ID {user_raw}')
                return None
            user.id = str(user_id) + '_' + (user_raw.get('username') or '')

            user.username = username
            user.policy_group = int_or_none(user_raw.get('groupNumber'))
            user.policy_group_name = user_raw.get('groupName')
            try:
                user.ip_v4 = user_raw.get('ipAddress')
                user.ip_v4_raw = user_raw.get('ipAddress')
            except Exception:
                pass
            user.note = user_raw.get('note')

            user.set_raw(user_raw)
            return user
        except Exception:
            logger.exception(f'Problem with fetching IbossCloud {instance_type} User for {user_raw} in {domain}')
            return None

    def _create_cloud_connected_user(self, user_raw: dict, domain: str, user: MyUserAdapter):
        try:
            user_id = user_raw.get('agentReference')
            if user_id is None:
                logger.warning(f'Bad cloud user with no ID {user_raw}')
                return None
            user.id = str(user_id) + '_' + (user_raw.get('username') or '')

            # Means that these are servers and a single user would not be associated with a server
            if user_raw.get('username') == user_raw.get('deviceName'):
                logger.debug(f'Server could not be associated with a user {user_raw}')
                return None

            username = user_raw.get('username')
            user.username = user_raw.get('username')

            if isinstance(username, str) and '@' in username:
                user.mail = username

            user.last_seen = parse_date(user_raw.get('lastSeen'))
            user.add_associated_device(device_caption=user_raw.get('deviceName'))

            self._fill_iboss_cloud_connected_user_fields(user_raw, user)

            user.set_raw(user_raw)
            return user
        except Exception:
            logger.exception(f'Problem with fetching IbossCloud User for {user_raw} in {domain}')
            return None

    def _create_user(self, user_raw: dict, domain: str, user: MyUserAdapter):
        try:
            user_id = user_raw.get('id')
            if user_id is None:
                logger.warning(f'Bad user with no ID {user_raw}')
                return None
            user.id = str(user_id) + '_' + (user_raw.get('userName') or '')

            user.first_name = user_raw.get('firstName')
            user.last_name = user_raw.get('lastName')
            user.username = user_raw.get('userName')
            user.employee_type = user_raw.get('userTypeName')
            user.is_admin = parse_bool_from_raw(user_raw.get('fullAdmin'))

            self._fill_iboss_cloud_user_fields(user_raw, user)

            user.set_raw(user_raw)
            return user
        except Exception:
            logger.exception(f'Problem with fetching IbossCloud User for {user_raw} from {domain}')
            return None

    # pylint: disable=arguments-differ
    def _parse_users_raw_data(self, users_raw_data):
        """
        Gets raw data and yields User objects.
        :param users_raw_data: the raw data we get.
        :return:
        """
        for user_raw, _, instance_type, domain in users_raw_data:
            if not user_raw:
                continue
            try:
                if instance_type == CLOUD_CONNECTED_DEVICE:
                    # noinspection PyTypeChecker
                    user = self._create_cloud_connected_user(user_raw, domain, self._new_user_adapter())
                elif instance_type in (STATIC_DEVICE, DYNAMIC_DEVICE):
                    # noinspection PyTypeChecker
                    user = self._create_dynamic_user(user_raw, domain, instance_type, self._new_user_adapter())
                else:
                    # noinspection PyTypeChecker
                    user = self._create_user(user_raw, domain, self._new_user_adapter())
                if user:
                    yield user
            except Exception:
                logger.exception(f'Problem with fetching IbossCloud User for {user_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets, AdapterProperty.UserManagement]
