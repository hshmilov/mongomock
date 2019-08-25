# pylint: disable=too-many-instance-attributes, too-many-nested-blocks, too-many-branches, too-many-statements
import logging
import datetime

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter, DeviceRunningState
from axonius.fields import Field
from axonius.smart_json_class import SmartJsonClass
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import guaranteed_list, parse_bool_from_raw
from axonius.mixins.configurable import Configurable
from vcloud_director_adapter.connection import VcloudDirectorConnection
from vcloud_director_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


# pylint: disable=too-many-instance-attributes
class GuestCustomization(SmartJsonClass):
    enabled = Field(bool, 'Enabled')
    change_sid = Field(bool, 'Change Sid')
    join_domain_enabled = Field(bool, 'Join Domain Enabled')
    use_org_settings = Field(bool, 'Use Org Settings')
    domain_name = Field(str, 'Domain Name')
    domain_user_name = Field(str, 'Domain User Name')
    customization_script = Field(str, 'Customization Script')
    admin_auto_logon_count = Field(int, 'Admin Auto Logon Count')
    admin_auto_logon_enabled = Field(bool, 'Admin Auto Logon Enabled')
    admin_password_auto = Field(bool, 'Admin Password Auto')
    admin_password_enabled = Field(bool, 'Admin Password Enabled')
    reset_password_required = Field(bool, 'Reset Password Required')


