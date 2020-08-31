import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection, RESTException
from axonius.clients.ivanti_security_controls.connection import IvantiSecurityControlsConnection
from axonius.clients.ivanti_security_controls.consts import DEFAULT_API_PORT, EXTRA_POLICY_INFO
from axonius.devices.device_adapter import AGENT_NAMES
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import parse_bool_from_raw, int_or_none
from ivanti_security_controls_adapter.client_id import get_client_id
from ivanti_security_controls_adapter.structures import IvantiSecurityControlsDeviceInstance, Policy

logger = logging.getLogger(f'axonius.{__name__}')

# pylint: disable=logging-format-interpolation


class IvantiSecurityControlsAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(IvantiSecurityControlsDeviceInstance):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'),
                                                https_proxy=client_config.get('https_proxy'))

    @staticmethod
    def get_connection(client_config):
        connection = IvantiSecurityControlsConnection(domain=client_config.get('domain'),
                                                      port=client_config.get('port'),
                                                      verify_ssl=client_config.get('verify_ssl'),
                                                      https_proxy=client_config.get('https_proxy'),
                                                      proxy_username=client_config.get('proxy_username'),
                                                      proxy_password=client_config.get('proxy_password'),
                                                      username=client_config.get('username'),
                                                      password=client_config.get('password'))
        with connection:
            pass  # check that the connection credentials are valid
        return connection

    def _connect_client(self, client_config):
        try:
            return self.get_connection(client_config)
        except RESTException as e:
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                client_config.get('domain'), str(e))
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
    def _clients_schema():
        """
        The schema IvantiSecurityControlsAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Host Name or IP Address',
                    'type': 'string'
                },
                {
                    'name': 'port',
                    'title': 'Port',
                    'type': 'integer',
                    'default': DEFAULT_API_PORT
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
                },
                {
                    'name': 'proxy_username',
                    'title': 'HTTPS Proxy User Name',
                    'type': 'string'
                },
                {
                    'name': 'proxy_password',
                    'title': 'HTTPS Proxy Password',
                    'type': 'string',
                    'format': 'password'
                }
            ],
            'required': [
                'domain',
                'port',
                'username',
                'password',
                'verify_ssl'
            ],
            'type': 'array'
        }

    @staticmethod
    def _fill_ivanti_security_controls_device_fields(device_raw: dict, device: MyDeviceAdapter):
        try:
            device.listening = parse_bool_from_raw(device_raw.get('isListening'))
            device.assigned_policy_id = device_raw.get('assignedPolicyId')
            device.report_policy_id = device_raw.get('reportedPolicyId')
            device.status = device_raw.get('status')

            if isinstance(device_raw.get(EXTRA_POLICY_INFO), dict):
                policy_raw = device_raw.get(EXTRA_POLICY_INFO)
                policy = Policy()

                policy.id = policy_raw.get('id')
                policy.name = policy_raw.get('name')
                policy.cancel_operation = parse_bool_from_raw(policy_raw.get('allowCancelOperations'))
                policy.manual_operation = parse_bool_from_raw(policy_raw.get('allowManualOperations'))
                try:
                    policy.check_in = policy_raw.get('checkInOption')
                except Exception:
                    if policy_raw.get('checkInOption') is not None:
                        logger.error(f'Failed parsing {policy_raw.get("checkInOption")}')
                policy.days_check_in = int_or_none(policy_raw.get('daysCheckInIntervalDays'))
                policy.minutes_check_in = int_or_none(policy_raw.get('minutesCheckInIntervalMinutes'))
                policy.internet_proxy = policy_raw.get('internetProxyCredentialsId')
                policy.listen_port = int_or_none(policy_raw.get('listeningAgentPort'))

                device.policy = policy

        except Exception:
            logger.exception(f'Failed creating instance for device {device_raw}')

    def _create_device(self, device_raw: dict, device: MyDeviceAdapter):
        try:
            device_id = device_raw.get('agentId')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = str(device_id) + '_' + (device_raw.get('machineName') or '')

            device.domain = device_raw.get('domain')
            device.last_seen = parse_date(device_raw.get('lastCheckIn'))
            device.hostname = device_raw.get('machineName')
            device.add_agent_version(agent=AGENT_NAMES.ivanti_sc,
                                     version=device_raw.get('frameworkVersion'))

            port_id = int_or_none(device_raw.get('listeningPort'))
            device.add_open_port(port_id=port_id)

            ips = device_raw.get('lastKnownIPAddress') or []
            if isinstance(ips, str):
                ips = [ips]
            device.add_nic(ips=ips)

            self._fill_ivanti_security_controls_device_fields(device_raw, device)

            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching IvantiSecurityControls Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        """
        Gets raw data and yields Device objects.
        :param devices_raw_data: the raw data we get.
        :return:
        """
        for device_raw in devices_raw_data:
            if not device_raw:
                continue
            try:
                # noinspection PyTypeChecker
                device = self._create_device(device_raw, self._new_device_adapter())
                if device:
                    yield device
            except Exception:
                logger.exception(f'Problem with fetching IvantiSecurityControls Device for {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets, AdapterProperty.Agent]
