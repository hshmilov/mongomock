import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from snow_adapter.consts import MAX_DEVICES_COUNT, DEVICE_PER_PAGE

logger = logging.getLogger(f'axonius.{__name__}')


class SnowConnection(RESTConnection):
    """ rest client for Snow adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='api',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')
        self._get('customers/',
                  do_basic_auth=True,
                  url_params={'$format': 'json',
                              '$top': DEVICE_PER_PAGE})

    def _get_api_paginated(self, endpoint):
        skip = 0
        while skip < MAX_DEVICES_COUNT:
            try:
                logger.info(f'Endpoint {endpoint} with skip {skip}')
                url_params = {'$format': 'json',
                              '$top': DEVICE_PER_PAGE}
                if skip > 0:
                    url_params['$skip'] = skip
                response = self._get(endpoint,
                                     do_basic_auth=True,
                                     url_params=url_params
                                     )
                if not isinstance(response.get('Body'), list):
                    raise RESTException(f'API call {endpoint} has not returned a list')
                yield from response.get('Body')
                if len(response.get('Body')) < DEVICE_PER_PAGE:
                    break
                skip += DEVICE_PER_PAGE
            except Exception:
                logger.exception(f'Problem with skip {skip}')
                if skip == 0:
                    raise
                break

    def _get_customers_ids(self):
        for customer_raw in self._get_api_paginated('customers/'):
            customer_id = self._get_obj_id(customer_raw)
            if customer_id:
                yield customer_id

    def _get_apps(self, device_id, customer_id):
        apps = []
        try:
            for app_raw in self._get_api_paginated(f'customers/{customer_id}/computers/{device_id}/applications/'):
                apps.append(app_raw.get('Body'))
        except Exception:
            logger.exception(f'Problem getting app for {device_id} of customer {customer_id}')
        return apps

    @staticmethod
    def _get_obj_id(snow_obj):
        if isinstance(snow_obj, dict) and \
                isinstance(snow_obj.get('Body'), dict) and snow_obj['Body'].get('Id'):
            return snow_obj['Body'].get('Id')
        return None

    # pylint: disable=arguments-differ
    def get_device_list(self, fetch_apps=True):
        for customer_id in self._get_customers_ids():
            try:
                for computer_raw in self._get_api_paginated(f'customers/{customer_id}/computers/'):
                    device_id = self._get_obj_id(computer_raw)
                    if device_id:
                        device_raw = computer_raw['Body']
                        if fetch_apps is True:
                            device_raw['application_raw'] = self._get_apps(device_id=device_id, customer_id=customer_id)
                        else:
                            device_raw['application_raw'] = []
                        yield device_raw
            except Exception:
                logger.exception(f'Problem with customer id {customer_id}')