class VcloudDirectorAdapter(AdapterBase, Configurable):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        date_created = Field(datetime.datetime, 'Date Created')
        vmware_tools_version = Field(str, 'VMWare Tools Version')

        # Guest Customization
        guest_customization = Field(GuestCustomization, 'Guest Customization')

        # VM Capabilities
        cpu_hot_add_enabled = Field(bool, 'CPU Hot Add Enabled')
        memory_hot_add_enabled = Field(bool, 'Memory Hot Add Enabled')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'))

    @staticmethod
    def get_connection(client_config):
        connection = VcloudDirectorConnection(domain=client_config['domain'],
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

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific  domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        with client_data:
            yield from client_data.get_device_list(self.__max_async_requests)

    @staticmethod
    def _clients_schema():
        """
        The schema vCloudDirectorAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'vCloud Director Domain',
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

    # pylint: disable=too-many-instance-attributes, too-many-nested-blocks, too-many-branches, too-many-statements
    def _create_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            device_id = device_raw.get('@id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = device_id
            device.name = device_raw.get('@name')
            device.date_created = parse_date(device_raw.get('DateCreated'))

            network_settings = device_raw.get('NetworkConnectionSection')
            if network_settings:
                for nic in guaranteed_list(network_settings.get('NetworkConnection')):
                    try:
                        if parse_bool_from_raw(nic.get('IsConnected')) is True:
                            ips = [ip.strip() for ip in guaranteed_list(nic.get('IpAddress'))]
                            mac = nic.get('MACAddress')
                            external_ips = [ip.strip() for ip in guaranteed_list(nic.get('ExternalIpAddress'))]
                            for external_ip in external_ips:
                                device.add_public_ip(external_ip)
                                ips.append(external_ip)
                            if mac or ips:
                                device.add_nic(mac=mac, ips=ips, name=nic.get('@network'))
                    except Exception:
                        logger.exception(f'Failed parsing nic {str(nic)}')

            guest_customization_raw = device_raw.get('GuestCustomizationSection')
            if guest_customization_raw:
                try:
                    guest_customization = GuestCustomization()
                    guest_customization.enabled = parse_bool_from_raw(guest_customization_raw.get('Enabled'))
                    try:
                        guest_customization.admin_auto_logon_count = int(
                            guest_customization_raw.get('AdminAutoLogonCount')
                        )
                    except Exception:
                        pass
                    guest_customization.admin_auto_logon_enabled = parse_bool_from_raw(
                        guest_customization_raw.get('AdminAutoLogonEnabled'))
                    guest_customization.admin_password_auto = parse_bool_from_raw(
                        guest_customization_raw.get('AdminPasswordAuto'))
                    guest_customization.admin_password_enabled = parse_bool_from_raw(
                        guest_customization_raw.get('AdminPasswordEnabled'))
                    guest_customization.change_sid = parse_bool_from_raw(guest_customization_raw.get('ChangeSid'))
                    guest_customization.join_domain_enabled = parse_bool_from_raw(
                        guest_customization_raw.get('JoinDomainEnabled'))
                    guest_customization.reset_password_required = parse_bool_from_raw(
                        guest_customization_raw.get('ResetPasswordRequired'))
                    guest_customization.use_org_settings = parse_bool_from_raw(
                        guest_customization_raw.get('UseOrgSettings'))
                    guest_customization.domain_name = guest_customization_raw.get('DomainName')
                    guest_customization.domain_user_name = guest_customization_raw.get('DomainUserName')
                    guest_customization.customization_script = guest_customization_raw.get('CustomizationScript')

                    device.guest_customization = guest_customization
                except Exception:
                    logger.exception(f'Failed parsing guest customization {guest_customization_raw}')

            try:
                device.cpu_hot_add_enabled = parse_bool_from_raw(
                    (device_raw.get('VmCapabilities') or {}).get('CpuHotAddEnabled'))
                device.memory_hot_add_enabled = parse_bool_from_raw(
                    (device_raw.get('VmCapabilities') or {}).get('MemoryHotAddEnabled'))
            except Exception:
                logger.exception('Failed parsing VM Capabilities')

            try:
                vm_spec_raw = device_raw.get('VmSpecSection') or {}
                device.vmware_tools_version = vm_spec_raw.get('VmToolsVersion')
                num_of_cpus = vm_spec_raw.get('NumCpus')
                if num_of_cpus:
                    try:
                        num_of_cpus = int(num_of_cpus)
                        device.total_number_of_physical_processors = num_of_cpus    # pylint: disable=invalid-name
                        device.total_number_of_cores = num_of_cpus * \
                            int(vm_spec_raw.get('NumCoresPerSocket'))
                    except Exception:
                        pass

                total_memory = (vm_spec_raw.get('MemoryResourceMb') or {}).get('Configured')
                if total_memory:
                    try:
                        device.total_physical_memory = round(int(total_memory) / 1024, 2)
                    except Exception:
                        pass

                for disk_setting in guaranteed_list((vm_spec_raw.get('DiskSection') or {}).get('DiskSettings')):
                    try:
                        device.add_hd(total_size=round(int(disk_setting.get('SizeMb')) / 1024, 2))
                    except Exception:
                        pass
            except Exception:
                logger.exception(f'Could not parse VmSpecSection')

            try:
                os = (device_raw.get('ovf:OperatingSystemSection') or {}).get(
                    'ovf:Description') or (device_raw.get('VmSpecSection') or {}).get('OsType')
                device.figure_os(os)
            except Exception:
                logger.exception(f'Could not figure operating system')

            try:
                device.description = device_raw.get('Description')
            except Exception:
                pass

            try:
                device.device_disabled = parse_bool_from_raw(device_raw.get('@deployed')) is False
            except Exception:
                pass

            try:
                powered_state = {
                    '4': DeviceRunningState.TurnedOn,
                    '8': DeviceRunningState.TurnedOff,
                    '3': DeviceRunningState.Suspended
                }.get(device_raw.get('@status'), DeviceRunningState.Unknown)

                device.power_state = powered_state
                if powered_state == DeviceRunningState.TurnedOn:
                    device.last_seen = datetime.datetime.now()
            except Exception:
                pass

            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching vCloudDirector Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets, AdapterProperty.Virtualization]

    @classmethod
    def _db_config_schema(cls) -> dict:
        return {
            'items': [
                {
                    'name': 'max_async_requests',
                    'title': 'Max Parallel Requests',
                    'type': 'integer'
                }
            ],
            'required': [
                'max_async_requests'
            ],
            'pretty_name': 'vCloud Director Configuration',
            'type': 'array'
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'max_async_requests': 50
        }

    def _on_config_update(self, config):
        self.__max_async_requests = config['max_async_requests']
