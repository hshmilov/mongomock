import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from axonius.clients.ivanti_sm.consts import MAX_NUMBER_OF_PAGES, DEVICE_PER_PAGE

logger = logging.getLogger(f'axonius.{__name__}')


class IvantiSmConnection(RESTConnection):
    """ rest client for IvantiSm adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='api',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._permanent_headers['Authorization'] = f'rest_api_key={self._apikey}'

    def _connect(self):
        if not self._apikey:
            raise RESTException('No API Key')
        self._get('odata/businessobject/CI__computers')

    def _get_business_object(self, business_object):
        skip = 0
        response = self._get(f'odata/businessobject/{business_object}',
                             url_params={'$top': DEVICE_PER_PAGE, '$skip': skip})
        if not isinstance(response, dict) or not response.get('value') or not isinstance(response['value'], list):
            raise RESTException(f'Bad Response: {response}')
        count = response.get('@odata.count')
        logger.info(f'Count is: {count}')
        yield from response['value']
        skip += DEVICE_PER_PAGE
        while skip < min(count, MAX_NUMBER_OF_PAGES):
            try:
                response = self._get(f'odata/businessobject/{business_object}',
                                     url_params={'$top': DEVICE_PER_PAGE, '$skip': skip})
                if not isinstance(response, dict) or not response.get('value')\
                        or not isinstance(response['value'], list):
                    raise RESTException(f'Bad Response: {response}')
                yield from response['value']
                skip += DEVICE_PER_PAGE
            except Exception:
                logger.exception(f'Problem with skip {skip}')
                break

    def get_user_list(self):
        yield from self._get_business_object('Employees')

    def get_device_list(self):
        yield from self._get_business_object('CI__computers')

    def create_ivanti_sm_computer(self, connection_dict):
        logger.info(f'Creating computer')
        try:
            device_raw = self._post(f'odata/businessobject/CI__computers', body_params=connection_dict)
            return True, device_raw
        except Exception:
            logger.exception(f'Exception while creating computer with connection dict {connection_dict}')
            return False, None

    def uptade_ivanti_sm_computer(self, connection_dict):
        rec_id = connection_dict['RecId']
        logger.info(f'Updating computer')
        try:
            device_raw = self._put(f'odata/businessobject/CI__computers(‘{rec_id}‘)',
                                   body_params=connection_dict)
            return True, device_raw
        except Exception:
            logger.exception(f'Exception while creating incident with connection dict {connection_dict}')
            return False, None
