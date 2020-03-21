import logging
from datetime import datetime

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field, ListField
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import parse_date
from digicert_certcentral_adapter.client_id import get_client_id
from digicert_certcentral_adapter.connection import DigicertCertcentralConnection
from digicert_certcentral_adapter import consts
from digicert_certcentral_adapter.structures import DiscoveryScan, Certificate, Order, DiscoveryEndpoint
from digicert_certcentral_adapter.utils import parse_enum

logger = logging.getLogger(f'axonius.{__name__}')


class DigicertCertcentralAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        device_type = Field(str, 'Device Type', enum=consts.DEVICE_TYPES)

        # DeviceType.SCANNED_ENDPOINT specific
        endpoint = Field(DiscoveryEndpoint, 'Endpoint')
        scan = Field(DiscoveryScan, 'Scan')
        is_cert_present = Field(bool, 'Endpoint certificate presence',
                                description='Whether or not certificate is installed at the endpoint.')

        # DeviceType.ORDER specific
        order = Field(Order, 'Order')
        # Note: This comes from the certificate's dns_names, Moved here for better correlation
        dns_names = ListField(str, 'DNS Names')

        # Common Field
        certificate = Field(Certificate, 'Certificate')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(consts.REST_ENDPOINT_AUTH,
                                                http_proxy=client_config.get('https_proxy'))

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
                    'name': 'account_id',
                    'title': 'Account ID',
                    'type': 'string',
                },
                {
                    'name': 'api_key',
                    'title': 'API Key',
                    'type': 'string',
                    'format': 'password',
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
                    'default': False,
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
    def _parse_endpoint(device_raw):
        try:
            endpoint = DiscoveryEndpoint()
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
    def _parse_scanned_certificate(certificate_raw):
        try:
            cert = Certificate()
            cert.cert_id = certificate_raw.get('certificateId')
            cert.cert_ca = certificate_raw.get('ca')
            cert.cert_cn = certificate_raw.get('commonName')
            cert.cert_san = certificate_raw.get('san').split(',') \
                if isinstance(certificate_raw.get('san'), str) else None
            cert.cert_org = certificate_raw.get('org')
            cert.cert_rating = parse_enum(certificate_raw, 'certRating', consts.ENUM_CERT_RATING)
            cert.cert_status = parse_enum(certificate_raw, 'certStatus', consts.ENUM_CERT_STATUS)
            cert.cert_expiry_date = parse_date(certificate_raw.get('certExpiryDate'))
            return cert
        except Exception:
            logger.exception(f'Failed to parse scanned certificate: {certificate_raw}')
            return None

    @staticmethod
    def _parse_scan(device_raw):
        try:
            scan = DiscoveryScan()
            scan.scan_id = device_raw.get('scanId')
            scan.scan_name = device_raw.get('scanName')
            scan.scan_first_discovery_date = parse_date(device_raw.get('firstDiscoveredDate'))
            scan.scan_protocol = device_raw.get('service')
            scan_vulnerabilities = parse_enum('vulnerabilityName', device_raw, consts.ENUM_CERT_VULNS)
            if scan_vulnerabilities:
                # Filter out sparse values
                scan.scan_vulnerabilities = list(filter(lambda val: val not in ['NO_VULNERABILITY_FOUND'],
                                                        scan_vulnerabilities))
            return scan
        except Exception:
            logger.exception(f'Failed to parse scan for device {device_raw}')
            return None

    @staticmethod
    def _fill_generic_scanned_endpoint_fields(device, device_raw):
        try:
            device_id = device_raw.get('certificateId')
            if not device_id:
                message = f'Bad device with no ID {device_raw}'
                logger.warning(message)
                raise Exception(message)
            ip_address = device_raw.get('ipAddress') or ''
            device.id = f'SCAN_{device_id}_{ip_address or ""}'

            # Note: we set the asset_name to be the certificate id
            #       for different Digicert asset entities to correlate into the same device
            device.name = f'Certificate {device_id}'

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
                logger.exception(f'Failed to parse installed software for device {device_raw}')

            try:
                if device_raw.get('deviceType'):
                    device.device_model = device_raw.get('deviceType')
            except Exception:
                logger.exception(f'Failed to parse deviceType for device {device_raw}')

        except Exception:
            logger.exception(f'Failed to parse generic fields for device {device_raw}')
            return

    @staticmethod
    def _handle_scanned_endpoint_device(device, device_raw):
        try:
            DigicertCertcentralAdapter._fill_generic_scanned_endpoint_fields(device, device_raw)
            device.endpoint = DigicertCertcentralAdapter._parse_endpoint(device_raw)
            device.scan = DigicertCertcentralAdapter._parse_scan(device_raw)
            if device_raw.get('isCertPresent'):
                device.certificate = DigicertCertcentralAdapter._parse_scanned_certificate(device_raw)
        except Exception:
            logger.exception(f'Failed to fill specific fields for {device_raw}')

    @staticmethod
    def _parse_ordered_certificate(certificate_raw, order_status=None):
        try:
            cert = Certificate()
            cert.cert_id = certificate_raw.get('id')
            cert.cert_cn = certificate_raw.get('common_name')
            expiry_date = parse_date(certificate_raw.get('valid_till'))
            cert.cert_expiry_date = expiry_date
            cert.cert_signature_hash = certificate_raw.get('signature_hash')
            # translate an order_status into an equivalent certificate_status
            cert.cert_status = consts.CERT_STATUS_BY_ORDER_STATUS.get(order_status)

            try:
                days_remaining = None
                if certificate_raw.get('days_remaining'):
                    days_remaining = int(certificate_raw['days_remaining'])
                    # Note: Transition expired certificates' remaining_days to negative if not
                    if (expiry_date and (expiry_date < parse_date(datetime.utcnow())) and (days_remaining > 0)):
                        days_remaining = -1 * days_remaining
                cert.cert_days_remaining = days_remaining
            except (ValueError, TypeError):
                logger.warning(f'Invalid days_remaining found: {certificate_raw.get("days_remaining")}')

            return cert
        except Exception:
            logger.exception(f'Failed to parse ordered certificate: {certificate_raw}')
            return None

    @staticmethod
    def _parse_order(device_raw):
        try:
            order = Order()
            order.order_id = device_raw.get('id')
            order.order_status = parse_enum(device_raw, 'status', consts.ENUM_ORDER_STATUS)
            order.is_order_renewed = device_raw.get('is_renewed')
            order.order_date_created = parse_date(device_raw.get('date_created'))
            organization_dict = device_raw.get('organization')
            if isinstance(organization_dict, dict):
                order.organization_id = organization_dict.get('id')
                order.organization_name = organization_dict.get('name')
            order.order_validity_years = device_raw.get('validitiy_years')
            order.has_duplicated = device_raw.get('has_duplicates')
            order.product_name_id = device_raw.get('product_name_id')
            return order
        except Exception:
            logger.exception(f'Failed to fill specific fields for {device_raw}')

    @staticmethod
    def _handle_order_device(device, device_raw):
        try:
            device_id = device_raw.get('id')  # this is the order id
            if not device_id:
                message = f'Bad device with no ID {device_raw}'
                logger.warning(message)
                raise Exception(message)
            device.id = f'ORDER_{device_id}'
            device.order = DigicertCertcentralAdapter._parse_order(device_raw)
            certificate_dict = device_raw.get('certificate')
            if isinstance(certificate_dict, dict):
                # Note: we set the asset_name to be the certificate id
                #       for different Digicert asset entities to correlate into the same device
                device.name = f'Certificate {certificate_dict.get("id")}'
                device.hostname = certificate_dict.get('common_name')
                device.dns_names = certificate_dict.get('dns_names') \
                    if isinstance(certificate_dict.get('dns_names'), list) else None
                device.certificate = DigicertCertcentralAdapter._parse_ordered_certificate(
                    certificate_dict, order_status=device_raw.get('status'))
        except Exception:
            logger.exception(f'Failed to fill specific fields for {device_raw}')

    def _create_device(self, device_raw):
        try:
            if not isinstance(device_raw, tuple):
                logger.error(f'Invalid device_raw retrieved {device_raw}')
                return None

            device = self._new_device_adapter()
            device_type, device_raw = device_raw

            if device_type == consts.DeviceType.SCANNED_ENDPOINT:
                device.device_type = consts.DeviceType.SCANNED_ENDPOINT.value
                self._handle_scanned_endpoint_device(device, device_raw)

            elif device_type == consts.DeviceType.ORDER:
                device.device_type = consts.DeviceType.ORDER.value
                self._handle_order_device(device, device_raw)

            else:
                logger.error(f'Unknown device_type "{device_type}" yielded')
                return None

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
