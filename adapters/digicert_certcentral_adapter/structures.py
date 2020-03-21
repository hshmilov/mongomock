import datetime

from axonius.fields import Field, ListField
from axonius.smart_json_class import SmartJsonClass
from digicert_certcentral_adapter.consts import ENUM_CERT_STATUS, ENUM_CERT_RATING, ENUM_CERT_VULNS, ENUM_ORDER_STATUS


class DiscoveryEndpoint(SmartJsonClass):
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


class DiscoveryScan(SmartJsonClass):
    scan_id = Field(str, 'scan id',
                    description='Unique ID for the CertCentral Discovery scan that'
                                ' scanned and retrieved details for the endpoint.')
    scan_name = Field(str, 'scan name',
                      description='Friendly name the admin gave to the CertCentral Discovery scan.')
    scan_first_discovery_date = Field(datetime.datetime, 'Endpoint first discovery date',
                                      description='Date endpoint was first found by CertCentral Discovery scan.')
    scan_vulnerabilities = ListField(str, 'Endpoint vulnerabilities found',
                                     description='Vulnerabilities found based on known endpoint details.',
                                     enum=ENUM_CERT_VULNS)
    scan_protocol = Field(str, 'Communication protocol',
                          description='Communication protocol, such as https.')


class Certificate(SmartJsonClass):
    # Common
    cert_id = Field(str, 'Certificate ID')
    cert_cn = Field(str, 'Common name',
                    description='Common name of certificate found on the endpoint.')
    cert_expiry_date = Field(datetime.datetime, 'Expiration date',
                             description='Expiration date of the certificate found on the endpoint.')

    # Scanned Certificate specific
    cert_ca = Field(str, 'Certificate authority',
                    description='Certificate Authority that issued the certificate.')
    cert_san = ListField(str, 'Subject alternative names',
                         description='Subject alternative names on the certificate found on the endpoint.')
    cert_org = Field(str, 'Organization name',
                     description='Organization name on the certificate found on the endpoint.')
    cert_rating = Field(str, 'Security rating',
                        description='Certificate security rating, '
                                    'based on industry standards and the certificate\'s settings.',
                        enum=ENUM_CERT_RATING)
    cert_status = Field(str, 'Certificate status',
                        description='Status of the certificate found on the endpoint.',
                        enum=ENUM_CERT_STATUS)

    # Ordered Certificate specific
    cert_days_remaining = Field(int, 'Days remaining')
    cert_signature_hash = Field(str, 'Signature Hash')


class Order(SmartJsonClass):
    order_id = Field(int, 'Order ID')
    order_status = Field(str, 'Order status', enum=ENUM_ORDER_STATUS)
    is_order_renewed = Field(bool, 'Was order renewed')
    organization_id = Field(int, 'Associated organization ID')
    organization_name = Field(str, 'Associated organization name')
    order_date_created = Field(datetime.datetime, 'Order creation date')
    order_validity_years = Field(int, 'Order validity years')
    has_duplicated = Field(bool, 'Has duplicate orders')
    # Possible product_name_ids: https://dev.digicert.com/glossary/#product-identifiers
    product_name_id = Field(str, 'Order product name id')
