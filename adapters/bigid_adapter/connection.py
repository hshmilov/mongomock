import logging
from urllib3.util.url import parse_url

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from bigid_adapter.consts import DEVICE_PER_PAGE, MAX_NUMBER_OF_DEVICES
from bigid_adapter.structures import CatalogData


logger = logging.getLogger(f'axonius.{__name__}')


class BigidConnection(RESTConnection):
    """ rest client for Bigid adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='api/v1',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')
        resposne = self._post('sessions', body_params={'username': self._username, 'password': self._password})
        if not isinstance(resposne, dict) or not resposne.get('auth_token'):
            raise RESTException(f'Bad response: {resposne}')
        token = resposne['auth_token']
        self._session_headers['authorization'] = token
        self._get('data-catalog/', url_params={'format': 'json', 'offset': 0, 'limit': DEVICE_PER_PAGE})

    def _paginated_api_get(self, api_endpoint, object_name):
        try:
            offset = 0
            while offset < MAX_NUMBER_OF_DEVICES:
                try:
                    response = self._get(api_endpoint,
                                         url_params={'format': 'json', 'offset': offset, 'limit': DEVICE_PER_PAGE})
                    yield from response.get(object_name)
                    if len(response.get(object_name)) < DEVICE_PER_PAGE:
                        break
                    offset += DEVICE_PER_PAGE
                except Exception:
                    logger.exception(f'Problem at offset {offset}')
                    if offset == 0:
                        raise
                    break

        except Exception:
            logger.exception(f'Invalid request made while paginating devices')
            raise

    # pylint: disable=too-many-branches, too-many-statements, too-many-locals, too-many-nested-blocks
    @staticmethod
    def _parse_catalog_raw(catalog_raw: dict, source_dict: dict, risks_dict: dict):
        hostname = None
        ip = None
        catalog_data = CatalogData()
        try:
            catalog_data.open_access = catalog_raw.get('open_access')
            catalog_data.container_name = catalog_raw.get('containerName')
            catalog_data.object_type = catalog_raw.get('objectType')
            catalog_data.full_object_name = catalog_raw.get('fullObjectName')
            catalog_data.source = catalog_raw.get('source')
            catalog_data.catalog_name = catalog_raw.get('objectName')
            catalog_data.scanner_type_group = catalog_raw.get('scanner_type_group')
            catalog_data.total_pii_count = catalog_raw.get('total_pii_count') \
                if isinstance(catalog_raw.get('total_pii_count'), int) else None
            catalog_data.attribute_list = catalog_raw.get('attribute') \
                if isinstance(catalog_raw.get('attribute'), list) else None

            source = catalog_raw.get('source')
            source_key = None
            if source in source_dict.keys():
                source_key = source
            dup_key = False
            if not source_key:
                for source_key_potential in source_dict.keys():
                    if source in source_key_potential:
                        if source_key:
                            dup_key = True
                        source_key = source_key_potential
            if source_key and source_dict.get(source_key) and not dup_key:
                source_raw = source_dict.get(source_key)
                risk_raw = risks_dict.get(source_key)
                if risk_raw and risk_raw.get('avg') and isinstance(risk_raw.get('avg'), int):
                    catalog_data.avg = risk_raw.get('avg')
                hostname = source_raw.get('rdb_url')
                if hostname:
                    hostname = parse_url(hostname).host
        except Exception:
            logger.exception(f'Failed creating instance for catalog {catalog_raw}')
        return catalog_data, hostname

    def get_device_list(self):
        source_dict = dict()
        devices_dict = dict()
        risks_dict = dict()
        try:
            for risk_raw in self._paginated_api_get('sourceRisks', 'source_risks'):
                risks_dict[risk_raw.get('name')] = risk_raw
        except Exception:
            logger.exception(f'Problem getting risk data')
        try:
            for source_raw in self._paginated_api_get('ds_connections', 'ds_connections'):
                source_dict[source_raw.get('name')] = source_raw
        except Exception:
            logger.exception(f'Problem getting source data')
        try:
            for catalog_raw in self._paginated_api_get('data-catalog/', 'results'):
                catalog_data, hostname = self._parse_catalog_raw(catalog_raw, source_dict, risks_dict)
                if hostname:
                    if hostname not in devices_dict:
                        devices_dict[hostname] = []
                    devices_dict[hostname].append(catalog_data)
        except RESTException as err:
            logger.exception(str(err))
            raise
        yield from devices_dict.items()
