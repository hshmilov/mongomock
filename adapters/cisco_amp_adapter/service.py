import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.utils.datetime import parse_date
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.devices.device_adapter import DeviceAdapter, DeviceRunningState, AGENT_NAMES
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
        policy_name = Field(str, 'Policy Name')

    def __init__(self):
        super().__init__(get_local_config_file(__file__))

    # pylint: disable=R0201
    def _get_client_id(self, client_config):
        """
        :param client_config:
        :return: Client ID
        """
        return client_config[consts.CLIENT_ID]

    def _test_reachability(self, client_config):
        return RESTConnection.test_reachability(client_config.get(consts.DOMAIN),
                                                https_proxy=client_config.get('https_proxy'))

    def _connect_client(self, client_config):
        """
        :param client_config:
        :return: a connection to the CiscoAMPConnection class.
        """
        try:
            connection = CiscoAMPConnection(domain=client_config[consts.DOMAIN], apikey=client_config[consts.API_KEY],
                                            client_id=client_config[consts.CLIENT_ID],
                                            https_proxy=client_config.get('https_proxy'))

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
                },
                {
                    'name': 'https_proxy',
                    'title': 'HTTPS Proxy',
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

    # pylint: disable=R1702, R0912
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
                device.add_agent_version(agent=AGENT_NAMES.cisco_amp,
                                         version=raw_device_data.get('connector_version'))
                try:
                    os = raw_device_data.get('operating_system', '')
                    device.figure_os(os)
                except Exception:
                    logger.exception(f'Error configuring the OS for {raw_device_data}')

                device.external_ip = raw_device_data.get('external_ip')
                network_addresses = raw_device_data.get('network_addresses', [])
                try:
                    device.last_seen = parse_date(raw_device_data.get('last_seen'))
                except Exception:
                    logging.exception(f'Problem getting last seen for {raw_device_data}')
                try:
                    device.policy_name = (raw_device_data.get('policy') or {}).get('name')
                except Exception:
                    logging.exception(f'Problem getting policy for {raw_device_data}')
                if isinstance(network_addresses, list):
                    for entry in network_addresses:
                        try:
                            mac = entry.get('mac')
                            ip = entry.get('ip')
                            if ip:
                                ips = ip.split(',')
                            else:
                                ips = None
                            if ips or mac:
                                device.add_nic(mac=mac, ips=ips)
                        except Exception:
                            logger.exception(f'Incurred an error adding network address for {raw_device_data}')

                yield device
            except Exception:
                logger.exception(f'Got exception for raw_device_data: {raw_device_data}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Endpoint_Protection_Platform, AdapterProperty.Agent, AdapterProperty.Manager]
