import logging
from urllib.parse import urlparse

from urllib3.contrib import pyopenssl

from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field, ListField
from axonius.smart_json_class import SmartJsonClass
from webscan_adapter.scanners.service_scanner import ServiceScanner

logger = logging.getLogger(f'axonius.{__name__}')


class X509Name(SmartJsonClass):
    country_name = Field(str, 'Country Name')
    postal_code = Field(str, 'Postal Code')
    state = Field(str, 'State Or Province Name')
    locality = Field(str, 'Locality Name')
    street = Field(str, 'Street Name')
    organization = Field(str, 'Organization Name')
    organization_unit = Field(str, 'Organizational Unit Name')
    common_name = Field(str, 'Common Name')
    email_address = Field(str, 'Email Address')


class CertAltName(SmartJsonClass):
    name_type = Field(str, 'Type')
    name = Field(str, 'Name')


class Cert(SmartJsonClass):
    issuer = Field(X509Name, 'Issuer')
    version = Field(str, 'Version')
    serial_number = Field(str, 'Serial Number')
    subject = Field(X509Name, 'Subject')
    alt_names = ListField(CertAltName, 'Alt Names')


class CertScanner(ServiceScanner):
    """
    Get SSL Certificate data
    """
    DEFAULT_SSL_PORT = 443

    @staticmethod
    def get_cert_info(url: str = None, domain: str = None, port: int = DEFAULT_SSL_PORT):
        """
        Get cert data from url/domain
        :param url: url to get the cert from
        :param domain: domain to get the cert from
        :param port: remote server port
        :return: dict of cert data
        """
        if not domain and not url:
            return {}
        if not domain:
            domain = urlparse(url).netloc
        logger.debug(f'Getting {domain}:{port} cert info')
        x509 = pyopenssl.OpenSSL.crypto.load_certificate(
            pyopenssl.OpenSSL.crypto.FILETYPE_PEM,
            pyopenssl.ssl.get_server_certificate((domain, port))
        )
        subject = x509.get_subject().get_components()
        issuer = x509.get_issuer().get_components()
        return {
            'issuer': issuer,
            'version': x509.get_version(),
            'subject': subject,
            'serial_number': x509.get_serial_number(),
            'alt_name': pyopenssl.get_subj_alt_name(x509)
        }

    @staticmethod
    def get_subject_value(subject_data: list, key: bytes) -> str:
        """
        Parse x509 subject data from key
        :param subject_data: data to parse
        :param key: key to parse
        :return: decoded key
        """
        filtered = [x[1] for x in subject_data if x[0] == key and len(x) > 1]
        if not filtered:
            return None
        value = filtered.pop()
        if not value:
            return None
        value = value.decode('utf-8') if isinstance(value, bytes) else value
        return value

    @staticmethod
    def get_x509_name_from_data(data: list) -> X509Name:
        """
        parse x509 data into X509Name object
        :param data: data dict
        :return: X509Name object
        """
        if not data:
            return None
        return X509Name(country_name=CertScanner.get_subject_value(data, b'C'),
                        postal_code=CertScanner.get_subject_value(data, b'postalCode'),
                        state=CertScanner.get_subject_value(data, b'ST'),
                        locality=CertScanner.get_subject_value(data, b'L'),
                        street=CertScanner.get_subject_value(data, b'street'),
                        organization=CertScanner.get_subject_value(data, b'O'),
                        organization_unit=CertScanner.get_subject_value(data, b'OU'),
                        common_name=CertScanner.get_subject_value(data, b'CN'),
                        email_address=CertScanner.get_subject_value(data, b'emailAddress'))

    def scan(self):
        """
        Get cert data form the given url / domain
        :return: cert data results
        """
        self.results = self.get_cert_info(self.url, self.domain)
        return self.results

    def parse(self, device: DeviceAdapter):
        """
        Parse the scan results into a DeviceAdapter data
        :param device: DeviceAdapter to add the results
        :return: None
        """
        if not self.results:
            return
        data = self.results
        alt_names_data = data.get('alt_name', [])
        alt_names = [CertAltName(name_type=name[0], name=name[1]) for name in alt_names_data if len(name) > 1]
        subject = self.get_x509_name_from_data(data.get('subject'))
        issuer = self.get_x509_name_from_data(data.get('issuer'))
        crt = Cert(issuer=issuer,
                   version=data.get('version'),
                   serial_number=data.get('serial_number'),
                   alt_names=alt_names,
                   subject=subject)
        device.cert = crt
