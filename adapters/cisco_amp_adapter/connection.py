import logging
from base64 import b64encode

from axonius.clients.rest.connection import RESTConnection, RESTException
from cisco_amp_adapter import consts

logger = logging.getLogger(f'axonius.{__name__}')


class CiscoAMPConnection(RESTConnection):
    def __init__(self, *args, client_id: str, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._client_id = client_id

    def _connect(self):
        """
        There is no need to authenticate the AMP account, so in _connect, we set the permanent headers
        for Basic HTTP Authentication.
        :return:
        """
        if self._client_id and self._apikey:
            try:
                authorize = b64encode((self._client_id + ':' + self._apikey).encode('utf-8')).decode('utf-8')
            except Exception:
                logger.exception('There was an error authorizing the client id and api key')
                raise RESTException('Unable to perform base encoding')

            self._permanent_headers = {'Authorization': f'Basic {authorize}'}
        else:
            raise RESTException('No API key or Client ID')

    def get_device_list(self):
        """
        Retreive the computers from the v1 api.
        Is it relevant to maintain the x-ratelimit-limit, reset and remaining
        :return: list of all devices.
        """
        try:
            raw_data = self._get('v1/computers', url_params={'offset': 0, 'limit': consts.DEVICES_PER_PAGE})
            yield from raw_data.get('data', [])
        except Exception:
            logger.exception(f'Incurred an error making a get request of v1/computers')
            raise RESTException('Incurred an error making a request for results and items per page')

        results = (raw_data.get('metadata') or {}).get('results')
        if results:
            devices_total = results.get('total')
        else:
            raise ValueError('Either not a value for results or total number of devices')

        count = consts.DEVICES_PER_PAGE

        while devices_total > count and consts.MAX_NUMBER_OF_DEVICES > count:
            try:
                raw_data = self._get('v1/computers', url_params={'offset': count, 'limit': consts.DEVICES_PER_PAGE})
                yield from raw_data.get('data', [])
            except Exception:
                logger.exception(f'Incurred an error making a get request of v1/computers')
            count += consts.DEVICES_PER_PAGE
