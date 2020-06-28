import logging

# pylint: disable=import-error
import zeep
import zeep.helpers

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
            logger.exception(f'Failed to get server list count. Assuming max ({MAX_NUMBER_OF_DEVICES})')
        return MAX_NUMBER_OF_DEVICES

    def _paginated_get_servers(self):
        dict_params = {
            'startIndex': 0,
            'itemsCount': DEVICE_PER_PAGE
        }
        max_results = min(self._get_server_count(), MAX_NUMBER_OF_DEVICES)
        # response = self._client.service.GetServerListFull(**dict_params)
        # result = response.GetServerListFullResult.ServerFullInfo
        result = self._client.service.GetServerListFull(**dict_params)
        while result and dict_params['startIndex'] < max_results:
            logger.info(f'Yielding servers from {dict_params["startIndex"]}')
            if isinstance(result, list):
                yield from zeep.helpers.serialize_object(result, dict)
            else:
                logger.error(f'Result is not a list: {result}')
                raise TypeError(result)
            dict_params['startIndex'] += DEVICE_PER_PAGE
            # response = self._client.service.GetServerListFull(**dict_params)
            # result = response.GetServerListFullResult.ServerFullInfo
            result = self._client.service.GetServerListFull(**dict_params)

    def _paginated_get_equipment(self):
        dict_params = {
            'startIndex': 0,
            'itemsCount': DEVICE_PER_PAGE
        }
        max_results = MAX_NUMBER_OF_DEVICES
        result = self._client.service.GetNetworkEquipmentList(**dict_params)
        while result and dict_params['startIndex'] < max_results:
            logger.info(f'Yielding Network Equipment from {dict_params["startIndex"]}')
            if isinstance(result, list):
                yield from zeep.helpers.serialize_object(result, dict)
            else:
                logger.error(f'Result is not a list: {result}')
                raise TypeError(result)
            dict_params['startIndex'] += DEVICE_PER_PAGE
            # response = self._client.service.GetServerListFull(**dict_params)
            # result = response.GetServerListFullResult.ServerFullInfo
            result = self._client.service.GetNetworkEquipmentList(**dict_params)

    def _paginated_get_apps(self):
        dict_params = {
            'startIndex': 0,
            'itemsCount': DEVICE_PER_PAGE
        }
        max_results = MAX_NUMBER_OF_DEVICES
        # response = self._client.service.GetApplicationListFull(**dict_params)
        # result = response.GetApplicationListFullResult.ApplicationFullInfo
        result = self._client.service.GetApplicationListFull(**dict_params)
        while result and dict_params['startIndex'] < max_results:
            logger.info(f'Yielding apps from {dict_params["startIndex"]}')
            if isinstance(result, list):
                yield from zeep.helpers.serialize_object(result, dict)
            else:
                logger.error(f'Result is not a list: {result}')
                raise TypeError(result)
            dict_params['startIndex'] += DEVICE_PER_PAGE
            # response = self._client.service.GetApplicationListFull(**dict_params)
            # result = response.GetApplicationListFullResult.ApplicationFullInfo
            result = self._client.service.GetApplicationListFull(**dict_params)

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
            self._paginated_get_apps(),
            self._paginated_get_equipment()
        )

    def get_users_list(self):
        return self._paginated_get_servers(), self._get_servers_to_apps_mapping(), self._paginated_get_apps()

    def get_device_list(self):
        return self.get_all_data()
