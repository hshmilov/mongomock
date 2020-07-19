import datetime
import logging
import ipaddress
import chardet

from axonius.adapter_base import AdapterProperty
from axonius.scanner_adapter_base import ScannerAdapterBase
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.fields import Field, ListField
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from axonius.utils.datetime import parse_date
from axonius.utils.parsing import make_dict_from_csv
from axonius.smart_json_class import SmartJsonClass
from bitsight_adapter.connection import BitsightConnection
from bitsight_adapter.client_id import get_client_id
from bitsight_adapter.consts import DEFAULT_DOMAIN


logger = logging.getLogger(f'axonius.{__name__}')


# pylint: disable=too-many-instance-attributes
class DeviceObservation(SmartJsonClass):
    id = Field(str, 'Observation ID')
    last_seen = Field(datetime.datetime, 'Last Seen')
    first_seen = Field(datetime.datetime, 'First Seen')
    os_str = Field(str, 'OS')
    risk_type = Field(str, 'Risk Type')
    category = Field(str, 'Category')
    subcategory = Field(str, 'Subcategory')
    grade = Field(str, 'Grade')
    grade_explanation = Field(str, 'Grade Explanation')
    user_agent = Field(str, 'User Agent')
    event_date = Field(datetime.datetime, 'Event Date')
    description = Field(str, 'Description')
    observation_type = Field(str, 'Device Type')
    issues = ListField(str, 'Issues')


