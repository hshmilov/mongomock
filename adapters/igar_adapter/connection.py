import logging

# pylint: disable=import-error
import zeep
import zeep.helpers
import zeep.exceptions

from axonius.clients.rest.connection import RESTConnection
from igar_adapter.consts import DEVICE_PER_PAGE, MAX_NUMBER_OF_DEVICES

logger = logging.getLogger(f'axonius.{__name__}')


class IgarConnection(RESTConnection):
    """ SOAP client for IGAR adapter """

    def __init__(self,
                 domain,
                 *args,
                 **kwargs):
        super().__init__(*args,
                         domain=domain,
                         url_base_prefix='',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._client = None

    def _create_client(self):
        if not self._verify_ssl:
            self._session.verify = False
        if self._proxies:
            self._session.proxies = self._proxies
        transport = zeep.Transport(session=self._session)
        self._client = zeep.Client(wsdl=self._domain, transport=transport)

    def _connect(self):
        self._create_client()
        logger.info(f'Expecting {self._client.service.GetServerListFullCountAll()} results')

    def _get_server_count(self):
        response = self._client.service.GetServerListFullCountAll()
        try:
            return int(response)
        except Exception:
            logger.exception(f'Failed to get server list count. '
                             f'Assuming max ({MAX_NUMBER_OF_DEVICES})')
        return MAX_NUMBER_OF_DEVICES

    def _paginated_get_servers(self):
        dict_params = {
            'startIndex': 0,
            'itemsCount': DEVICE_PER_PAGE
        }
        skipped = 0
        max_results = min(self._get_server_count(), MAX_NUMBER_OF_DEVICES)
        result = True
        while result and dict_params['startIndex'] < max_results:
            index = dict_params['startIndex']
            logger.debug(f'Fetching servers from {index}')
            try:
                result = self._client.service.GetServerListFull(**dict_params)
            except zeep.exceptions.Fault:
                logger.debug(f'Exception trying to fetch devices after {index}', exc_info=True)
                if dict_params['itemsCount'] == 1:
                    logger.debug(f'Skipping device at index {index}')
                    dict_params = {
                        'startIndex': index + 1,
                        'itemsCount': DEVICE_PER_PAGE
                    }
                    skipped += 1
                else:
                    dict_params['itemsCount'] = int(dict_params['itemsCount'] / 2) or 1
                continue
            else:
                if not result:
                    break
                if isinstance(result, list):
                    logger.info(f'Yielding next {len(result)} devices from {index}')
                    yield from zeep.helpers.serialize_object(result, dict)
                else:
                    logger.error(f'Result is not a list: {result}')
                    raise TypeError(result)
                dict_params['startIndex'] += dict_params['itemsCount']
                dict_params['itemsCount'] = DEVICE_PER_PAGE
        logger.warning(f'Skipped {skipped} items due to server errors! '
                       f'See debug log for more information')

    def _paginated_get_equipment(self):
        dict_params = {
            'startIndex': 0,
            'itemsCount': DEVICE_PER_PAGE
        }
        skipped = 0
        max_results = MAX_NUMBER_OF_DEVICES
        result = True
        while result and dict_params['startIndex'] < max_results:
            index = dict_params['startIndex']
            logger.debug(f'Fetching network equipment from {index}')
            try:
                result = self._client.service.GetNetworkEquipmentList(**dict_params)
            except zeep.exceptions.Fault:
                logger.debug(f'Exception trying to fetch network equipment after {index}',
                             exc_info=True)
                if dict_params['itemsCount'] == 1:
                    logger.warning(f'Skipping network equipment at index {index}')
                    dict_params = {
                        'startIndex': index + 1,
                        'itemsCount': DEVICE_PER_PAGE
                    }
                    skipped += 1
                else:
                    dict_params['itemsCount'] = int(dict_params['itemsCount'] / 2) or 1
                continue
            else:
                if not result:
                    break
                if isinstance(result, list):
                    logger.info(f'Yielding next {len(result)} net eq from {index}')
                    yield from zeep.helpers.serialize_object(result, dict)
                else:
                    logger.error(f'Result is not a list: {result}')
                    raise TypeError(result)
                dict_params['startIndex'] += dict_params['itemsCount']
                dict_params['itemsCount'] = DEVICE_PER_PAGE
        logger.warning(f'Skipped {skipped} items due to server errors! '
                       f'See debug log for more information')

    def _paginated_get_apps(self, per_page=DEVICE_PER_PAGE):
        dict_params = {
            'startIndex': 0,
            'itemsCount': per_page
        }
        skipped = 0
        max_results = MAX_NUMBER_OF_DEVICES
        result = True
        while result and dict_params['startIndex'] < max_results:
            index = dict_params['startIndex']
            logger.debug(f'Fetching apps from {index}')
            try:
                result = self._client.service.GetApplicationListFull(**dict_params)
            except zeep.exceptions.Fault:
                logger.debug(f'Exception trying to fetch apps after {index}', exc_info=True)
                if dict_params['itemsCount'] == 1:
                    logger.warning(f'Skipping app at index {index}')
                    dict_params = {
                        'startIndex': index + 1,
                        'itemsCount': per_page
                    }
                    skipped += 1
                else:
                    dict_params['itemsCount'] = int(dict_params['itemsCount'] / 2) or 1
                continue
            else:
                if not result:
                    break
                if isinstance(result, list):
                    logger.info(f'Yielding next {len(result)} apps from {index}')
                    yield from zeep.helpers.serialize_object(result, dict)
                else:
                    logger.error(f'Result is not a list: {result}')
                    raise TypeError(result)
                dict_params['startIndex'] += dict_params['itemsCount']
                dict_params['itemsCount'] = per_page
        logger.warning(f'Skipped {skipped} items due to server errors! '
                       f'See debug log for more information')

    def _get_servers_to_apps_mapping(self):
        # response = self._client.service.GetApplicationOnServerFull
        mapping_list = self._client.service.GetApplicationOnServerFull()
        # mapping_list = response.GetApplicationOnServerFullResult.ServerApplications
        if isinstance(mapping_list, list):
            yield from zeep.helpers.serialize_object(mapping_list[:MAX_NUMBER_OF_DEVICES], dict)

    def get_all_data(self):
        # Actual get all data, in the same format as the csv
        return (
            self._paginated_get_servers(),
            self._get_servers_to_apps_mapping(),
            self._paginated_get_apps(4096),
            self._paginated_get_equipment()
        )

    def get_users_list(self):
        return (self._paginated_get_servers(),
                self._get_servers_to_apps_mapping(),
                self._paginated_get_apps(4096))

    def get_device_list(self):
        return self.get_all_data()
