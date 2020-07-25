import logging
import os
from datetime import datetime

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field, ListField
from axonius.mixins.configurable import Configurable
from axonius.utils.files import get_local_config_file
from axonius.clients.wmi_query import consts
from wmi_adapter.client_id import get_client_id
from wmi_adapter.consts import DEFAULT_POOL_SIZE
from wmi_adapter.connection import WmiConnection
from wmi_adapter.execution import WmiExecutionMixIn

logger = logging.getLogger(f'axonius.{__name__}')


class WmiAdapter(WmiExecutionMixIn, AdapterBase, Configurable):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        wmi_adapter_last_success_execution = Field(datetime, 'Last WMI Success')
        wmi_adapter_does_answer_to_ping = Field(bool, 'Did answer to ping')
        wmi_adapter_last_time_answered_to_ping = Field(datetime, 'Last time answered to ping')
        pm_last_execution_success = Field(datetime, 'Last PM Info Success')

        ad_bad_config_no_lm_hash = Field(int, 'Bad Config - No LMHash')
        ad_bad_config_force_guest = Field(int, 'Bad Config - Force Guest')
        ad_bad_config_authentication_packages = ListField(str, 'Bad Config - Authentication Packages')
        ad_bad_config_lm_compatibility_level = Field(int, 'Bad Config - Compatibility Level')
        ad_bad_config_disabled_domain_creds = Field(int, 'Bad Config - Disabled Domain Creds')
        ad_bad_config_secure_boot = Field(int, 'Bad Config - Secure Boot')
        reg_key_not_exists = ListField(str, 'Validated Registry Keys - Not Existing')
        reg_key_exists = ListField(str, 'Validated Registry Keys - Existing')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @property
    def _use_wmi_smb_path(self):
        return os.path.abspath(os.path.join(os.path.dirname(__file__), self.config['paths']['wmi_smb_path']))

    @property
    def _python_27_path(self):
        return self.config['paths']['python_27_path']

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return WmiConnection.test_reachability(client_config.get(consts.HOSTNAMES),
                                               dns_servers=client_config.get(consts.DNS_SERVERS))

    def _connect_client(self, client_config):
        if not WmiConnection.test_reachability(client_config[consts.HOSTNAMES]):
            message = 'Error connecting to {0}, reason: Connection Refused'.format(
                client_config.get(consts.HOSTNAMES))
            logger.exception(message)
            raise ClientConnectionException(message)
        return WmiConnection(targets=client_config[consts.HOSTNAMES],
                             username=client_config[consts.USERNAME],
                             password=client_config[consts.PASSWORD],
                             dns_servers=client_config.get(consts.DNS_SERVERS),
                             python27_path=self._python_27_path,
                             wmi_smb_path=self._use_wmi_smb_path,
                             pool_size=self._pool_size)

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
        The schema WmiAdapter expects from configs
        :return: JSON scheme
        """
        return consts.ADAPTER_SCHEMA

    def _create_device(self, device_raw) -> DeviceAdapter:
        """
        Parse wmi results for each subplugin
        :param device_raw: subplugins results
        :return: a new DeviceAdapter
        """
        try:
            device = self._new_device_adapter()
            subplugins_objects, dev_response = device_raw
            queries_response_index = 0
            if isinstance(dev_response, Exception):
                raise ValueError(f'Bad wmi response: {dev_response}')
            for subplugin in subplugins_objects:
                try:
                    subplugin_num_queries = len(subplugin.get_wmi_smb_commands())
                    subplugin_result = dev_response[queries_response_index:
                                                    queries_response_index + subplugin_num_queries]
                    queries_response_index = queries_response_index + subplugin_num_queries
                    parse_status = subplugin.handle_result(self, subplugin_result, device)
                    if not parse_status:
                        logger.error(f'Error parsing plugin {subplugin.__class__.__name__}')
                except Exception:
                    logger.exception(f'Error parsing plugin {subplugin.__class__.__name__}')
            if not device.does_field_exist('bios_serial') and not device.does_field_exist('hostname'):
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            bios_serial = device.bios_serial if device.does_field_exist('bios_serial') else ''
            device_hostname = device.hostname if device.does_field_exist('hostname') else ''
            device.id = f'{bios_serial}_{device_hostname}'.replace(' ', '_')
            device.set_raw({'product': dev_response})
            return device
        except Exception:
            logger.exception(f'Problem with fetching Wmi Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        # AUTOADAPTER - check if you need to add other properties'
        return [AdapterProperty.Assets]

    @classmethod
    def _db_config_schema(cls) -> dict:
        items = [
            {'name': 'pool_size',
             'title': 'Number of parallel connections',
             'type': 'integer',
             'default': DEFAULT_POOL_SIZE}
        ]
        return {
            'items': items,
            'required': ['pool_size'],
            'pretty_name': 'WMI Configuration',
            'type': 'array',
        }

    @classmethod
    def _db_config_default(cls):
        return {'pool_size': DEFAULT_POOL_SIZE}

    def _on_config_update(self, config):
        self._pool_size = config['pool_size'] or DEFAULT_POOL_SIZE
