import base64
import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from kaspersky_sc_adapter.consts import MAX_NUMBER_OF_DEVICES, DEVICE_PER_PAGE

logger = logging.getLogger(f'axonius.{__name__}')


class KasperskyScConnection(RESTConnection):
    """ rest client for KasperskySc adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='api/v1.0',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')
        username = base64.b64encode(self._username.encode('utf-8')).decode('utf-8')
        password = base64.b64encode(self._password.encode('utf-8')).decode('utf-8')
        internal = '1'
        extra_headers = {
            'Authorization': 'KSCBasic user="' + username +
                             '", pass="' + password + '", internal="' + internal + '"'
        }
        try:
            self._post('login',
                       body_params={},
                       extra_headers=extra_headers)
        except Exception:
            internal = '0'
            extra_headers = {
                'Authorization': 'KSCBasic user="' + username +
                                 '", pass="' + password + '", internal="' + internal + '"'
            }
            self._post('login',
                       body_params={},
                       extra_headers=extra_headers)

    def _get_group_hosts(self, group_id):
        url = 'HostGroup.FindHosts'
        body_params = {'wstrFilter': '(KLHST_WKS_GROUPID = ' + str(group_id) + ')',
                       'vecFieldsToReturn': ['KLHST_WKS_FQDN', 'KLHST_WKS_HOSTNAME', 'KLHST_WKS_IP_LONG',
                                             'KLHST_WKS_LAST_VISIBLE',
                                             'KLHST_WKS_WINDOMAIN', 'KLHST_WKS_STATUS_MASK', 'KLHST_WKS_STATUS'],
                       'lMaxLifeTime': 100}
        response = self._post(url,
                              body_params=body_params)
        if 'strAccessor' in response:
            hosts_str_accessor = response['strAccessor']
            yield from self._get_search_results(hosts_str_accessor)

    def _get_apps_for_host(self, device_id):
        products = dict()
        try:
            url = 'HostGroup.GetHostProducts'
            body_params = {'strHostName': device_id}
            response = self._post(url, body_params=body_params)
            product_data = response['PxgRetVal']
            for product in product_data:
                major_ver = list(product_data[product]['value'].keys())[0]
                if 'DisplayName' in product_data[product]['value'][major_ver]['value']:
                    name = product_data[product]['value'][major_ver]['value']['DisplayName']
                else:
                    name = product
                products[name] = dict()
                if 'ProdVersion' in product_data[product]['value'][major_ver]['value']:
                    products[name]['version'] = product_data[product]['value'][major_ver]['value']['ProdVersion']
                else:
                    products[name]['version'] = major_ver
        except Exception:
            logger.exception(f'Problem getting apps for {device_id}')
        return products

    def _get_details_for_host(self, device_id):
        try:
            url = 'HostGroup.GetHostInfo'
            body_params = {'strHostName': device_id,
                           'pFields2Return': ['KLHST_WKS_OS_NAME',
                                              'KLHST_WKS_LAST_FULLSCAN',
                                              'KLHST_WKS_VIRUS_COUNT',
                                              ]}

            response = self._post(url, body_params=body_params)
            return response['PxgRetVal']
        except Exception:
            logger.exception(f'Problem getting details for {device_id}')
            return {}

    def get_device_list(self):
        body_params = {'wstrFilter': '', 'vecFieldsToReturn': ['id', 'name'], 'lMaxLifeTime': 100}
        response = self._post('HostGroup.FindGroups',
                              body_params=body_params)
        if 'strAccessor' not in response:
            raise RESTException(f'Bad Groups Data Response: {response}')
        groups_str_accessor = response['strAccessor']
        groups = self._get_search_results(groups_str_accessor)
        for group in groups:
            try:
                group_id = group['value']['id']
                for device_raw in self._get_group_hosts(group_id):
                    try:
                        device_id = device_raw['value']['KLHST_WKS_HOSTNAME']
                        device_raw['apps'] = self._get_apps_for_host(device_id)
                        device_raw['details'] = self._get_details_for_host(device_id)
                        yield device_raw
                    except Exception:
                        logger.exception(f'Problem with device_raw {device_raw}')
            except Exception:
                logger.exception(f'Problem with group {group}')

    def _get_search_results(self, str_accessor):
        body_params = {'strAccessor': str_accessor}
        response = self._post('ChunkAccessor.GetItemsCount',
                              body_params=body_params)
        items_count = response['PxgRetVal']
        start = 0
        step = DEVICE_PER_PAGE
        while start < min(items_count, MAX_NUMBER_OF_DEVICES):
            try:
                body_params = {'strAccessor': str_accessor,
                               'nStart': start, 'nCount': DEVICE_PER_PAGE}
                response = self._post('ChunkAccessor.GetItemsChunk',
                                      body_params=body_params)
                yield from response['pChunk']['KLCSP_ITERATOR_ARRAY']
                start += step
            except Exception:
                logger.exception(f'Problem with offset {start}')
                break
