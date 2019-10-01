import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from randori_adapter.consts import DEVICE_PER_PAGE, MAX_NUMBER_OF_DEVICES

logger = logging.getLogger(f'axonius.{__name__}')


class RandoriConnection(RESTConnection):
    """ rest client for Randori adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='recon/api/v1',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._permanent_headers['Authorization'] = self._apikey

    def _connect(self):
        if not self._apikey:
            raise RESTException('No API Key')
        self._get('hostname', url_params={'limit': DEVICE_PER_PAGE, 'offset': 0})

    def _get_api_endpoint(self, endpoint):
        offset = 0
        response = self._get(endpoint, url_params={'limit': DEVICE_PER_PAGE, 'offset': offset})
        yield from response['data']
        total = response['total']
        offset += DEVICE_PER_PAGE
        while offset < min(total, MAX_NUMBER_OF_DEVICES):
            try:
                response = self._get(endpoint, url_params={'limit': DEVICE_PER_PAGE, 'offset': offset})
                if not response.get('data'):
                    break
                yield from response['data']
                offset += DEVICE_PER_PAGE
            except Exception:
                logger.exception(f'Probelm with offset {offset}')
                break

    def get_device_list(self):
        port_info_dict = dict()
        try:
            for port_info_raw in self._get_api_endpoint('ports-for-ip'):
                if port_info_raw.get('ip_id'):
                    if not port_info_raw.get('ip_id') in port_info_dict:
                        port_info_dict[port_info_raw.get('ip_id')] = []
                    port_info_dict[port_info_raw.get('ip_id')].append(port_info_raw)
        except Exception:
            logger.exception(f'Problem getting ips data')

        ips_data_dict = dict()
        try:
            for ip_info_raw in self._get_api_endpoint('ip'):
                if ip_info_raw.get('id'):
                    ips_data_dict[ip_info_raw.get('id')] = ip_info_raw
        except Exception:
            logger.exception(f'Problem getting ips data')
        hostname_to_ip_dict = dict()
        try:
            for hostname_ip_info_raw in self._get_api_endpoint('hostnames-for-ip'):
                if hostname_ip_info_raw.get('hostname_id') and hostname_ip_info_raw.get('ip_id'):
                    if not hostname_ip_info_raw.get('hostname_id') in hostname_to_ip_dict:
                        hostname_to_ip_dict[hostname_ip_info_raw.get('hostname_id')] = []
                    hostname_to_ip_dict[hostname_ip_info_raw.get('hostname_id')].\
                        append(hostname_ip_info_raw.get('ip_id'))
        except Exception:
            logger.exception('Problem getting IP inifo')
        for device_raw in self._get_api_endpoint('hostname'):
            yield device_raw, hostname_to_ip_dict, ips_data_dict, port_info_dict
