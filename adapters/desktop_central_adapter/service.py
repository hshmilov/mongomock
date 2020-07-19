import datetime
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from axonius.devices.device_adapter import DeviceAdapter, AGENT_NAMES
from axonius.fields import Field, ListField
from axonius.utils.datetime import parse_date
from axonius.smart_json_class import SmartJsonClass
from axonius.utils.files import get_local_config_file
from desktop_central_adapter import consts
from desktop_central_adapter.connection import DesktopCentralConnection

logger = logging.getLogger(f'axonius.{__name__}')


class BitlockerData(SmartJsonClass):
    encryption_method = Field(str, 'Encryption Method')
    encryption_status = Field(str, 'Encryption Status')
    last_updated_time = Field(datetime.date, 'Last Updated Time')
    lock_status = Field(str, 'Lock Status')
    logical_drive_name = Field(str, 'Logical Drive Name')
    logical_disk_type = Field(str, 'Logical Disk Type')
    protection_status = Field(str, 'Protection Status')
    recovery_key_status = Field(str, 'Recovery Key Status')


class DesktopCentralAdapter(AdapterBase):

    class MyDeviceAdapter(DeviceAdapter):
        installation_status = Field(str, 'Installation Status')
        device_type = Field(str, 'Device Type')
        warranty_expiry_date = Field(datetime.datetime, 'Warranty Expiry Date')
        shipping_date = Field(datetime.datetime, 'Shipping Date')
        disks_info = ListField(BitlockerData, 'Bitlocker Data')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    def _get_client_id(self, client_config):
        return client_config['domain']

    def _test_reachability(self, client_config):
        return RESTConnection.test_reachability(client_config.get('domain'),
                                                port=client_config.get('port') or consts.DEFAULT_PORT,
                                                https_proxy=client_config.get('https_proxy'),
                                                http_proxy=client_config.get('http_proxy'))

    def _connect_client(self, client_config):
        try:
            connection = DesktopCentralConnection(domain=client_config['domain'],
                                                  verify_ssl=client_config['verify_ssl'],
                                                  username=client_config['username'],
                                                  password=client_config['password'],
                                                  https_proxy=client_config.get('https_proxy'),
                                                  http_proxy=client_config.get('http_proxy'),
                                                  port=client_config.get('port', consts.DEFAULT_PORT),
                                                  username_domain=client_config.get('username_domain'))
            with connection:
                pass  # check that the connection credentials are valid
            return connection
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
        try:
            client_data.connect()
            yield from client_data.get_device_list()
        finally:
            client_data.close()

    def _clients_schema(self):
        """
        The schema the adapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Desktop Central Domain',
                    'type': 'string'
                },
                {
                    'name': 'username',
                    'title': 'User Name',
                    'type': 'string'
                },
                {
                    'name': 'username_domain',
                    'title': 'Username Domain',
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
                    'name': 'http_proxy',
                    'title': 'HTTP Proxy',
                    'type': 'string'
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

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            try:
                # 22 Means installed
                # In case there is no such field we don't want to miss the device

                device = self._new_device_adapter()
                property_none_list = []
                for device_property in device_raw:
                    if device_raw[device_property] == '--':
                        property_none_list.append(device_property)
                for device_property in property_none_list:
                    del device_raw[device_property]
                if 'resource_id' not in device_raw:
                    logger.info(f'No Desktop Central device Id for {str(device_raw)}')
                    continue
                device.id = str(device_raw.get('resource_id'))
                try:
                    sw_raw = device_raw.get('sw_raw')
                    if not isinstance(sw_raw, list):
                        sw_raw = []
                    for ins_sw in sw_raw:
                        if not isinstance(ins_sw, dict) or not ins_sw.get('software_name'):
                            continue
                        device.add_installed_software(name=ins_sw.get('software_name'),
                                                      version=ins_sw.get('software_version'))
                except Exception:
                    logger.exception(f'Probelm getting sw for {device_raw}')
                try:
                    pa_raw = device_raw.get('pa_raw')
                    if not isinstance(pa_raw, list):
                        pa_raw = []
                    for pa_data in pa_raw:
                        if not isinstance(pa_data, dict) or not pa_data.get('patch_name'):
                            continue
                        device.add_security_patch(security_patch_id=pa_data.get('patch_name'),
                                                  installed_on=parse_date(pa_data.get('installed_time')),
                                                  severity=pa_data.get('severity_name'),
                                                  bulletin_id=pa_data.get('bulletin_id'))
                except Exception:
                    logger.exception(f'Probelm getting sw for {device_raw}')
                device.domain = device_raw.get('domain_netbios_name', '')
                try:
                    sum_raw = device_raw.get('sum_raw')
                    if not isinstance(sum_raw, dict):
                        sum_raw = {}
                    computer_hardware_summary = sum_raw.get('computer_hardware_summary') or {}
                    device.device_manufacturer = computer_hardware_summary.get('device_manufacturer')
                    device.device_model = computer_hardware_summary.get('device_model')
                    device.device_type = computer_hardware_summary.get('device_type')
                    device.device_serial = computer_hardware_summary.get('serial_number')
                    try:
                        device.total_physical_memory = float(computer_hardware_summary.get('memory')) / 1000.0
                    except Exception:
                        pass
                    device.shipping_date = parse_date(computer_hardware_summary.get('shipping_date'))
                    device.warranty_expiry_date = parse_date(computer_hardware_summary.get('warranty_expiry_date'))

                except Exception:
                    logger.exception(f'Problem with sum raw {device_raw}')
                device.hostname = device_raw.get('fqdn_name', device_raw.get('full_name'))
                try:
                    last_seen = device_raw.get('agent_last_contact_time')
                    if last_seen is not None:
                        device.last_seen = datetime.datetime.fromtimestamp(last_seen / 1000)
                except Exception:
                    logger.exception(f'Problem getting last seen for {device_raw}')
                device.figure_os(' '.join([device_raw.get('os_name', ''),
                                           device_raw.get('service_pack', '')]))
                try:
                    if device_raw.get('mac_address') or device_raw.get('ip_address'):
                        mac_addresses = (device_raw.get('mac_address') or '').split(',')
                        filtered_macs = [mac for mac in mac_addresses if mac]
                        ips = (device_raw.get('ip_address') or '').split(',')
                        filtered_ips = [ip for ip in ips if ip]
                        device.add_ips_and_macs(filtered_macs, filtered_ips)
                except Exception:
                    logger.exception('Problem with adding nic to desktop central device')
                device.add_agent_version(agent=AGENT_NAMES.desktop_central, version=device_raw.get('agent_version', ''))
                os_version_list = ''
                try:
                    os_version_list = device_raw.get('os_version', '').split('.')
                    os_major = os_version_list[0]
                    if os_major != '':
                        device.os.major = int(os_major)
                except Exception:
                    logger.exception(f'Problem getting major os for {device_raw}')
                try:
                    if len(os_version_list) > 1 and '(' not in os_version_list[1]:
                        device.os.minor = int(os_version_list[1])
                except Exception:
                    logger.exception(f'Problem getting minor os for {os_version_list}')
                device.installation_status = device_raw.get('installation_status')
                installation_status = device_raw.get('installation_status')
                if installation_status is not None:
                    device.installation_status = {21: 'Yet to install', 22: 'Installed',
                                                  23: 'uninstalled', 24: 'yet to uninstall',
                                                  29: 'installation failure'}.get(installation_status)
                if device_raw.get('agent_logged_on_users'):
                    device.last_used_users = device_raw.get('agent_logged_on_users').split(',')
                bitlocker = device_raw.get('bitlocker')
                if not isinstance(bitlocker, dict):
                    bitlocker = {}
                bitlocker_details = bitlocker.get('bitLockerDetails')
                if not isinstance(bitlocker_details, list):
                    bitlocker_details = []
                for disk in bitlocker_details:
                    try:
                        bitlocker_obj = BitlockerData()
                        bitlocker_obj.encryption_method = disk.get('encryptionMethod')
                        bitlocker_obj.encryption_status = disk.get('encryptionStatus')
                        bitlocker_obj.last_updated_time = parse_date(disk.get('lastUpdatedTime'))
                        bitlocker_obj.lock_status = disk.get('lockStatus')
                        bitlocker_obj.logical_drive_name = disk.get('logicalDriveName')
                        bitlocker_obj.logical_disk_type = disk.get('logiclDiskType')
                        bitlocker_obj.protection_status = disk.get('protectionStatus')
                        bitlocker_obj.recovery_key_status = disk.get('recoveryKeyStatus')
                        device.disks_info.append(bitlocker_obj)
                        is_encrypted = disk.get('encryptionStatus') == 'Fully Encrypted'
                        device.add_hd(path=disk.get('logicalDriveName'), is_encrypted=is_encrypted)
                    except Exception:
                        logger.exception(f'Problem with disk {disk}')

                device.set_raw(device_raw)
                yield device
            except Exception:
                logger.exception('Problem with fetching Desktop Central Device')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent]
