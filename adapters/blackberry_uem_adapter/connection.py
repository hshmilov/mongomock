import base64
import logging

import requests

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException

logger = logging.getLogger(f'axonius.{__name__}')


class BlackberryUemConnection(RESTConnection):
    def __init__(self, *args, username_domain: str = '', **kwargs):
        super().__init__(*args, **kwargs)
        self._username_domain = username_domain

    def _connect(self):
        if self._username and self._password:
            auth_dict = {'username': self._username, 'password': base64.b64encode(
                bytearray(self._password, 'utf-8')).decode('utf-8')}
            if self._username_domain is None:
                auth_dict['provider'] = 'LOCAL'
            else:
                auth_dict['domain'] = self._username_domain
                auth_dict['provider'] = 'AD'
            try:
                response = self._session.post(self._get_url_request('util/authorization'),
                                              json=auth_dict,
                                              headers={'Content-Type':
                                                       'application/vnd.blackberry.authorizationrequest-v1+json'},
                                              verify=self._verify_ssl,
                                              timeout=self._session_timeout,
                                              proxies=self._proxies)
                response.raise_for_status()
                self._session_headers['Authorization'] = response.text
                self._get('devices')
            except requests.HTTPError as e:
                raise RESTException(str(e))
        else:
            raise RESTException('No user name or password')

    def get_device_list(self):
        devices_raw = self._get('devices')['devices']
        async_requests = []
        async_requests_devices = []

        for device_raw in devices_raw:
            try:
                device_links = device_raw.get('links')
                for link in device_links:
                    if link['rel'] == 'userDevice':
                        if link.get('href') is not None:
                            user_device_url = link['href']
                            async_requests.append(
                                {
                                    'name': f'{user_device_url}/applications',
                                    'force_full_url': True
                                }
                            )
                            async_requests_devices.append(device_raw)

                        else:
                            logger.error(f'Error, device {device_raw} does not have a href, cant get apps. yielding '
                                         f'it without apps')
                            yield device_raw
            except Exception:
                logger.exception(f'Problem getting applications for device : {device_raw}')

        for device_raw, device_apps_response in zip(async_requests_devices, self._async_get(async_requests)):
            if self._is_async_response_good(device_apps_response):
                device_apps_response = device_apps_response.get('deviceApplications')
                if device_apps_response is not None:
                    device_raw['applications'] = device_apps_response
            else:
                logger.error(f'error fetching devices apps for some device, '
                             f'response is {device_apps_response} and devices is {device_raw}')
            yield device_raw
