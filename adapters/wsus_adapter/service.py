import datetime
import ipaddress
import logging
import os
import re

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.devices.device_adapter import DeviceAdapter, AGENT_NAMES, DeviceAdapterOS
from axonius.fields import Field, ListField
from axonius.clients.rest.connection import RESTConnection
from axonius.utils.parsing import get_exception_string
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from wsus_adapter import consts
from wsus_adapter.connection import WsusWmiConnection

logger = logging.getLogger(f'axonius.{__name__}')


class WsusAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        wsus_server = Field(str, 'WSUS Server GUID')
        last_sync_result = Field(str, 'Last Sync Result')
        last_sync_time = Field(datetime.datetime, 'Last Sync Time')
        last_reported_inventory_time = Field(datetime.datetime, 'Last Reported Inventory Time')
        last_reported_status_time = Field(datetime.datetime, 'Last Reported Status Time')
        role = Field(str, 'Computer Role')
        groups = ListField(str, 'Groups')

    def __init__(self):
        super().__init__(get_local_config_file(__file__))
        self._date_regex = re.compile('(-*\\d+)')

    def _get_client_id(self, client_config):
        return f'{client_config[consts.WSUS_HOST]}_{client_config[consts.USER]}'

    def _test_reachability(self, client_config):
        return RESTConnection.test_reachability(client_config.get(consts.WSUS_HOST))

    def _connect_client(self, client_config):
        try:
            connection = WsusWmiConnection(
                client_config[consts.WSUS_HOST],
                client_config[consts.USER],
                client_config[consts.PASSWORD],
                self._use_wmi_smb_path,
                self._python_27_path,
                # output_file=client_config.get(consts.WMI_OUTPUT_FILE),
                # working_dir=client_config.get(consts.WMI_WORKING_DIR)
            )
        except Exception as e:
            message = f'Error connecting to WSUS host: {str(client_config[consts.WSUS_HOST])}'
            logger.exception(message)
            raise ClientConnectionException(get_exception_string())
        else:
            return connection

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all computer targets from a specific WSUS server
        :param str client_name: The name of the client
        :param obj client_data: The data that represent a WSUS wmi connection

        :return: A json with all the attributes returned from the WSUS Server
        """
        yield from client_data.get_devices()

    def _clients_schema(self):
        return {
            'items': [
                {
                    'name': consts.WSUS_HOST,
                    'title': 'WSUS Server',
                    'type': 'string'
                },
                {
                    'name': consts.USER,
                    'title': 'User Name',
                    'type': 'string'
                },
                {
                    'name': consts.PASSWORD,
                    'title': 'Password',
                    'type': 'string',
                    'format': 'password'
                },
                # {
                #     'name': consts.WMI_WORKING_DIR,
                #     'title': 'Working Directory',
                #     'type': 'string',
                #     'default': consts.WMI_WORKING_DIR_DEFAULT
                # },
                # {
                #     'name': consts.WMI_OUTPUT_FILE,
                #     'title': 'Temporary Output File Name',
                #     'type': 'string'
                # }
            ],
            'required': [consts.WSUS_HOST, consts.USER, consts.PASSWORD],
            'type': 'array',
        }

    @property
    def _use_wmi_smb_path(self):
        return os.path.abspath(os.path.join(os.path.dirname(__file__), self.config['paths']['wmi_smb_path']))

    @property
    def _python_27_path(self):
        return self.config['paths']['python_27_path']

    def _parse_date(self, date_str):
        try:
            date_match = self._date_regex.findall(date_str)[0]
            date_int = int(date_match)
            if date_int > 0:
                return parse_date(date_int)
            return None
        except Exception as e:
            logger.warning(f'Failed to parse date {date_str}: {str(e)}')
            return None

    # pylint: disable=too-many-branches, too-many-statements, too-many-locals, too-many-nested-blocks
    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            try:
                device = self._new_device_adapter()
                device.wsus_server = device_raw.get('ParentServerId')
                device_id = device_raw.get('Id')
                if device_id is None:
                    logger.warning(f'Bad device with no ID {device_raw}')
                    continue
                device.id = str(device_id) + '_' + (device_raw.get('FullDomainName') or '')
                device.name = device_raw.get('FullDomainName')
                try:
                    if device_raw.get('IPAddress'):
                        # logger.info(f'XXXX IPAddress: {device_raw.get("IPAddress")}')
                        if device_raw.get('IPAddress').get('Address'):
                            ip_obj = ipaddress.ip_address(device_raw.get('IPAddress').get('Address'))
                            # logger.info(f'XXXX Got IP: {device_raw.get("IPAddress").get("Address")}')
                            device.add_nic(ips=[str(ip_obj)])
                except Exception as e:
                    logger.warning(f'Failed to parse IP info: {str(e)}')
                try:
                    domain_parts = device_raw.get('FullDomainName', '').split('.')
                    device.hostname = domain_parts[0]
                    device.domain = '.'.join(domain_parts[1:])
                except Exception:
                    message = f'Failed to parse device domain from {device_raw.get("FullDomainName")}!'
                    logger.exception(message)
                device.device_model = device_raw.get('Model')
                device.device_manufacturer = (device_raw.get('Make'))

                device.role = device_raw.get('ComputerRole')
                last_reported_status_time = self._parse_date(device_raw.get('LastReportedStatusTime'))
                device.last_reported_status_time = last_reported_status_time
                device.last_sync_result = device_raw.get('LastSyncResult')
                last_sync_time = self._parse_date(device_raw.get('LastSyncTime'))
                device.last_sync_time = last_sync_time
                last_reported_inventory_time = self._parse_date(device_raw.get('LastReportedInventoryTime'))
                device.last_reported_inventory_time = last_reported_inventory_time
                if last_reported_inventory_time and last_sync_time and last_reported_status_time:
                    device.last_seen = max(last_sync_time, last_reported_inventory_time, last_reported_status_time)
                else:
                    device.last_seen = last_sync_time or last_reported_inventory_time or last_reported_status_time
                device.add_agent_version(agent=AGENT_NAMES.wsus,
                                         version=device_raw.get('ClientVersion'))
                try:
                    bitness = device_raw.get('OSArchitecture')
                    device.os = DeviceAdapterOS()
                    if bitness:
                        device.os.bitness = 32 if '32' in bitness else 64
                    device.os.type = 'Windows'
                    device.os.build = device_raw.get('OSBuildNumber')
                    device.os.major = device_raw.get('OSMajorVersion')
                    device.os.minor = device_raw.get('OSMinorVersion')
                    device.os.sp = device_raw.get('OSServicePackMajorNumber')
                except Exception:
                    logger.exception(f'Prolbem with os for {device_raw}')
                device.bios_version = device_raw.get('BiosInfo', {}).get('Version')

                try:
                    group_ids = device_raw.get('RequestedTargetGroupNames')
                    if not isinstance(group_ids, list):
                        group_ids = []
                    for group_id in group_ids:
                        try:
                            device.groups.append(group_id)
                        except Exception:
                            logger.exception(f'Problem with group ID {group_id}')
                except Exception:
                    logger.exception(f'Problem getting groups')
                device.set_raw(device_raw)
                yield device
            except Exception:
                logger.exception(f'Problem with device: {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent]
