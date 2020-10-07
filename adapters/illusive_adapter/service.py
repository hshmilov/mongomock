import datetime
import ipaddress
import logging

from axonius.adapter_base import AdapterProperty
from axonius.scanner_adapter_base import ScannerAdapterBase
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from axonius.devices.device_adapter import DeviceAdapter, AGENT_NAMES
from axonius.fields import Field
from axonius.utils.parsing import convert_ldap_searchpath_to_domain_name, is_domain_valid
from axonius.utils.files import get_local_config_file
from axonius.utils.datetime import parse_date
from illusive_adapter.connection import IllusiveConnection

logger = logging.getLogger(f'axonius.{__name__}')


class IllusiveAdapter(ScannerAdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        policy_name = Field(str, 'Policy Name')
        group_name = Field(str, 'Group Name')
        is_healthy = Field(bool, 'Is Healthy')
        last_execution_type = Field(str, 'Last Execution Type')
        ghost = Field(bool, 'Ghost')
        last_deployment_method_type = Field(str, 'Last Deployment Method Type')
        last_logon = Field(datetime.datetime, 'Last Logon Time')
        machine_execution_unified_status = Field(str, 'Machine Execution Unified Status')

    def __init__(self):
        super().__init__(get_local_config_file(__file__))

    def _get_client_id(self, client_config):
        return client_config['domain']

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'),
                                                https_proxy=client_config.get('https_proxy'))

    def _connect_client(self, client_config):
        try:
            connection = IllusiveConnection(domain=client_config['domain'],
                                            apikey=client_config['apikey'],
                                            verify_ssl=client_config.get('verify_ssl', False),
                                            https_proxy=client_config.get('https_proxy'))
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
        Get all devices from a specific Illusive domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a Illusive connection

        :return: A json with all the attributes returned from the Illusive Server
        """
        with client_data:
            yield from client_data.get_device_list()

    def _clients_schema(self):
        """
        The schema IllusiveAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Illusive Domain',
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

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            try:
                device = self._new_device_adapter()
                device_id = device_raw.get('machineId')
                if not device_id:
                    logger.warning(f'No id of device {device_raw}')
                    continue
                device.id = device_id + (device_raw.get('machineName') or '')
                hostname_or_ip = device_raw.get('machineName')
                try:
                    ip = str(ipaddress.ip_address(hostname_or_ip))
                    device.add_nic(None, [ip])
                except Exception:
                    device.hostname = hostname_or_ip
                domain = None
                try:
                    domain = convert_ldap_searchpath_to_domain_name(device_raw.get('distinguishedName'))
                except Exception:
                    pass
                if is_domain_valid(domain):
                    device.domain = domain
                device.group_name = device_raw.get('groupName')
                device.add_agent_version(agent=AGENT_NAMES.illusive,
                                         version=device_raw.get('agentVersion'))
                device.policy_name = device_raw.get('policyName')
                device.last_seen = parse_date(device_raw.get('machineLastExecutionPhaseFinishDate'))
                device.last_logon = parse_date(device_raw.get('lastLogonTime'))
                device.last_deployment_method_type = device_raw.get('lastDeploymentMethodType')
                try:
                    device.figure_os((device_raw.get('operatingSystemName') or '') +
                                     (device_raw.get('operatingSystemVersion') or ''))
                except Exception:
                    logger.exception(f'Probelm getting OS for {device_raw}')
                if isinstance(device_raw.get('loggedInUserName'), str) and device_raw.get('loggedInUserName') \
                        and 'Unable to find' not in device_raw.get('loggedInUserName'):
                    device.last_used_users = device_raw.get('loggedInUserName').split(',')
                if isinstance(device_raw.get('isHealthy'), bool):
                    device.is_healthy = device_raw.get('isHealthy')
                if isinstance(device_raw.get('ghost'), bool):
                    device.ghost = device_raw.get('ghost')
                device.last_execution_type = device_raw.get('lastExecutionType')
                # pylint: disable=invalid-name
                device.machine_execution_unified_status = device_raw.get('machineExecutionUnifiedStatus')
                device.set_raw(device_raw)
                yield device
            except Exception:
                logger.exception(f'Problem with fetching Illusive Device {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent, AdapterProperty.Manager]
