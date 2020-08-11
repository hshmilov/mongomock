import datetime
import logging
import time

from retrying import retry

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from bluecat_adapter.consts import DEVICE_PER_PAGE

logger = logging.getLogger(f'axonius.{__name__}')


class BluecatConnection(RESTConnection):
    """ rest client for Bluecat adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='Services/REST/v1',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'}, **kwargs)
        self.sleep_between_requests_in_sec = None
        self._token_time = None
        self._device_per_page = DEVICE_PER_PAGE

    # pylint: disable=arguments-differ
    def _do_request(self, *args, **kwargs):
        if self.sleep_between_requests_in_sec and isinstance(self.sleep_between_requests_in_sec, int):
            time.sleep(self.sleep_between_requests_in_sec)
        return super()._do_request(*args, **kwargs)

    def _refresh_token(self):
        seconds_in_last_minute = 59
        if self.sleep_between_requests_in_sec \
                and isinstance(self.sleep_between_requests_in_sec, int) and self.sleep_between_requests_in_sec < 60:
            seconds_in_last_minute = 59 - self.sleep_between_requests_in_sec
        if self._token_time and \
                (datetime.datetime.now() - self._token_time) \
                < datetime.timedelta(minutes=4, seconds=seconds_in_last_minute):
            return
        logger.info('Do token request')
        try:
            response = self._get(f'login?username={self._username}&password={self._password}',
                                 use_json_in_response=False)
        except Exception:
            logger.exception('Authentication Error')
            raise RESTException('Authentication Error')
        response = str(response)
        if 'ERROR' in response:
            raise RESTException('Bad Authentication')
        if '->' not in response or '<-' not in response:
            raise RESTException(f'Bad Response for login: {response}')
        index_start = response.index('->') + len('->')
        index_end = response.index('<-')
        if index_end <= index_start:
            raise RESTException(f'Got Empty Token: {response}')
        token = response[index_start:index_end].strip()
        if not token:
            raise RESTException(f'Got Empty Token: {response}')
        self._session_headers['Authorization'] = token
        self._token_time = datetime.datetime.now()

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')
        self._token_time = None
        self._refresh_token()

    @retry(stop_max_attempt_number=3, wait_fixed=5000)
    def _get_page(self, method: str, url_params):
        self._refresh_token()
        return self._get(method, url_params=url_params)

    def _get_paginated(self, method: str, url_params: dict):
        if 'start' not in url_params:
            url_params['start'] = 0
        if 'count' not in url_params:
            url_params['count'] = self._device_per_page
        results = self._get_page(method, url_params=url_params)

        while results:
            yield from results
            url_params['start'] = url_params['start'] + len(results)
            results = self._get_page(method, url_params=url_params)

    def _get_entities(self, parent_id: int, object_type: str):
        yield from self._get_paginated('getEntities', {'parentId': parent_id, 'type': object_type})

    def get_blocks_recursively(self, parent_id):
        for ip4block in self._get_entities(parent_id, 'IP4Block'):
            if 'id' not in ip4block:
                logger.error(f'Bad ip4block: {ip4block}')
                continue

            yield ip4block['id']
            yield from self.get_blocks_recursively(ip4block['id'])

    # pylint: disable=R0912,arguments-differ, too-many-statements
    def get_device_list(self, sleep_between_requests_in_sec, get_extra_host_data=True, device_per_page=None):
        self.sleep_between_requests_in_sec = sleep_between_requests_in_sec
        if device_per_page:
            self._device_per_page = device_per_page
        else:
            self._device_per_page = DEVICE_PER_PAGE

        ip4_blocks = set()

        # 1. List all configurations
        for configuration in self._get_entities(0, 'Configuration'):
            if 'id' not in configuration:
                logger.error(f'Bad configuration: {configuration}')
                continue
            # 2. List all blocks recursively
            for ip4_block_id in self.get_blocks_recursively(configuration['id']):
                ip4_blocks.add(ip4_block_id)

        ip4_blocks = list(ip4_blocks)
        logger.info(f'Got {len(ip4_blocks)} blocks')

        networks_ids = set()
        networks_raw = dict()
        for ip4_block_id in ip4_blocks:
            for ip4network in self._get_entities(ip4_block_id, 'IP4Network'):
                if 'id' not in ip4network:
                    logger.error(f'Bad IP4Network: {ip4network}')
                    continue
                networks_ids.add(ip4network['id'])
                networks_raw[ip4network['id']] = ip4network

        # pylint: disable=R1702
        networks_ids = list(networks_ids)
        logger.info(f'Got {len(networks_ids)} networks')
        for i, network_id in enumerate(networks_ids):
            try:
                if i % 100 == 0:
                    logger.info(f'Got networks count {i}')
                self._refresh_token()
                for device_raw in self._get_entities(network_id, 'IP4Address'):
                    try:
                        device_raw['network'] = networks_raw.get(network_id) or {}
                        host_id = device_raw.get('id')
                        if host_id and get_extra_host_data:
                            self._refresh_token()
                            dns_name_raw = self._get(f'getLinkedEntities?entityId={host_id}&type=HostRecord&'
                                                     f'start=0&count={self._device_per_page}')

                            if isinstance(dns_name_raw, list) and len(dns_name_raw) > 0:
                                device_raw['all_dns_names'] = dns_name_raw

                                # Optimize
                                if len(dns_name_raw) == 1:
                                    device_raw['dns_name'] = dns_name_raw[0].get('name')
                                    yield device_raw
                                    continue

                                # Otherwise if we have more than 1 in the list, we have to find the real one

                                real_dns_name = None
                                device_name = device_raw.get('name')

                                # First, compare to the 'name' attribute if it exists
                                if isinstance(device_name, str) and device_name:
                                    for dns_candidate in dns_name_raw:
                                        if dns_candidate.get('name').lower() == device_name.lower():
                                            real_dns_name = dns_candidate.get('name')
                                            break

                                # Second, take the first one which is not ttl=0 in it
                                if not real_dns_name:
                                    for dns_candidate in dns_name_raw:
                                        properties = dns_candidate.get('properties')
                                        if isinstance(properties, str) and 'ttl=0' not in properties:
                                            real_dns_name = dns_candidate.get('name')
                                            break

                                # Otherwise just take the first one
                                if not real_dns_name:
                                    real_dns_name = dns_name_raw[0].get('name')

                                device_raw['dns_name'] = real_dns_name
                    except Exception:
                        logger.exception(f'Problem getting dns name for {device_raw}')
                    yield device_raw
            except Exception:
                logger.exception(f'Problem getting network id {network_id}')
