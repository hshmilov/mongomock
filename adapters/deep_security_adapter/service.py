import ipaddress
import logging
import sys

from dsp3.models.manager import Manager

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field
from axonius.utils.files import get_local_config_file
from deep_security_adapter import consts

logger = logging.getLogger(f'axonius.{__name__}')


def raise_not_exit(msg=''):
    raise Exception(msg)


class DeepSecurityAdapter(AdapterBase):

    class MyDeviceAdapter(DeviceAdapter):
        agent_version = Field(str, 'Agent Version')
        state = Field(str, 'Device running state')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    def _get_client_id(self, client_config):
        return (client_config.get('domain') or '') + (client_config.get('tenant') or '') + client_config['username']

    def _test_reachability(self, client_config):
        raise NotImplementedError()

    @staticmethod
    def __create_manager_from_config(client_config):
        # In case of an error dsp3 calls to exit(). We have to change this to an exception
        exit_func = sys.exit
        try:
            sys.exit = raise_not_exit
            if client_config.get('domain'):
                dsm = Manager(username=client_config['username'],
                              password=client_config['password'],
                              host=client_config['domain'],
                              port=client_config.get('port') or consts.DEFAULT_PORT,
                              )
            else:
                dsm = Manager(username=client_config['username'],
                              password=client_config['password'],
                              tenant=client_config.get('tenant'),
                              verify_ssl=client_config.get('verify_ssl') or False)
            return dsm
        finally:
            sys.exit = exit_func

    def _connect_client(self, client_config):
        try:
            dsm = self.__create_manager_from_config(client_config)
            dsm.end_session()
            return client_config
        except Exception as e:
            reason = str(e)
            if not reason:
                reason = 'Login Failed'
            message = 'Error connecting to client , reason: {0}'.format(reason)
            logger.exception(message)
            raise ClientConnectionException(message)

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific DeepSecurity domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a DeepSecurity connection

        :return: A json with all the attributes returned from the DeepSecurity Server
        """
        dsm = self.__create_manager_from_config(client_data)
        devices = dsm.host_retrieve_all()
        dsm.end_session()
        return devices

    def _clients_schema(self):
        """
        The schema DeepSecurityAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'On-Premise DeepSecurity Domain',
                    'type': 'string'
                },                {
                    'name': 'port',
                    'title': 'Port',
                    'type': 'string'
                },
                {
                    'name': 'tenant',
                    'title': 'Tenant ID',
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
                'username',
                'password',
            ],
            'type': 'array'
        }

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            try:
                device = self._new_device_adapter()
                device_raw_dict = device_raw.__dict__
                device_raw = device_raw_dict.copy()
                for key in device_raw_dict:
                    if '__' in key:
                        del device_raw[key]
                device_id = device_raw.get('ID')
                hostname_or_ip = device_raw.get('name')
                if not device_id:
                    logger.warning(f'Bad device with no ID {device_raw}')
                    continue
                device.id = str(device_id) + '_' + (hostname_or_ip or '')
                device.name = device_raw.get('displayName')
                try:
                    ip = str(ipaddress.ip_address(hostname_or_ip))
                    device.add_nic(None, [ip])
                except Exception:
                    device.hostname = hostname_or_ip
                device.description = device_raw.get('description')
                device.figure_os(device_raw.get('platform'))
                device.set_raw(device_raw)
                yield device
            except Exception:
                logger.exception(f'Problem with fetching Device {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Endpoint_Protection_Platform, AdapterProperty.Agent, AdapterProperty.Manager]
