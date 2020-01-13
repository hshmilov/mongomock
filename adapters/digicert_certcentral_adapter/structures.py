import datetime

from axonius.fields import Field, ListField
from axonius.smart_json_class import SmartJsonClass
from digicert_certcentral_adapter.consts import ENUM_CERT_STATUS, ENUM_CERT_RATING, ENUM_CERT_VULNS


class Endpoint(SmartJsonClass):
    server_id = Field(str, 'Server ID',
                      description='Server ID, if available.')
    hardware_type = Field(str, 'Hardware type',
                          description='General hardware type, if available.')
    server_software = Field(str, 'Server software',
                            description='Server software, if available.')
    server_version = Field(str, 'Server version',
                           description='Server version, if available.')
    domain_name = Field(str, 'Root domain',
                        description='Root domain of the endpoint.')
    port_status = Field(str, 'Endpoint port status',
                        description='Availability or connection status of the endpoint.')
    security_rating = Field(str, 'Server security rating',
                            description='Server security rating,'
                                        ' based on the endpoint\'s communication and security settings.')
    # os = Field(str, 'OS',
    #            description='Operating system.')
    # osVersion = Field(str, 'OS Version',
    #                   description='Operating system version, if available.')


class DigicertScan(SmartJsonClass):
    scan_id = Field(str, 'Discovery scan id',
                    description='Unique ID for the CertCentral Discovery scan that'
                                ' scanned and retrieved details for the endpoint.')
    scan_name = Field(str, 'Discovery scan name',
                      description='Friendly name the admin gave to the CertCentral Discovery scan.')
    scan_first_discovery_date = Field(datetime.datetime, 'Endpoint first discovery date',
                                      description='Date endpoint was first found by CertCentral Discovery scan.')
    scan_protocol = Field(str, 'Communication protocol',
                          description='Communication protocol, such as https.')
    scan_vulnerabilities = ListField(str, 'Endpoint vulnerabilities found',
                                     description='Vulnerabilities found based on known endpoint details.',
                                     enum=ENUM_CERT_VULNS)


class Certificate(SmartJsonClass):
    cert_ca = Field(str, 'Certificate authority',
                    description='Certificate Authority that issued the certificate.')
    cert_cn = Field(str, 'Certificate common name',
                    description='Common name of certificate found on the endpoint.')
    cert_san = ListField(str, 'Certificate subject alternative names',
                         description='Subject alternative names on the certificate found on the endpoint.')
    cert_org = Field(str, 'Endpoint certificate organization name',
                     description='Organization name on the certificate found on the endpoint.')
    cert_expiry_date = Field(datetime.datetime, 'Certificate expiration date',
                             description='Expiration date of the certificate found on the endpoint.')


class DigicertScannedCertificate(Certificate):
    cert_id = Field(str, 'Digicert ceritificate id',
                    description='Unique DigiCert-generated ID for the certificate found on the endpoint.'
                                ' Use for API requests that require it.')
    # Enumerations source: (might need update from time to time)
    #   https://dev.digicert.com/glossary/#certificate-status-discovery
    cert_rating = Field(str, 'Certificate Security rating',
                        description='Certificate security rating, '
                                    'based on industry standards and the certificate\'s settings.',
                        enum=ENUM_CERT_RATING)
    cert_status = Field(str, 'Certificate status',
                        description='Status of the certificate found on the endpoint.',
                        enum=ENUM_CERT_STATUS)
