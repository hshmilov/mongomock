import logging
from datetime import datetime

import OpenSSL

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.digicert_pki_platform.consts import WS_DEFAULT_DOMAIN
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from axonius.clients.digicert_pki_platform.connection import DigicertPkiPlatformConnection

logger = logging.getLogger(f'axonius.{__name__}')


class DigicertPkiPlatformAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        seat_id = Field(str, 'Seat ID')
        common_name = Field(str, 'Common Name')
        account_id = Field(str, 'Account ID')
        profile_oid = Field(str, 'Profile OID')
        cert_email = Field(str, 'Certificate Email Address')
        cert_status = Field(str, 'Certificate Status')
        revoked_at = Field(datetime, 'Revoked At')
        revoke_reason = Field(str, 'Revocation Reason Code')
        valid_from = Field(datetime, 'Certificate Issue Date')
        valid_to = Field(datetime, 'Certificate Expiration date')
        serial_number = Field(str, 'Certificate Serial Number')
        is_escrowed = Field(bool, 'Is Escrowed')
        enrollment_notes = Field(str, 'Enrollment Notes')
        revoke_comments = Field(str, 'Revocation Comments')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    def _get_client_id(self, client_config):
        try:
            x509 = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM,
                                                   self._grab_file_contents(client_config['cert_file']))
            return x509.get_subject().commonName
        except Exception:
            logger.exception('Failed extracting client_id from cert_file')
            raise

    @staticmethod
    def _test_reachability(client_config):
        try:
            url_for_reachability = RESTConnection.build_url(client_config['domain'], use_domain_path=True)
            # Note: https version is not reported as reachable without sufficient certificate, so we use the http one.
            url_for_reachability = url_for_reachability.replace('https://', 'http://', 1)
            return RESTConnection.test_reachability(url_for_reachability,
                                                    https_proxy=client_config.get('https_proxy'))
        except Exception:
            logger.exception('Unexpected exception occurred during test_reachability')
            return False

    def _connect_client(self, client_config):
        try:
            connection = DigicertPkiPlatformConnection(
                domain=client_config['domain'],
                cert_file_data=self._grab_file_contents(client_config['cert_file']),
                private_key_data=self._grab_file_contents(client_config['private_key']),
                https_proxy=client_config.get('https_proxy'))
            with connection:
                pass
            return connection
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
        The schema DigicertPkiPlatformAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Domain',
                    'type': 'string',
                    'default': WS_DEFAULT_DOMAIN,
                },
                {
                    'name': 'cert_file',
                    'title': 'RA Certificate File',
                    'description': 'The binary contents of the cert_file',
                    'type': 'file'
                },
                {
                    'name': 'private_key',
                    'title': 'Private Key File',
                    'description': 'The binary contents of the private_key',
                    'type': 'file'
                },
                {
                    'name': 'https_proxy',
                    'title': 'HTTPS Proxy',
                    'type': 'string'
                }
            ],
            'required': [
                'domain',
                'cert_file',
                'private_key'
            ],
            'type': 'array'
        }

    @staticmethod
    def _parse_specific_fields(device, device_raw):

        device.seat_id = device_raw.get('seatId')
        device.common_name = device_raw.get('commonName')
        device.account_id = device_raw.get('accountId')
        device.profile_oid = device_raw.get('profileOID')
        device.cert_email = device_raw.get('emailAddress')
        device.cert_status = device_raw.get('status')
        device.revoked_at = parse_date(device_raw.get('revokeAt'))
        device.revoke_reason = device_raw.get('revokeReason')
        device.valid_from = parse_date(device_raw.get('validFrom'))
        device.valid_to = parse_date(device_raw.get('validTo'))
        device.serial_number = device_raw.get('serialNumber')
        device.is_escrowed = device_raw.get('isEscrowed')
        device.enrollment_notes = device_raw.get('enrollmentNotes')
        device.revoke_comments = device_raw.get('revokeComments')

    @staticmethod
    def _parse_generic_fields(device, device_raw):
        device.name = device_raw.get('commonName')
        device.email = device_raw.get('emailAddress')

    def _create_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            device_id_components = [device_raw.get(field_name) for field_name in ['seatId', 'serialNumber']]
            if not all(device_id_components):
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = '_'.join(device_id_components)
            self._parse_generic_fields(device, device_raw)
            self._parse_specific_fields(device, device_raw)
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching DigicertPkiPlatform Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
