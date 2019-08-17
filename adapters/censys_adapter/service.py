import logging
from hashlib import sha1

from axonius.adapter_base import AdapterProperty
from axonius.scanner_adapter_base import ScannerAdapterBase
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection, RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from axonius.utils.datetime import parse_date
from axonius.clients.censys.connection import CensysConnection
from axonius.clients.censys.consts import (ADAPTER_SCHEMA)
from axonius.smart_json_class import SmartJsonClass
from axonius.fields import Field, ListField
from censys_adapter.client_id import get_client_id
from censys_adapter.execution import CensysExecutionMixIn


logger = logging.getLogger(f'axonius.{__name__}')


class CensysLocation(SmartJsonClass):
    """
    A definition for a Censys location field
    """
    continent = Field(str, 'Continent')
    country = Field(str, 'Country')
    country_code = Field(str, 'Country Code')
    province = Field(str, 'Province')
    city = Field(str, 'City')
    postal_code = Field(str, 'Postal Code')
    longitude = Field(float, 'Longitude')
    latitude = Field(float, 'Latitude')
    registered_country = Field(str, 'Registered Country')
    registered_country_code = Field(str, 'Registered Country Code')
    timezone = Field(str, 'Time Zone')


class CensysAutonomousSystem(SmartJsonClass):
    """
    A definition for a Censys Autonomous System field
    """
    asn = Field(int, 'ASN')
    name = Field(str, 'Name')
    description = Field(str, 'Description')
    rir = Field(str, 'RIR')
    routed_prefix = Field(str, 'Routed Prefix')
    country_code = Field(str, 'Country Code')
    path = ListField(int, 'Path')


class CensysPort(SmartJsonClass):
    """
    A definition for a Censys Port (details) field
    """
    port = Field(int, 'Port')
    # protocol_raw = Field(str, 'Protocol')   # This will be implemented soon. We don't have much data on possibilities


class CensysAdapter(CensysExecutionMixIn, ScannerAdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        # pylint: disable=R0902
        protocols = ListField(str, 'Protocols')
        alexa_rank = Field(int, 'Alexa Rank')
        censys_tags = Field(str, 'Censys Tags')
        ports = ListField(CensysPort, 'Ports')
        location = Field(CensysLocation, 'Location')
        autonomous_system = Field(CensysAutonomousSystem, 'Autonomous System')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'))

    def _connect_client(self, client_config):
        try:
            # Credential check is done automatically via _connect in connection.py
            with CensysConnection(username=client_config['api_id'], password=client_config['api_secret'],
                                  domain_preferred=client_config.get('domain'),
                                  free_tier=not client_config.get('is_paid_tier'),
                                  search_type=client_config['search_type'],
                                  https_proxy=client_config.get('https_proxy')) as connection:

                # Ensure search type is valid
                if connection.search_type not in ['ipv4', 'websites']:
                    raise ClientConnectionException('Search Type must be one of "ipv4" or "websites"')

                # Ensure we have a search query present
                search_query = client_config['search_query']

                return connection, search_query
        except RESTException as e:
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                client_config['domain'], str(e))
            logger.exception(message)
            raise ClientConnectionException(message)

    @staticmethod
    def _query_devices_by_client(client_name, client_data):
        """
        Get all result details given a list of search results

        :param str client_name: The name of the client
        :param obj client_data: The data that represents a connection

        :return: A json with all the attributes returned from the server for all devices
        """
        connection, search_query = client_data
        with connection:
            yield from connection.get_device_list(search_query)

    @staticmethod
    def _clients_schema():
        """
        The schema CensysAdapter expects from configs

        :return: JSON schema
        """
        return ADAPTER_SCHEMA

    def _create_device(self, device_raw):
        try:
            device = self._new_device_adapter()

            # We don't know what type, so check the two possible
            # "primary key" values in the response, and create a
            # hash of both possible values to get an ID
            ipv4_ip = device_raw.get('ip')
            website_domain = device_raw.get('domain')

            # Handle case where there's no "primary key" present
            device_id = sha1(f'{ipv4_ip}{website_domain}'.encode('utf-8')).hexdigest()
            if device_id in [None, sha1(''.encode('utf-8')).hexdigest()]:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None

            device.id = device_id
            device.last_seen = parse_date(device_raw.get('updated_at'))
            device.censys_tags = device_raw.get('tags')
            device.protocols = device_raw.get('protocols')
            if device_raw.get('ports'):
                device.ports = list(CensysPort(port=p) for p in device_raw.get('ports'))

            for port_and_service in device_raw.get('protocols') or []:
                try:
                    split_info = port_and_service.split('/', 1)
                    device.add_open_port(port_id=int(split_info[0]), service_name=split_info[1])
                except Exception:
                    logger.exception(f'Failed to add port for device {str(device_raw.get("protocols"))}')

            if ipv4_ip:
                device.name = ipv4_ip
                device.add_nic(ips=[ipv4_ip])
                device.add_public_ip(ipv4_ip)
                device.location = CensysLocation(
                    continent=device_raw.get('location').get('continent'),
                    country=device_raw.get('location').get('country'),
                    country_code=device_raw.get('location').get('country_code'),
                    province=device_raw.get('location').get('province'),
                    city=device_raw.get('location').get('city'),
                    postal_code=device_raw.get('location').get('postal_code'),
                    longitude=device_raw.get('location').get('longitude'),
                    latitude=device_raw.get('location').get('latitude'),
                    registered_country=device_raw.get('location').get('registered_country'),
                    registered_country_code=device_raw.get('location').get('registered_country_code'),
                    timezone=device_raw.get('location').get('timezone')
                ) if device_raw.get('location') else None
                device.autonomous_system = CensysAutonomousSystem(
                    asn=device_raw.get('autonomous_system').get('asn'),
                    name=device_raw.get('autonomous_system').get('name'),
                    description=device_raw.get('autonomous_system').get('description'),
                    rir=device_raw.get('autonomous_system').get('rir'),
                    routed_prefix=device_raw.get('autonomous_system').get('routed_prefix'),
                    country_code=device_raw.get('autonomous_system').get('country_code'),
                    path=device_raw.get('autonomous_system').get('path')
                ) if device_raw.get('autonomous_system') else None
            elif website_domain:
                device.name = website_domain
                device.hostname = website_domain
                device.alexa_rank = device_raw.get('alexa_rank')
            else:
                logger.exception(f'Problem with fetching Censys Device for {device_raw}, no primary key present.')
                return None
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Censys Device for {device_raw}, unknown error.')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw)
            if device:
                yield device

    def outside_reason_to_live(self) -> bool:
        """
        This adapter might be called from outside, let it live
        """
        return True

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Network]
