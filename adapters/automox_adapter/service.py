import datetime
import logging
import os

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.consts.system_consts import GENERIC_ERROR_MESSAGE
from axonius.fields import Field, ListField
from axonius.utils.datetime import parse_date
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.plugin_base import EntityType, add_rule, return_error
from axonius.clients.rest.connection import RESTException
from axonius.smart_json_class import SmartJsonClass
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from automox_adapter.connection import AutomoxConnection
from automox_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class AutmoxPackage(SmartJsonClass):
    display_name = Field(str, 'Display Name')
    name = Field(str, 'Name')
    installed = Field(bool, 'Installed')
    severity = Field(str, 'Severity')
    version = Field(str, 'Version')


class AutomoxAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        basic_device_id = Field(str)
        org_id = Field(str, 'Organization Id')
        instance_id = Field(str, 'Instancef Id')
        last_refresh_time = Field(datetime.datetime, 'Last Refresh Time')
        last_update_time = Field(datetime.datetime, 'Last Update Time')
        automox_tags = ListField(str, 'Automox Tags')
        next_patch_time = Field(datetime.datetime, 'Next Patch Time')
        patches = Field(int, 'Patches')
        pending_patches = Field(int, 'Pending Patches')
        automox_packages = ListField(AutmoxPackage, 'Automox Packages')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @add_rule('install_update', methods=['POST'])
    def install_update(self):
        try:
            if self.get_method() != 'POST':
                return return_error('Method not supported', 405)
            automox_dict = self.get_request_data_as_object()
            device_id = automox_dict.get('device_id')
            client_id = automox_dict.get('client_id')
            org_id = automox_dict.get('org_id')
            update_name = automox_dict.get('update_name')
            automox_obj = self.get_connection(self._get_client_config_by_client_id(client_id))
            with automox_obj:
                device_raw = automox_obj.install_update(device_id, org_id, update_name)
            device = self._create_device(device_raw)
            if device:
                self._save_data_from_plugin(
                    client_id,
                    {'raw': [], 'parsed': [device.to_dict()]},
                    EntityType.Devices, False)
                self._save_field_names_to_db(EntityType.Devices)
        except Exception as e:
            logger.exception(f'Problem during isolating changes')
            return return_error(str(e) if os.environ.get('PROD') == 'false' else GENERIC_ERROR_MESSAGE, 500)
        return '', 200

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'),
                                                https_proxy=client_config.get('https_proxy'))

    @staticmethod
    def get_connection(client_config):
        connection = AutomoxConnection(domain=client_config['domain'],
                                       verify_ssl=client_config['verify_ssl'],
                                       https_proxy=client_config.get('https_proxy'),
                                       apikey=client_config['apikey'])
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
        The schema AutomoxAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Automox Domain',
                    'type': 'string'
                },
                {
                    'name': 'apikey',
                    'title': 'API Key',
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
                'apikey',
                'verify_ssl'
            ],
            'type': 'array'
        }

    # pylint: disable=too-many-branches, too-many-statements, too-many-nested-blocks
    def _create_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            device_id = device_raw.get('id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = str(device_id) + '_' + (device_raw.get('name') or '')
            device.basic_device_id = device_id
            device.first_seen = parse_date(device_raw.get('create_time'))
            device.hostname = device_raw.get('name')
            if isinstance(device_raw.get('organization_id'), int):
                device.org_id = device_raw.get('organization_id')
            if isinstance(device_raw.get('ip_addrs'), list):
                device.add_nic(ips=device_raw.get('ip_addrs'))
            device.instance_id = device_raw.get('instance_id')
            last_refresh_time = parse_date(device_raw.get('last_refresh_time'))
            device.last_refresh_time = last_refresh_time
            last_seen = last_refresh_time
            last_update_time = parse_date(device_raw.get('last_update_time'))
            device.last_update_time = last_update_time
            if not last_seen or (last_update_time and last_update_time > last_seen):
                last_seen = last_update_time
            device.last_seen = last_seen
            device.figure_os((device_raw.get('os_family') or '') + ' ' + (device_raw.get('os_name') or ''))
            if isinstance(device_raw.get('tags'), list):
                device.automox_tags = device_raw.get('tags')
            device_details = device_raw.get('detail')
            if not isinstance(device_details, dict):
                device_details = {}
            nics = device_details.get('NICS')
            if not isinstance(nics, list):
                nics = []
            for nic in nics:
                try:
                    mac = nic.get('MAC') if nic.get('MAC') else None
                    if mac == '(null)':
                        mac = None
                    ips = nic.get('IPS') if isinstance(nic.get('IPS'), list) else None
                    if mac or ips:
                        device.add_nic(mac=mac, ips=ips)
                except Exception:
                    logger.exception(f'Problem with nic {nic}')
            device.device_serial = device_details.get('SERIAL')
            device.device_manufacturer = device_details.get('VENDOR')
            device.pending_patches = device_raw.get('pending_patches')\
                if isinstance(device_raw.get('pending_patches'), int) else None
            device.patches = device_raw.get('patches') if isinstance(device_raw.get('patches'), int) else None
            device.device_model = device_details.get('MODEL')
            try:
                device.last_used_users = [device_details.get('LAST_USER_LOGON').get('USER')]
            except Exception:
                pass
            try:
                if device_raw.get('uptime'):
                    device.set_boot_time(uptime=datetime.timedelta(seconds=int(device_raw.get('uptime'))))
            except Exception:
                pass
            device.uuid = device_raw.get('uuid')
            device.next_patch_time = parse_date(device_raw.get('next_patch_time'))
            apps_raw = device_raw.get('apps_raw')
            if not isinstance(apps_raw, list):
                apps_raw = []
            for app_raw in apps_raw:
                try:
                    app_name = app_raw.get('display_name')
                    app_version = app_raw.get('version')

                    if not app_raw.get('installed'):
                        continue
                    if 'Security Update (KB' in app_name or 'Update for Microsoft' in app_name or\
                            'Security Update for Microsoft' in app_name or \
                            'Servicing Stack Update for Windows' in app_name or 'Update for Skype' in app_name:
                        device.add_security_patch(security_patch_id=app_name)
                    else:
                        device.add_installed_software(name=app_name, version=app_version)
                    device.automox_packages.append(AutmoxPackage(name=app_raw.get('name'),
                                                                 display_name=app_raw.get('display_name'),
                                                                 version=app_raw.get('version'),
                                                                 installed=app_raw.get('installed'),
                                                                 severity=app_raw.get('severity')))
                except Exception:
                    logger.exception(f'Probelm getting app {app_raw}')
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Automox Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent]
