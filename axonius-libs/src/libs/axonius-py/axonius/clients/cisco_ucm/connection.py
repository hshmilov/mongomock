import logging
import os

import zeep
import zeep.helpers
from requests.auth import HTTPBasicAuth

from axonius.clients.cisco_ucm.consts import MAX_NUMBER_OF_DEVICES, BINDING, DOMAIN_URL, WSDL_PATH
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from axonius.utils.parsing import parse_bool_from_raw

logger = logging.getLogger(f'axonius.{__name__}')

CURRENT_PATH = os.path.abspath(os.path.dirname(__file__))


class CiscoUcmConnection(RESTConnection):
    """ rest client for CiscoUcm adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='',
                         **kwargs)
        self._wsdl = os.path.join(CURRENT_PATH, WSDL_PATH)
        self._domain = self._domain.strip('http://').strip('https://')

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')

        if not self._verify_ssl:
            self._session.verify = False
        if self._proxies:
            self._session.proxies = self._proxies

        self._session.auth = HTTPBasicAuth(self._username, self._password)
        transport = zeep.Transport(session=self._session)
        client = zeep.Client(wsdl=self._wsdl, transport=transport)
        self._service = client.create_service(BINDING, DOMAIN_URL.format(domain=self._domain))

        self._service.listPhone(searchCriteria={'name': '%'}, returnedTags={'name': ''})

    def _get_devices(self, fetch_inactive_devices=False):
        try:
            response = self._service.listPhone(searchCriteria={'name': '%'}, returnedTags={'name': ''})

            response = zeep.helpers.serialize_object(response, dict)
            if not (response and
                    isinstance(response.get('return'), dict) and
                    isinstance(response.get('return').get('phone'), list)):
                logger.error(f'Response is not in the correct format: {response}')
                return
            phones = response.get('return').get('phone')

            number_of_phones = 0
            for phone in phones:
                if not isinstance(phone, dict):
                    logger.error(f'phone is not in the correct format: {phone}')
                    continue
                phone.pop('authenticationString', None)
                if not fetch_inactive_devices and not parse_bool_from_raw(phone.get('isActive')) is True:
                    continue
                yield phone
                number_of_phones += 1

                if number_of_phones >= MAX_NUMBER_OF_DEVICES:
                    logger.info(
                        f'Exceeding max number of devices: {number_of_phones}, left: {len(phones) - number_of_phones}')
                    break
            logger.info(f'Fetched {number_of_phones} devices.')
        except Exception as e:
            logger.exception(f'Error while fetching devices: {str(e)}')
            raise

    # pylint: disable=arguments-differ
    def get_device_list(self, fetch_inactive_devices=False):
        try:
            yield from self._get_devices(fetch_inactive_devices)
        except RESTException as err:
            logger.exception(str(err))
            raise
