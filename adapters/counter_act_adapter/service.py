import datetime
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field, ListField
from axonius.utils.files import get_local_config_file
from counter_act_adapter.connection import CounterActConnection
from counter_act_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class CounterActAdapter(AdapterBase):
    # pylint: disable=R0902
    class MyDeviceAdapter(DeviceAdapter):
        online_status = Field(str, 'Online Status')
        agent_version = Field(str, 'Agent Version')
        av_install = ListField(str, 'AV Installed')
        ad_disply_name = Field(str, 'AD Display Name')
        fingerprint = Field(str, 'Fingerprint')
        in_groups = ListField(str, 'In Groups')

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
            with CounterActConnection(domain=client_config['domain'], verify_ssl=client_config['verify_ssl'],
                                      username=client_config['username'], password=client_config['password'],
                                      https_proxy=client_config.get('https_proxy')) as connection:
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
        The schema CounterActAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'CounterAct Domain',
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

    # pylint: disable=R1702, R0912,R0915
    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            try:
                device = self._new_device_adapter()
                mac = device_raw.get('mac')
                if not mac:
                    mac = None
                ip = device_raw.get('ip')
                href = ((device_raw.get('_links') or {}).get('self') or {}).get('href')
                if not href:
                    logger.warning(f'Bad device with no id {device_raw}')
                    continue
                device.id = href + '_' + (mac or '') + '_' + (ip or '')
                ips = None
                if ip:
                    ips = [ip]
                if mac or ips:
                    device.add_nic(mac, ips)
                try:
                    fields_dict = ((device_raw.get('extra') or {}).get('host') or {}).get('fields')
                    if isinstance(fields_dict, dict):
                        for field_raw_name, field_raw_data in fields_dict.items():
                            try:
                                if isinstance(field_raw_data, dict) and field_raw_data.get('value') == 'None':
                                    field_raw_data['value'] = None
                                if field_raw_name == 'online':
                                    device.online_status = field_raw_data.get('value')
                                elif field_raw_name == 'openports':
                                    for field in field_raw_data or []:
                                        try:
                                            device.add_open_port(port_id=field.get('value'))
                                        except Exception:
                                            logger.exception(f'Failed to add open port')
                                elif field_raw_name == 'comp_application':
                                    for app_data_raw in field_raw_data:
                                        app_data = app_data_raw.get('value') or {}
                                        if str(app_data.get('app_name')) != 'None':
                                            device.add_installed_software(name=app_data.get('app_name'),
                                                                          version=app_data.get('app_version'))
                                elif field_raw_name == 'av_install':
                                    device.av_install = [field_raw.get('value') for field_raw in field_raw_data
                                                         if str(field_raw.get('value')) != 'None']
                                elif field_raw_name == 'agent_version':
                                    device.agent_version = field_raw_data.get('value')
                                elif field_raw_name == 'hostname':
                                    device.hostname = field_raw_data.get('value')
                                elif field_raw_name == 'dhcp_hostname':
                                    device.name = field_raw_data.get('value')
                                elif field_raw_name == 'os_classification':
                                    device.figure_os(field_raw_data.get('value'))
                                elif field_raw_name == 'vendor_classification':
                                    device.device_model_family = field_raw_data.get('value')
                                elif field_raw_name == 'vendor':
                                    device.device_manufacturer = field_raw_data.get('value')
                                elif field_raw_name == 'ad_displayname':
                                    device.ad_disply_name = field_raw_data.get('value')
                                elif field_raw_name == 'mac':
                                    try:
                                        device.last_seen = datetime.datetime.\
                                            fromtimestamp(field_raw_data.get('timestamp'))
                                    except Exception:
                                        logging.exception(f'Problem getting last seen for {device_raw}')
                                elif field_raw_name == 'fingerprint':
                                    device.fingerprint = field_raw_data.get('value')
                                elif field_raw_name == 'vendor':
                                    device.device_manufacturer = field_raw_data.get('value')
                                elif field_raw_name == 'in-group':
                                    if isinstance(field_raw_data, list):
                                        for group_info in field_raw_data:
                                            if isinstance(group_info, dict) and group_info.get('value'):
                                                device.in_groups.append(group_info.get('value'))
                            except Exception:
                                logger.exception(f'Problem with field {field_raw_name}')
                except Exception:
                    logger.exception(f'Problem with fields')
                device.set_raw(device_raw)
                yield device
            except Exception:
                logger.exception(f'Problem with fetching CounterAct Device for {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Network]
