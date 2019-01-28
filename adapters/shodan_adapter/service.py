import logging

from axonius.adapter_base import AdapterProperty
from axonius.scanner_adapter_base import ScannerAdapterBase
from axonius.adapter_exceptions import ClientConnectionException
from axonius.devices.device_adapter import ShodanVuln
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from axonius.clients.shodan.connection import ShodanConnection
from shodan_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class ShodanAdapter(ScannerAdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        # AUTOADAPTER - add here device fields if needed
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        raise NotImplementedError()

    @staticmethod
    def _connect_client(client_config):
        try:
            with ShodanConnection(apikey=client_config['apikey']) as connection:
                connection.get_cidr_info(client_config['cidr'])
                return connection, client_config['cidr']
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
        connection, cidr = client_data
        with connection:
            matches = connection.get_cidr_info(cidr)
        ip_dict = dict()
        for match_data in matches:
            ip = match_data.get('ip_str')
            if ip:
                if ip not in ip_dict:
                    ip_dict[ip] = []
                ip_dict[ip].append(match_data)
        return ip_dict

    @staticmethod
    def _clients_schema():
        """
        The schema ShodanAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
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
                }
            ],
            'required': [
                'cidr',
                'apikey'
            ],
            'type': 'array'
        }

    def _parse_raw_data(self, devices_raw_data):
        # pylint: disable=R1702,R0912,R0915
        for ip_str, device_raw_list in devices_raw_data.items():
            try:
                device = self._new_device_adapter()
                device.id = ip_str
                device.add_nic(None, [ip_str])
                hostname = None
                city = None
                region_code = None
                country_name = None
                org = None
                os = None
                ports = []
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
                        except Exception:
                            logger.exception(f'Problem adding vuln name {vuln_name}')
                    if not hostname:
                        hostname = device_raw.get('hostnames')[0] if isinstance(device_raw.get('hostnames'), list) \
                            and len(device_raw.get('hostnames')) > 0 else None
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
                if hostname:
                    device.hostname = hostname
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
                                       os=os)
                device.set_raw({ip_str: device_raw_list})
                yield device
            except Exception:
                logger.exception(f'Problem with fetching Shodan Device for {ip_str}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Network]