class BitsightAdapter(ScannerAdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        country = Field(str, 'Country')
        attributed_to = Field(str, 'Attributed To')
        as_number = Field(str, 'AS Number')
        source = Field(str, 'Source')
        observations = ListField(DeviceObservation, 'Observations')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'))

    @staticmethod
    def get_connection(client_config):
        connection = BitsightConnection(domain=client_config['domain'],
                                        verify_ssl=client_config['verify_ssl'],
                                        https_proxy=client_config.get('https_proxy'),
                                        proxy_username=client_config.get('proxy_username'),
                                        proxy_password=client_config.get('proxy_password'),
                                        apikey=client_config['apikey'])
        with connection:
            pass
        return connection

    def _connect_client(self, client_config):
        try:
            connection = self.get_connection(client_config)
            cidr_csv_data = None
            try:
                csv_data_bytes = self._grab_file_contents(client_config['cidr_csv'])
                encoding = chardet.detect(csv_data_bytes)['encoding']  # detect decoding automatically
                encoding = encoding or 'utf-8'
                csv_data = csv_data_bytes.decode(encoding)
                cidr_csv_data = make_dict_from_csv(csv_data)
            except Exception:
                pass
            return connection, cidr_csv_data
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
        connection, cidr_csv_data = client_data
        yield cidr_csv_data, 'cidr'
        with connection:
            for device_raw in connection.get_device_list():
                yield device_raw, 'device_raw'

    @staticmethod
    def _clients_schema():
        """
        The schema BitsightAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'BitSight Domain',
                    'type': 'string',
                    'default': DEFAULT_DOMAIN
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
                },
                {
                    'name': 'proxy_username',
                    'title': 'HTTPS Proxy Username',
                    'type': 'string'
                },
                {
                    'name': 'proxy_password',
                    'title': 'HTTPS Proxy Password',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': 'cidr_csv',
                    'title': 'CIDR Data CSV File',
                    'type': 'file'
                }
            ],
            'required': [
                'domain',
                'apikey',
                'verify_ssl'
            ],
            'type': 'array'
        }

    @staticmethod
    def _create_observation(observation_raw):
        try:
            observation = DeviceObservation()
            device_id = observation_raw.get('observation_id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {observation_raw}')
                return None
            observation.id = device_id
            observation.risk_type = observation_raw.get('risk_type')
            event_date = parse_date(observation_raw.get('event_date'))
            observation.event_date = event_date
            observation.last_seen = event_date
            observation_details = observation_raw.get('details')
            if observation_details and isinstance(observation_details, dict):
                observation.category = observation_details.get('category')
                observation.description = observation_details.get('description')
                observation.grade = observation_details.get('grade')
                observation.subcategory = observation_details.get('subcategory')
                observation.user_agent = observation_details.get('user_agent')
                grade_explanation = observation_details.get('grade_explanation')
                if isinstance(grade_explanation, dict):
                    observation.grade_explanation = grade_explanation.get('type')
                observation_occurrences = observation_details.get('occurrences')
                if observation_occurrences and isinstance(observation_occurrences, dict):
                    observation.first_seen = parse_date(observation_occurrences.get('first_seen'))
                    # This is better the event date for last seen
                    observation.last_seen = parse_date(observation_occurrences.get('last_seen'))
                observation_tags = observation_details.get('tags')
                if observation_tags and isinstance(observation_tags, dict):
                    observation.os_str = observation_tags.get('OS family')
                    observation.observation_type = observation_tags.get('type')
                issues = observation_details.get('issues')
                if isinstance(issues, list):
                    observation.issues = issues

            observation_forensics = observation_raw.get('forensics')
            if observation_forensics and isinstance(observation_forensics, dict):
                if observation_forensics.get('host_ip'):
                    ip = observation_forensics.get('host_ip')
                    port = observation_forensics.get('host_port')
                    return ip, port, observation.last_seen, observation, observation_raw
            return None
        except Exception:
            logger.exception(f'Problem with fetching Bitsight Device for {observation_raw}')
            return None

    # pylint: disable=too-many-branches, too-many-statements, too-many-locals, too-many-nested-blocks
    def _parse_raw_data(self, devices_raw_data):
        ips_observations_dict = dict()
        cidr_csv_data = []
        for device_raw, data_type in devices_raw_data:
            if data_type == 'cidr':
                cidr_csv_data = list(device_raw) if device_raw else []
                continue
            try:
                observation_value = self._create_observation(device_raw)
                if observation_value:
                    ip, port, last_seen, observation, observation_raw = observation_value
                    if ip not in ips_observations_dict:
                        ips_observations_dict[ip] = dict()
                    if port not in ips_observations_dict[ip]:
                        ips_observations_dict[ip][port] = [last_seen, observation, observation_raw]
                    if last_seen > ips_observations_dict[ip][port][0]:
                        ips_observations_dict[ip][port] = [last_seen, observation, observation_raw]
            except Exception:
                logger.exception(f'Problem post proccessing observation {device_raw}')
        for ip, port_observations in ips_observations_dict.items():
            try:
                device = self._new_device_adapter()
                raw_data = dict()
                last_seen_ip = None
                for port, port_values in port_observations.items():
                    try:
                        last_seen, observation, observation_raw = port_values
                        if not last_seen_ip or last_seen > last_seen_ip:
                            last_seen_ip = last_seen
                        device.add_open_port(protocol='TCP', port_id=port)
                        device.add_nic(ips=[ip])
                        device.observations.append(observation)
                        raw_data[port] = observation_raw
                        try:
                            device.figure_os(observation.os_str)
                        except Exception:
                            # No log needed
                            pass
                    except Exception:
                        logger.exception(f'Problem with port data {port}')
                device.last_seen = last_seen_ip
                device.id = ip
                try:
                    for cidr_data in cidr_csv_data:
                        try:
                            cidr_block = cidr_data.get('CIDR Block')
                            if '/' not in cidr_block:
                                cidr_block += '/32'
                            if ipaddress.ip_address(ip) in ipaddress.ip_network(cidr_block):
                                device.country = cidr_data.get('Country')
                                device.attributed_to = cidr_data.get('Attributed To')
                                device.source = cidr_data.get('Source')
                                device.as_number = cidr_data.get('AS Number')
                                break
                        except Exception:
                            logger.debug(f'Problem with cidr data {cidr_data}')
                except Exception:
                    pass
                device.set_raw(raw_data)
                yield device
            except Exception:
                logger.exception(f'Problem with IP {ip}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Network]
