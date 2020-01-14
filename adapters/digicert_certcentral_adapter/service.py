import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import parse_date
from digicert_certcentral_adapter.client_id import get_client_id
from digicert_certcentral_adapter.connection import DigicertCertcentralConnection
from digicert_certcentral_adapter.consts import REST_PATH_DISCOVERY_API, ENUM_UNKNOWN_VALUE_LOG_PREFIX, \
    ENUM_CERT_RATING, ENUM_CERT_STATUS, ENUM_CERT_VULNS, ENUM_BLACKLISTED_VALUE_LOG_PREFIX
from digicert_certcentral_adapter.structures import DigicertScan, Endpoint, DigicertScannedCertificate
from digicert_certcentral_adapter.utils import partition

logger = logging.getLogger(f'axonius.{__name__}')


class DigicertCertcentralAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        endpoint = Field(Endpoint, 'Endpoint Info')
        scan = Field(DigicertScan, 'Digicert Scan Info')
        is_cert_present = Field(bool, 'Endpoint certificate presence',
                                description='Whether or not certificate is installed at the endpoint.')
        certificate = Field(DigicertScannedCertificate, 'Endpoint Certificate')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(REST_PATH_DISCOVERY_API)

    @staticmethod
    def get_connection(client_config):
        connection = DigicertCertcentralConnection(api_key=client_config['api_key'],
                                                   account_id=client_config['account_id'],
                                                   division_ids=client_config.get('division_ids'),
                                                   verify_ssl=client_config['verify_ssl'],
                                                   https_proxy=client_config.get('https_proxy'))
        with connection:
            pass
        return connection

    def _connect_client(self, client_config):
        try:
            return self.get_connection(client_config)
        except RESTException as e:
            message = f'Error connecting to client with reason: {str(e)}'
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
        The schema DigicertCertcentralAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'api_key',
                    'title': 'API Key',
                    'type': 'string',
                },
                {
                    'name': 'account_id',
                    'title': 'Account ID',
                    'type': 'string',
                },
                {
                    'name': 'division_ids',
                    'title': 'Division IDs',
                    'type': 'array',
                    'items': {
                        'type': 'string'
                    },
                },
                {
                    'name': 'verify_ssl',
                    'title': 'Verify SSL',
                    'type': 'bool',
                },
                {
                    'name': 'https_proxy',
                    'title': 'HTTPS Proxy',
                    'type': 'string',
                }
            ],
            'required': [
                'api_key',
                'account_id',
                'verify_ssl'
            ],
            'type': 'array'
        }

    @staticmethod
    def _parse_enum(field_name: str, device_raw: dict, whitelist: list):
        values_list = device_raw.get(field_name)
        # remove empty values
        if not values_list:
            return None

        # split and strip comma separated string (implicitly non empty) values
        if isinstance(values_list, str):
            values_list = list(map(str.strip, values_list.split(',')))

        # log invalid values and remove
        if not isinstance(values_list, list):
            logger.warning(f'{ENUM_UNKNOWN_VALUE_LOG_PREFIX}'
                           f' Unexpected values retrieved for field "{field_name}" in raw: {device_raw}')
            return None

        # filter out blacklisted values
        blacklisted, whitelisted = list(map(list, partition(whitelist.__contains__, values_list)))
        if blacklisted:
            logger.warning(f'{ENUM_BLACKLISTED_VALUE_LOG_PREFIX}'
                           f' Unknown "{field_name}" value encountered "{",".join(blacklisted)}"'
                           f' for whitelist {whitelist} in raw: {device_raw}.')
        return whitelisted

    @staticmethod
    def _parse_endpoint(device_raw):
        try:
            endpoint = Endpoint()
            endpoint.server_id = device_raw.get('serverId')
            endpoint.hardware_type = device_raw.get('deviceType')
            endpoint.server_software = device_raw.get('serverName')
            endpoint.server_version = device_raw.get('serverVersion')
            endpoint.domain_name = device_raw.get('domainName')
            endpoint.port_status = device_raw.get('portStatus')
            endpoint.security_rating = device_raw.get('serverSecurityRating')
            return endpoint
        except Exception:
            logger.exception(f'Failed to parse endpoint for device {device_raw}')
            return None

    @staticmethod
    def _parse_certificate(device_raw):
        try:
            cert = DigicertScannedCertificate()

            cert.cert_id = device_raw.get('certificateId')
            cert.cert_rating = DigicertCertcentralAdapter._parse_enum('certRating', device_raw, ENUM_CERT_RATING)
            cert.cert_status = DigicertCertcentralAdapter._parse_enum('certStatus', device_raw, ENUM_CERT_STATUS)

            cert.cert_ca = device_raw.get('ca')
            cert.cert_cn = device_raw.get('commonName')
            cert.cert_san = device_raw.get('san').split(',') if device_raw.get('san') else None
            cert.cert_org = device_raw.get('org')
            try:
                cert.cert_expiry_date = parse_date(device_raw.get('certExpiryDate'))
            except Exception:
                logger.exception(f'Failed to parse certificate expiry date for {device_raw}')
            return cert
        except Exception:
            logger.exception(f'Failed to parse certificate for device {device_raw}')
            return None

    @staticmethod
    def _parse_scan(device_raw):
        try:
            scan = DigicertScan()
            scan.scan_id = device_raw.get('scanId')
            scan.scan_name = device_raw.get('scanName')
            try:
                scan.scan_first_discovery_date = parse_date(device_raw.get('firstDiscoveredDate'))
            except Exception:
                logger.exception(f'Failed to parse firstDiscoveredDate for {device_raw} ')
            scan.scan_protocol = device_raw.get('service')
            scan_vulnerabilities = DigicertCertcentralAdapter._parse_enum(
                'vulnerabilityName', device_raw, ENUM_CERT_VULNS)
            if scan_vulnerabilities:
                # Filter out sparse values
                scan.scan_vulnerabilities = list(filter(lambda val: val not in ['NO_VULNERABILITY_FOUND'],
                                                        scan_vulnerabilities))
            return scan
        except Exception:
            logger.exception(f'Failed to parse scan for device {device_raw}')
            return None

    @staticmethod
    def _fill_generic_fields(device, device_raw):
        try:
            device_id = device_raw.get('certificateId')
            if not device_id:
                message = f'Bad device with no ID {device_raw}'
                logger.warning(message)
                raise Exception(message)

            ip_address = device_raw.get('ipAddress')
            device.id = f'{device_id}_{ip_address or ""}'

            try:
                device.add_ips_and_macs(ips=[ip_address])
            except Exception:
                logger.exception(f'Failed to parse IP for device {device_raw}')

            device.hostname = device_raw.get('domainName')

            try:
                device.figure_os(' '.join(device_raw.get(field, '') for field in ['os', 'osVersion']))
            except Exception:
                logger.exception(f'Failed to parse OS for device {device_raw}')

            try:
                if device_raw.get('port'):
                    device.add_open_port(protocol=device_raw.get('service', ''), port_id=device_raw.get('port'),
                                         service_name=device_raw.get('serverName', ''))
            except Exception:
                logger.exception(f'Failed to parse open port for device {device_raw}')

            try:
                if device_raw.get('serverName'):
                    device.add_installed_software(name=device_raw.get('serverName'),
                                                  version=device_raw.get('serverVersion', ''))
            except Exception:
                logger.exception(f'Failed to parse OS for device {device_raw}')

            try:
                if device_raw.get('deviceType'):
                    device.device_model = device_raw.get('deviceType')
            except Exception:
                logger.exception(f'Failed to parse deviceType for device {device_raw}')

        except Exception:
            logger.exception(f'Failed to parse certificate for device {device_raw}')
            return

    @staticmethod
    def _fill_specific_fields(device, device_raw):
        try:
            device.endpoint = DigicertCertcentralAdapter._parse_endpoint(device_raw)
            device.scan = DigicertCertcentralAdapter._parse_scan(device_raw)
            device.is_cert_present = device_raw.get('isCertPresent', False)
            device.certificate = DigicertCertcentralAdapter._parse_certificate(device_raw)
        except Exception:
            logger.exception(f'Failed to fill specific fields for {device_raw}')

    def _create_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            self._fill_generic_fields(device, device_raw)
            self._fill_specific_fields(device, device_raw)
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Failed to generate Digicert Certcentral Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
