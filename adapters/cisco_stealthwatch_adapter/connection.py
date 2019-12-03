import logging

from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from cisco_stealthwatch_adapter.consts import REST_PATH_LOGOUT, REST_PATH_AUTH, REST_PATH_EXPORTERS

logger = logging.getLogger(f'axonius.{__name__}')


class CiscoStealthwatchConnection(RESTConnection):
    """ rest client for CiscoStealthwatch adapter """

    def __init__(self, *args, tenant: str = '0', **kwargs):
        super().__init__(*args, url_base_prefix='',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._tenant_id = tenant

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')
        try:
            auth_data = {'username': self._username, 'password': self._password}
            logger.debug(f'Getting auth cookie from {self._domain} using POST to {REST_PATH_AUTH}')
            self._post(REST_PATH_AUTH,
                       body_params=auth_data,
                       use_json_in_body=False,
                       extra_headers={'Content-Type': 'application/x-www-form-urlencoded'})
        except RESTException as e:
            message = f'Error connecting to Cisco Stealthwatch Management: {str(e)}'
            logger.exception(message)
            raise ClientConnectionException(message)

    def get_device_list(self):
        """
        Get list of exporters for each tenant
        :return:
        """
        try:
            logger.debug(f'Trying to fetch exporters')
            url = REST_PATH_EXPORTERS.format(tenant_id=self._tenant_id)
            yield from self._get(url)['data']
        except RESTException as e:
            message = f'Failed to get exporters (devices)'
            logger.exception(message)

    # pylint: disable=W0150
    def close(self):
        """
        Close the session, deleting the token.
        """
        try:
            logger.debug(f'Trying to kill session with {self._domain} using DELETE to {REST_PATH_LOGOUT}')
            self._delete(REST_PATH_LOGOUT, extra_headers={'Content-Type': 'application/x-www-form-urlencoded'},
                         use_json_in_respone=False)
        except RESTException as e:
            message = f'Error DISconnecting from Cisco Stealthwatch Management: {str(e)}'
            logger.exception(message)
        else:
            logger.debug(f'Successfully closed auth token to {self._domain}')
        finally:
            return super().close()
