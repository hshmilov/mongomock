import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.devices.device_adapter import DeviceAdapter, DeviceRunningState
from axonius.fields import Field
from axonius.utils.files import get_local_config_file
from cisco_amp_adapter import consts
from cisco_amp_adapter.connection import CiscoAMPConnection

logger = logging.getLogger(f'axonius.{__name__}')


class CiscoAmpAdapter(AdapterBase):
    def _parse_correlation_results(self, correlation_cmd_result, os_type):
        pass

    class MyDeviceAdapter(DeviceAdapter):
        connector_version = Field(str, 'Connector Version')
        external_ip = Field(str, 'External IP')

    def __init__(self):
        super().__init__(get_local_config_file(__file__))

    # pylint: disable=R0201
    def _get_client_id(self, client_config):
        """
        :param client_config:
        :return: Client ID
        """
        return client_config[consts.CLIENT_ID]

    def _connect_client(self, client_config):
        """
        :param client_config:
        :return: a connection to the CiscoAMPConnection class.
        """
        try:
            connection = CiscoAMPConnection(domain=client_config[consts.DOMAIN], apikey=client_config[consts.API_KEY],
                                            client_id=client_config[consts.CLIENT_ID])

            with connection:
                pass
            return connection
        except Exception as e:
            logger.error(f'Failed to connect to client {self._get_client_id(client_config)}')
            raise ClientConnectionException(str(e))

    def _query_devices_by_client(self, client_name, client_data):
        """
        Connect to the CiscoAMP adapter and retreive the list of all devices.
        :param **kwargs:
        :param client_data:
        :return: devices list.
        """
        with client_data:
            yield from client_data.get_device_list()

    # pylint: disable=R0201
    def _clients_schema(self):
        return {
            'items': [
                {
                    'name': consts.DOMAIN,
                    'title': 'Domain',
                    'type': 'string',
                    'default': consts.US_URL
                },
                {
                    'name': consts.CLIENT_ID,
                    'title': 'Client ID',
                    'type': 'string'
                },
                {
                    'name': consts.API_KEY,
                    'title': 'API Key',
                    'type': 'string'
                }
            ],
            'required': [
                consts.CLIENT_ID,
                consts.API_KEY,
                consts.DOMAIN
            ],
            'type': 'array'
        }

    def _parse_raw_data(self, devices_raw_data):
        """
        Parse through all of the relevant data from the v1/computers data
        :param raw_data: device list
        :return: Parsed relevant data
        """

        for raw_device_data in iter(devices_raw_data):
            try:
                device = self._new_device_adapter()

                guid = raw_device_data.get('connector_guid', '')
                if not guid:
                    logger.warning(f'No id for the device {raw_device_data}')
                    continue

                device.id = guid
                device.hostname = raw_device_data.get('hostname')
                device.set_raw(raw_device_data)

                if raw_device_data.get('active'):
                    device.power_state = DeviceRunningState.TurnedOn
                else:
                    device.power_state = DeviceRunningState.TurnedOff

                device.connector_version = raw_device_data.get('connector_version')
                try:
                    os = raw_device_data.get('operating_system', '')
                    device.figure_os(os)
                except Exception:
                    logger.exception(f'Error configuring the OS for {raw_device_data}')

                device.external_ip = raw_device_data.get('external_ip')
                network_addresses = raw_device_data.get('network_addresses', [])
                if isinstance(network_addresses, list):
                    for entry in network_addresses:
                        try:
                            mac = entry.get('mac', '')
                            ip = entry.get('ip') or ''
                            device.add_nic(mac=mac, ips=ip.split(','))
                        except Exception:
                            logger.exception(f'Incurred an error adding network address for {raw_device_data}')

                yield device
            except Exception:
                logger.exception(f'Got exception for raw_device_data: {raw_device_data}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Endpoint_Protection_Platform, AdapterProperty.Agent, AdapterProperty.Manager]
