import datetime
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from axonius.fields import Field
from axonius.utils.parsing import parse_date
from foreman_adapter.connection import ForemanConnection
from foreman_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class ForemanAdapter(AdapterBase):
    # pylint: disable=R0902
    class MyDeviceAdapter(DeviceAdapter):
        environment_name = Field(str, 'Environment Name')
        domain_name = Field(str, 'Domain Name')
        provision_method = Field(str, 'Provision Method')
        organization_name = Field(str, 'Organization Name')
        puppet_status = Field(int, 'Puppet Status')
        model_name = Field(str, 'Model Name')
        location_name = Field(str, 'Location Name')
        global_status_label = Field(str, 'Global Status Label')
        updated_at = Field(datetime.datetime, 'Updated At')
        created_at = Field(datetime.datetime, 'Created At')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'))

    @staticmethod
    def _connect_client(client_config):
        try:
            with ForemanConnection(domain=client_config['domain'], verify_ssl=client_config['verify_ssl'],
                                   username=client_config['username'], password=client_config['password'],
                                   ) as connection:
                return connection
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
        The schema ForemanAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Foreman Domain',
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
                device = self._new_device_adapter()
                device_id = device_raw.get('id')
                if device_id is None:
                    logger.warning(f'Bad device with no id {device_raw}')
                    continue
                device.id = str(device_id) + '_' + (device_raw.get('name') or '')
                device.hostname = device_raw.get('name')

                try:
                    mac = device_raw.get('mac')
                    if not mac:
                        mac = None
                    ip = device_raw.get('ip')
                    if not isinstance(ip, str):
                        ip = None
                    else:
                        ip = ip.split(',')
                    if mac or ip:
                        device.add_nic(mac, ip)
                except Exception:
                    logger.exception(f'Problem adding nic to {device_raw}')

                try:
                    device.last_seen = parse_date(device_raw.get('last_report'))
                except Exception:
                    logger.exception(f'Problem getting last seen for {device_raw}')
                try:
                    device.created_at = parse_date(device_raw.get('created_at'))
                except Exception:
                    logger.exception(f'Problem getting created at from {device_raw}')
                try:
                    device.updated_at = parse_date(device_raw.get('updated_at'))
                except Exception:
                    logger.exception(f'Problem getting updated at from {device_raw}')
                device.global_status_label = device_raw.get('global_status_label')
                device.location_name = device_raw.get('location_name')
                device.model_name = device_raw.get('model_name')
                device.puppet_status = device_raw.get('puppet_status')
                device.organization_name = device_raw.get('organization_name')
                try:
                    device.figure_os(device_raw.get('operatingsystem_name'))
                except Exception:
                    logger.exception(f'Problem getting os for {device_raw}')
                device.domain_name = device_raw.get('domain_name')
                device.provision_method = device_raw.get('provision_method')
                device.environment_name = device_raw.get('environment_name')
                device.set_raw(device_raw)
                yield device
            except Exception:
                logger.exception(f'Problem with fetching Foreman Device for {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent]
