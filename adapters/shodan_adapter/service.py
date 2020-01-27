import logging
import chardet

from axonius.adapter_base import AdapterProperty
from axonius.scanner_adapter_base import ScannerAdapterBase
from axonius.adapter_exceptions import ClientConnectionException
from axonius.devices.device_adapter import ShodanVuln
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from axonius.clients.shodan.connection import ShodanConnection
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.shodan.consts import DEFAULT_DOMAIN
from axonius.utils.parsing import make_dict_from_csv
from axonius.fields import Field
from axonius.utils.parsing import remove_large_ints
from shodan_adapter.client_id import get_client_id
from shodan_adapter.execution import ShodanExecutionMixIn


logger = logging.getLogger(f'axonius.{__name__}')


CIDR_TYPE = 'cidr_type'
SEARCH_TYPE = 'search_type'


class ShodanAdapter(ShodanExecutionMixIn, ScannerAdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        query_search = Field(str, 'Search Query')
        file_name = Field(str, 'File Name')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain') or 'api.shodan.io',
                                                https_proxy=client_config.get('https_proxy'))

    def _connect_client(self, client_config):
        try:
            with ShodanConnection(apikey=client_config['apikey'],
                                  domain_prefered=client_config.get('domain'),
                                  https_proxy=client_config.get('https_proxy')) as connection:
                if client_config.get('cidr'):
                    connection.get_cidr_info(client_config['cidr'].split(',')[0])
                    return connection, client_config['cidr'].split(','), CIDR_TYPE, client_config.get('user_id')
                if client_config.get('query_search'):
                    connection.get_search_info(client_config['query_search'].split(',')[0])
                    return connection, client_config['query_search'].split(','),\
                        SEARCH_TYPE, client_config.get('user_id')
                if not client_config.get('csv') or not client_config.get('user_id'):
                    raise ClientConnectionException('Please Enter CIDR CSV File or CIDR list or Query Search String')
                csv_data_bytes = self._grab_file_contents(client_config['csv'])
                encoding = chardet.detect(csv_data_bytes)['encoding']  # detect decoding automatically
                encoding = encoding or 'utf-8'
                csv_data = csv_data_bytes.decode(encoding)
                csv_data = make_dict_from_csv(csv_data)
                if 'CIDR' not in csv_data.fieldnames:
                    raise ClientConnectionException('The CSV file is missing the CIDR column')
                dns_field_name = None
                for field_name in csv_data.fieldnames:
                    if field_name and field_name.replace(' ', '').lower() == 'dnsname':
                        dns_field_name = field_name
                cidr_list = []
                for cidr_raw in csv_data:
                    if cidr_raw.get('CIDR'):
                        cidr_dns_name = None
                        if dns_field_name:
                            cidr_dns_name = cidr_raw.get(dns_field_name)
                        cidr_list.append([cidr_raw.get('CIDR'), cidr_dns_name])
                return connection, cidr_list, CIDR_TYPE, client_config.get('user_id')
        except RESTException as e:
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                client_config.get('domain'), str(e))
            logger.warning(message, exc_info=True)
            raise ClientConnectionException(message)

    @staticmethod
    def _query_devices_by_client(client_name, client_data):
        """
        Get all devices from a specific  domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        connection, cidr_list, shodan_type, file_name = client_data
        with connection:
            for cidr in cidr_list:
                try:
                    shodan_dns_name = None
                    cidr_str = ''
                    if isinstance(cidr, list):
                        cidr_str = cidr[0]
                        shodan_dns_name = cidr[1]
                    if isinstance(cidr, str):
                        cidr_str = cidr
                    ip_dict = dict()
                    cidr_str = cidr_str.strip()
                    if shodan_type == CIDR_TYPE:
                        matches = connection.get_cidr_info(cidr_str)
                    else:
                        matches = connection.get_search_info(cidr_str)
                    for match_data in matches:
                        ip = match_data.get('ip_str')
                        if ip:
                            if ip not in ip_dict:
                                ip_dict[ip] = []
                            ip_dict[ip].append(match_data)
                    query_search = None
                    if shodan_type == SEARCH_TYPE:
                        query_search = cidr_list
                    yield ip_dict, shodan_dns_name, query_search, file_name
                except Exception:
                    logger.debug(f'Problem getting cidr {cidr}')

    @staticmethod
    def _clients_schema():
        """
        The schema ShodanAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Shodan Domain',
                    'type': 'string',
                    'default': DEFAULT_DOMAIN,
                },
                {
                    'name': 'cidr',
                    'title': 'CIDR',
                    'type': 'string'
                },
                {
                    'name': 'apikey',
                    'title': 'API Key',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': 'https_proxy',
                    'title': 'HTTPS Proxy',
                    'type': 'string'
                },
                {
                    'name': 'user_id',
                    'title': 'CIDR CSV File Name',
                    'type': 'string'
                },
                {
                    'name': 'csv',
                    'title': 'CIDR CSV File',
                    'description': 'The binary contents of the csv',
                    'type': 'file'
                },
                {
                    'name': 'query_search',
                    'title': 'Query Search',
                    'type': 'string'
                }


            ],
            'required': [
                'apikey'
            ],
            'type': 'array'
        }

    def _parse_raw_data(self, devices_raw_data):
        # pylint: disable=R1702,R0912,R0915,R0914
        for ip_dict, shodan_dns_name, query_search, file_name in devices_raw_data:
            for ip_str, device_raw_list in ip_dict.items():
                try:
                    device = self._new_device_adapter()
                    device.id = ip_str
                    device.query_search = query_search
                    device.file_name = file_name
                    device.add_public_ip(ip_str)
                    device.add_nic(None, [ip_str])
                    device.software_cves = []
                    hostname = None
                    city = None
                    region_code = None
                    country_name = None
                    org = None
                    os = None
                    http_server = None
                    http_site_map = None
                    http_location = None
                    http_security_text_hash = None
                    ports = []
                    cpe = []
                    isp = None
                    vulns = []
                    for device_raw in device_raw_list:
                        if not isinstance(device_raw, dict):
                            logger.warning(f'Weird object {device_raw}')
                            continue
                        vulns_dict = device_raw.get('vulns') if isinstance(device_raw.get('vulns'), dict) else {}
                        for vuln_name, vuln_data in vulns_dict.items():
                            try:
                                vulns.append(ShodanVuln(summary=vuln_data.get('summary'),
                                                        vuln_name=vuln_name,
                                                        cvss=float(vuln_data.get('cvss'))
                                                        if vuln_data.get('cvss') is not None
                                                        else None))
                                device.add_vulnerable_software(cve_id=vuln_name)
                            except Exception:
                                logger.exception(f'Problem adding vulnerability for {vuln_name}')
                        if not hostname:
                            hostname = device_raw.get('hostnames')[0] if isinstance(device_raw.get('hostnames'), list) \
                                and len(device_raw.get('hostnames')) > 0 else None
                        http_info = device_raw.get('http')
                        if http_info and isinstance(http_info, dict):
                            if not http_server:
                                http_server = http_info.get('server')
                            if not http_site_map:
                                http_site_map = http_info.get('sitemap')
                            if not http_location:
                                http_location = http_info.get('location')
                            if not http_security_text_hash:
                                http_security_text_hash = http_info.get('securitytxt_hash')
                        if not org:
                            org = device_raw.get('org')
                        if not os:
                            os = device_raw.get('os')
                        if not isp:
                            isp = device_raw.get('isp')
                        if not city:
                            city = (device_raw.get('location') or {}).get('city')
                        if not region_code:
                            region_code = (device_raw.get('location') or {}).get('region_code')
                        if not country_name:
                            country_name = (device_raw.get('country_name') or {}).get('country_name')
                        if device_raw.get('port'):
                            ports.append(device_raw.get('port'))
                            try:
                                device.add_open_port(port_id=device_raw.get('port'),
                                                     protocol=device_raw.get('transport'),
                                                     service_name=(device_raw.get('_shodan') or {}).get('module'))
                            except Exception:
                                logger.warning(f'Could not add port for device', exc_info=True)
                        if device_raw.get('cpe') and isinstance(device_raw.get('cpe'), list):
                            for cpe_data in device_raw.get('cpe'):
                                if cpe_data and isinstance(cpe_data, str):
                                    cpe.append(cpe_data)
                    if shodan_dns_name or hostname:
                        device.hostname = shodan_dns_name or hostname
                    if not os:
                        os = None
                    if not org:
                        org = None
                    if not isp:
                        isp = None
                    if not city:
                        city = None
                    if not region_code:
                        region_code = None
                    if not country_name:
                        city = None
                    device.set_shodan_data(isp=isp,
                                           country_name=country_name,
                                           city=city,
                                           region_code=region_code,
                                           ports=ports,
                                           vulns=vulns,
                                           org=org,
                                           os=os,
                                           cpe=cpe,
                                           http_location=http_location,
                                           http_server=http_server,
                                           http_site_map=http_site_map,
                                           http_security_text_hash=http_security_text_hash)
                    try:
                        device_raw_list = remove_large_ints(device_raw_list, 'shodan_raw_data')
                        device.set_raw({'data': device_raw_list})
                    except Exception:
                        logger.warning('Problem setting raw data', exc_info=True)
                    yield device
                except Exception:
                    logger.warning(f'Problem with fetching Shodan Device for {ip_str}', exc_info=True)

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Network]
