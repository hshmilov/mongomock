import logging

import chardet

from axonius.adapter_base import AdapterProperty
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field, ListField
from axonius.scanner_adapter_base import ScannerAdapterBase
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import make_dict_from_csv

logger = logging.getLogger(f'axonius.{__name__}')


class RiskiqCsvAdapter(ScannerAdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        brands = ListField(str, 'Brands')
        web_component_names = ListField(str, 'Web Component Names')
        asn = Field(int, 'ASN')
        url = Field(str, 'URL')
        response_code = Field(int, 'Response Code')
        final_response_codes = Field(int, 'Final Response Codes')
        final_urls = Field(str, 'Final URLs')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return f'RISKIQ_{client_config["riskiq_host_csv_label"]}_{client_config["riskiq_ip_csv_label"]}' \
            f'_{client_config["riskiq_url_csv_label"]}'

    @staticmethod
    def _test_reachability(client_config):
        raise NotImplementedError()

    def _create_csv_data_from_file(self, csv_file):
        csv_data_bytes = self._grab_file_contents(csv_file)

        encoding = chardet.detect(csv_data_bytes)['encoding']  # detect decoding automatically
        encoding = encoding or 'utf-8'
        csv_data = csv_data_bytes.decode(encoding)
        csv_dict = make_dict_from_csv(csv_data)
        return csv_dict

    def _connect_client(self, client_config):
        self._create_csv_data_from_file(client_config['riskiq_host_csv'])
        self._create_csv_data_from_file(client_config['riskiq_ip_csv'])
        self._create_csv_data_from_file(client_config['riskiq_url_csv'])
        return client_config

    def _query_devices_by_client(self, client_name, client_data):
        hosts = self._create_csv_data_from_file(client_data['riskiq_host_csv'])
        ips = self._create_csv_data_from_file(client_data['riskiq_ip_csv'])
        urls = self._create_csv_data_from_file(client_data['riskiq_url_csv'])
        return hosts, ips, urls

    @staticmethod
    def _clients_schema():
        """
        The schema EdfsCsvAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'riskiq_host_csv_label',
                    'title': 'Risk IQ Hosts CSV file CSV file name',
                    'type': 'string',
                },
                {
                    'name': 'riskiq_host_csv',
                    'title': 'Risk IQ Hosts CSV file',
                    'type': 'file',
                },
                {
                    'name': 'riskiq_ip_csv_label',
                    'title': 'Risk IQ IPs CSV file CSV file name',
                    'type': 'string'
                },
                {
                    'name': 'riskiq_ip_csv',
                    'title': 'Risk IQ IPs CSV file CSV file',
                    'type': 'file',
                },
                {
                    'name': 'riskiq_url_csv_label',
                    'title': 'Risk IQ URLs CSV file CSV file name',
                    'type': 'string',
                },
                {
                    'name': 'riskiq_url_csv',
                    'title': 'Risk IQ URLs CSV file',
                    'type': 'file',
                }

            ],
            'required': [
                'riskiq_host_csv_label',
                'riskiq_host_csv',
                'riskiq_ip_csv_label',
                'riskiq_ip_csv',
                'riskiq_url_csv_label',
                'riskiq_url_csv'
            ],
            'type': 'array'
        }

    # pylint: disable=too-many-branches, too-many-statements
    def _parse_raw_data(self, devices_raw_data):
        hosts, ips, urls = devices_raw_data
        for host_raw in hosts:
            try:
                device = self._new_device_adapter()
                if not host_raw.get('Host name') and not host_raw.get('Asset name'):
                    logger.warning(f'Bad device - host with no ID {host_raw}')
                    continue
                host_name = host_raw.get('Host name') or host_raw.get('Asset name')
                device.id = 'host_' + host_name + '_' + (host_raw.get('IP Addresses') or '')
                device.hostname = host_name
                ips_raw = host_raw.get('IP Addresses')
                if ips_raw:
                    ips_raw = [ip.strip() for ip in ips_raw.split(',')]
                    device.add_nic(ips=ips_raw)
                    for ip_public in ips_raw:
                        device.add_public_ip(ip_public)

                if host_raw.get('Brands'):
                    device.brands = [a.strip() for a in host_raw.get('Brands').split(',')]
                if host_raw.get('Web Component Names'):
                    device.web_component_names = [a.strip() for a in host_raw.get('Web Component Names').split(',')]
                device.set_raw(host_raw)
                yield device
            except Exception:
                logger.exception(f'Problem with host_raw {host_raw}')
        for ip_data in ips:
            try:
                device = self._new_device_adapter()
                if not ip_data.get('IP Address'):
                    logger.warning(f'Bad device - ip with no ID {ip_data}')
                    continue
                device.id = 'ips_' + ip_data.get('IP Address')
                device.add_public_ip(ip_data.get('IP Address'))
                device.add_nic(ips=[ip_data.get('IP Address')])
                if ip_data.get('Brands'):
                    device.brands = [a.strip() for a in ip_data.get('Brands').split(',')]
                if ip_data.get('Web Component Names'):
                    device.web_component_names = [a.strip() for a in ip_data.get('Web Component Names').split(',')]
                try:
                    device.asn = int(ip_data.get('ASN'))
                except Exception:
                    pass
                try:
                    if ip_data.get('Ports'):
                        ports = [int(a.strip()) for a in ip_data.get('Ports').split(',')]
                        for port in ports:
                            device.add_open_port(port_id=port)
                except Exception:
                    pass
                device.set_raw(ip_data)
                yield device
            except Exception:
                logger.exception(f'Problem with ip data {ip_data}')

        for url_data in urls:
            try:
                device = self._new_device_adapter()
                if not url_data.get('IP Addresses'):
                    logger.warning(f'Bad device - url with no ID {url_data}')
                    continue
                device.id = 'url_' + url_data.get('IP Addresses')
                ips_raw = url_data.get('IP Addresses')
                if ips_raw:
                    ips_raw = [ip.strip() for ip in ips_raw.split(',')]
                    device.add_nic(ips=ips_raw)
                    for ip_public in ips_raw:
                        device.add_public_ip(ip_public)
                if url_data.get('Brands'):
                    device.brands = [a.strip() for a in url_data.get('Brands').split(',')]
                device.url = url_data.get('URL')
                device.final_urls = url_data.get('Final URLs')
                try:
                    device.response_code = int(url_data.get('Response Codes'))
                except Exception:
                    pass
                try:
                    device.final_response_codes = int(url_data.get('Final Response Codes'))
                except Exception:
                    pass
                device.set_raw(url_data)
                yield device
            except Exception:
                logger.exception(f'Problem with url data {url_data}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
