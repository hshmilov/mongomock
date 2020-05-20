import logging
import os

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.utils.files import get_local_config_file
from failover_cluster_adapter.client_id import get_client_id
from failover_cluster_adapter.connection import FailoverClusterConnection
from failover_cluster_adapter.structures import FailoverClusterDeviceInstance

logger = logging.getLogger(f'axonius.{__name__}')


class FailoverClusterAdapter(AdapterBase):
    class MyDeviceAdapter(FailoverClusterDeviceInstance):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__),
                         *args,
                         **kwargs)

    @property
    def _use_wmi_smb_path(self):
        return os.path.abspath(os.path.join(os.path.dirname(__file__),
                                            self.config['paths']['wmi_smb_path']))

    @property
    def _python_27_path(self):
        return self.config['paths']['python_27_path']

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'),
                                                https_proxy=client_config.get('https_proxy'))

    def get_connection(self, client_config):
        connection = FailoverClusterConnection(domain=client_config['domain'],
                                               username=client_config['username'],
                                               password=client_config['password'],
                                               wmi_util_path=self._use_wmi_smb_path,
                                               python_path=self._python_27_path,
                                               verify_ssl=client_config['verify_ssl'],
                                               https_proxy=client_config.get('https_proxy'),
                                               )
        with connection:
            pass
        return connection

    def _connect_client(self, client_config):
        try:
            return self.get_connection(client_config)
        except RESTException as e:
            message = f'Error connecting to client with domain ' \
                      f'{client_config.get("domain")}, reason: {str(e)}'
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
    def _clients_schema() -> dict:
        """
        The schema FailoverClusterAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Failover Cluster Domain',
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
                'domain',
                'username',
                'password',
                'verify_ssl'
            ],
            'type': 'array'
        }

    @staticmethod
    def _fill_failover_cluster_device_fields(device_raw: dict,
                                             device: MyDeviceAdapter):
        try:
            device.cluster_node_name = device_raw.get('Name') or device_raw.get('NodeName')
            device.cluster_node_id = device_raw.get('ID') or device_raw.get('NodeId')
            device.cluster_node_state = device_raw.get('State') or device_raw.get('NodeState')
        except Exception:
            logger.exception(f'Failed to create device {device_raw}')

    def _create_device(self, device_raw: dict, device: MyDeviceAdapter):
        try:
            device_id = device_raw.get('ID') or device_raw.get('NodeId')
            if not device_id:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = str(device_id) + '_' + (device_raw.get('domain') or '')

            device.name = device_raw.get('Name') or device_raw.get('NodeName')

            self._fill_failover_cluster_device_fields(device_raw, device)

            device.set_raw(device_raw)

            return device
        except Exception:
            logger.exception(f'Problem fetching FailoverCluster Device: '
                             f'{device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        """
        Gets raw data and yields Device objects.
        :param devices_raw_data: the raw data we get.
        """
        # split the cluster name from the raw data
        raw_data, cluster_name = devices_raw_data

        if isinstance(raw_data, list):
            for device_raw in raw_data:
                if not device_raw:
                    continue
                try:
                    # noinspection PyTypeChecker
                    device = self._create_device(device_raw,
                                                 self._new_device_adapter())
                    if device:
                        device.cluster_name = cluster_name
                        yield device
                except Exception:
                    logger.exception(f'Problem fetching FailoverCluster Device: '
                                     f'{device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets, AdapterProperty.Manager]
