import base64
import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException

logger = logging.getLogger(f'axonius.{__name__}')


class FreshServiceConnection(RESTConnection):
    def __init__(self, *args, **kwargs):
        """ Initializes a connection to FreshService using its rest API """
        super().__init__(url_base_prefix='/api/v2/', *args, **kwargs)
        base64_api_key = base64.b64encode(self._apikey.encode('utf-8')).decode('utf-8')
        self._permanent_headers = {'Authorization': base64_api_key,
                                   'Content-Type': 'application/json',
                                   'Accept': 'application/json'}

    def _connect(self):
        """
        Establish a connection by retreiving one page of tickets from Fresh Service.
        """

        # if username and password are not working with basic auth, you can base64 encode before auth header
        if self._apikey is not None:
            # will return the tickets of the last 30 days
            self._get('tickets')
        else:
            logger.exception('No username and password for connection to FreshService')
            raise RESTException('No username and password')

    def get_device_list(self):
        pass

    def create_fresh_service_incident(self, dict_data):
        if self._apikey is not None:
            try:
                self._post('tickets', body_params=dict_data)
            except Exception:
                logger.exception('Error occured when trying to create a ticket for fresh service')
                raise RESTException('Was unable to create a new ticket')
        else:
            logger.exception('No username and password to create ticket in FreshService')
            raise RESTException('No username and password')
