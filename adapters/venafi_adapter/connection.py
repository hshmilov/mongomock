import logging
from typing import Optional

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from venafi_adapter.consts import CERTIFICATE_PER_PAGE, MAX_NUMBER_OF_CERTIFICATES, AUTHENTICATION_URL_SUFFIX, \
    CERT_API_SUFFIX, DEFAULT_ASYNC_CHUNKS

logger = logging.getLogger(f'axonius.{__name__}')


# pylint: disable=logging-format-interpolation


class VenafiConnection(RESTConnection):
    """ rest client for Venafi adapter """

    def __init__(self, *args, auth_domain: Optional[str] = None, client_id: str, **kwargs):
        super().__init__(*args, url_base_prefix='',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)

        self._auth_domain = auth_domain
        self._client_id = client_id

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')

        try:
            body_params = {
                'username': self._username,
                'password': self._password,
                'client_id': self._client_id,
            }
            extra_headers = {
                'Content-Type': 'application/x-www-form-urlencoded'
            }

            if self._auth_domain:
                url = f'{self._auth_domain}/{AUTHENTICATION_URL_SUFFIX}'
                response = self._post(url, body_params=body_params, force_full_url=True, use_json_in_body=False,
                                      extra_headers=extra_headers)
            else:
                response = self._post(AUTHENTICATION_URL_SUFFIX, body_params=body_params, use_json_in_body=False,
                                      extra_headers=extra_headers)

            if not (isinstance(response, dict) and response.get('access_token')):
                message = f'Invalid response from the server while getting token {response}'
                logger.error(message)
                raise RESTException(message)

            self._token = response.get('access_token')
            self._session_headers['Authorization'] = f'Bearer {self._token}'

            body_params = {
                'limit': 1,  # Results to display
                'offset': 0  # Results to skip
            }
            self._get(CERT_API_SUFFIX, body_params=body_params)

        except Exception as e:
            raise RESTException(f'Error: Invalid response from server, please check domain or credentials. {str(e)}')

    def _get_certificates_ids(self):
        try:
            certificates_ids = set()

            body_params = {
                'limit': CERTIFICATE_PER_PAGE,
                'offset': 0
            }

            while len(certificates_ids) <= MAX_NUMBER_OF_CERTIFICATES:
                response = self._get(CERT_API_SUFFIX, body_params=body_params)
                if not (isinstance(response, dict) and isinstance(response.get('Certificates'), list)):
                    logger.warning(f'Received invalid response while paginating. {response}')
                    return []

                certificates = response.get('Certificates')
                for certificate in certificates:
                    if isinstance(certificate, dict) and certificate.get('ID'):
                        certificates_ids.add(certificate.get('ID'))

                if len(certificates) != CERTIFICATE_PER_PAGE:
                    logger.info(f'Stopped due to small page response {len(certificates)}')
                    break

                body_params['offset'] += CERTIFICATE_PER_PAGE

            logger.info(f'Got total of {len(certificates_ids)} certificates')
            return certificates_ids
        except Exception:
            logger.exception(f'Invalid request made while paginating certificates', exc_info=True)
            raise

    def _async_paginated_certificate_get(self, async_chunks: int):
        try:
            certificates = self._get_certificates_ids()

            user_raw_requests = []
            for certificate_id in certificates:
                user_raw_requests.append({
                    'name': f'{CERT_API_SUFFIX}/{certificate_id}',
                })

            for response in self._async_get(user_raw_requests, retry_on_error=True, chunks=async_chunks):
                if not self._is_async_response_good(response):
                    logger.error(f'Async response returned bad, its {response}')
                    continue

                if not (isinstance(response, dict) and response.get('id')):
                    logger.warning(f'Invalid response returned: {response}')
                    continue

                yield response

        except Exception:
            logger.exception(f'Invalid request made while async paginating certificates')
            raise

    # pylint: disable=arguments-differ
    def get_device_list(self, async_chunks: int = DEFAULT_ASYNC_CHUNKS):
        try:
            yield from self._async_paginated_certificate_get(async_chunks)
        except RESTException as err:
            logger.exception(str(err))
            raise
