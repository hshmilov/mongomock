import logging
import datetime
from collections import OrderedDict
import xmltodict
from funcy import chunks as split_to_chunks  # pylint: disable=import-error
from dicttoxml import dicttoxml

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from axonius.utils.parsing import int_or_none
from axonius.clients.cisco_security_manager.consts import MAX_NUMBER_OF_DEVICES, \
    URL_BASE_PREFIX, URL_API_LOGIN_SUFFIX, URL_API_REFRESH_TOKEN_SUFFIX, SESSION_REFRESH_TIME_SEC, \
    URL_API_DEVICE_LIST, URL_API_DEVICE_BY_GUID, URL_API_REFRESH_TOKEN_ROOT, VALID_RESPONSE, \
    URL_API_LOGIN_REQUEST_ROOT, URL_API_DEVICE_LIST_ROOT, URL_API_DEVICE_GUID_ROOT

logger = logging.getLogger(f'axonius.{__name__}')


# pylint: disable=logging-format-interpolation


class CiscoSecurityManagerConnection(RESTConnection):
    """ rest client for CiscoSecurityManager adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix=URL_BASE_PREFIX,
                         headers={'Content-Type': 'application/xml',
                                  'Accept': 'application/xml'},
                         **kwargs)
        self._session_refresh = None

    def _refresh_token(self):
        try:
            if self._session_refresh and self._session_refresh > datetime.datetime.now():
                return

            body_params = OrderedDict({
                'protVersion': '1.0',
                'reqId': '123'
            })
            body_params_xml = dicttoxml(body_params, custom_root=URL_API_REFRESH_TOKEN_ROOT,
                                        attr_type=False).decode('utf-8')
            response = self._put(URL_API_REFRESH_TOKEN_SUFFIX, body_params=body_params_xml, use_json_in_body=False,
                                 use_json_in_response=False, return_response_raw=True)
            if response.status_code not in VALID_RESPONSE:
                raise RESTException(f'Failed refreshing token, received invalid response: {str(response.content)}')

        except Exception as e:
            raise RESTException(f'Error: Unable to refresh session. {str(e)}')

    def _get_token(self):
        try:
            body_params = OrderedDict({
                'protVersion': '1.0',
                'reqId': '123',
                'username': self._username,
                'password': self._password
            })
            body_params_xml = dicttoxml(body_params, custom_root=URL_API_LOGIN_REQUEST_ROOT, attr_type=False).decode(
                'utf-8')
            response = self._post(URL_API_LOGIN_SUFFIX, body_params=body_params_xml, use_json_in_body=False,
                                  use_json_in_response=False, return_response_raw=True)
            if not (response.status_code in VALID_RESPONSE and response.headers.get('Set-Cookie')):
                raise RESTException(f'Failed getting token, received invalid response: {str(response.content)}')

            response = xmltodict.parse(response)

            session_refresh = SESSION_REFRESH_TIME_SEC
            if isinstance(response, dict) and isinstance(response.get('loginResponse'), dict) and int_or_none(
                    response.get('loginResponse').get('sessionTimeoutInMins')):
                session_timeout_min = int_or_none(response.get('loginResponse').get('sessionTimeoutInMins'))
                session_refresh = session_timeout_min * 60  # Convert from minutes to seconds
            self._session_refresh = datetime.datetime.now() + datetime.timedelta(seconds=session_refresh - 50)

            self._session_headers['Cookie'] = response.headers.get('Set-Cookie')
        except Exception as e:
            raise RESTException(f'Error: Failed to fetch cookie token. {str(e)}')

    def _connect(self):
        if not (self._username and self._password):
            raise RESTException('No username or password')

        try:
            self._get_token()

            body_params = OrderedDict({
                'protVersion': '1.0',
                'reqId': '123',
                'deviceCapability': '*'  # Return all devices (firewall, ids, router, switch)
            })
            body_params_xml = dicttoxml(body_params, custom_root=URL_API_DEVICE_LIST_ROOT,
                                        attr_type=False).decode('utf-8')
            response = self._post(URL_API_DEVICE_LIST, body_params=body_params_xml, use_json_in_body=False,
                                  use_json_in_response=False, return_response_raw=True)
            if response.status_code in VALID_RESPONSE:
                raise RESTException(f'Connecting failed {str(response.content)}')

        except Exception as e:
            raise ValueError(f'Error: Invalid response from server, please check domain or credentials. {str(e)}')

    def _get_devices_by_gid(self):
        try:
            devices_by_id = {}
            total_fetched_devices = 0

            # DeviceListByCapabilityRequest
            body_params = OrderedDict({
                'protVersion': '1.0',
                'reqId': '123',
                'deviceCapability': '*'  # Return all devices (firewall, ids, router, switch)
            })
            body_params_xml = dicttoxml(body_params, custom_root=URL_API_DEVICE_LIST_ROOT,
                                        attr_type=False).decode('utf-8')
            self._refresh_token()
            response = self._post(URL_API_DEVICE_LIST, body_params=body_params_xml, use_json_in_body=False,
                                  use_json_in_response=False, return_response_raw=True)

            response = xmltodict.parse(response)
            if not (response.status_code in VALID_RESPONSE and
                    isinstance(response, dict) and
                    isinstance(response.get('deviceListResponse'), dict) and
                    isinstance(response.get('deviceListResponse').get('deviceId'), list)):
                logger.warning(f'Received invalid response while getting devices {response}')
                return devices_by_id

            for device_raw in response.get('deviceListResponse').get('deviceId'):
                if isinstance(device_raw, dict) and device_raw.get('gid'):
                    devices_by_id[device_raw.get('gid')] = device_raw
                    total_fetched_devices += 1

                if total_fetched_devices >= MAX_NUMBER_OF_DEVICES:
                    logger.warning(f'Exceeded max number of devices {MAX_NUMBER_OF_DEVICES}')
                    break

            logger.info(f'Got total of {total_fetched_devices} devices')
            return devices_by_id
        except Exception:
            logger.exception(f'Invalid request made while fetching devices by id')
            return devices_by_id

    def _async_get_devices(self, async_chunks: int):
        try:
            total_fetched_devices = 0

            devices_by_gid = self._get_devices_by_gid()

            device_raw_requests = []
            for device_gid in devices_by_gid:
                body_params = OrderedDict({
                    'protVersion': '1.0',
                    'reqId': '123',
                    'gid': device_gid
                })
                body_params_xml = dicttoxml(body_params, custom_root=URL_API_DEVICE_GUID_ROOT,
                                            attr_type=False).decode('utf-8')
                device_raw_requests.append({
                    'name': URL_API_DEVICE_BY_GUID,
                    'body_params': body_params_xml,
                    'use_json_in_body': False,
                    'use_json_in_response': False,
                    'return_response_raw': True,
                })

            for response in self._async_post(device_raw_requests, retry_on_error=True, chunks=async_chunks):
                if not self._is_async_response_good(response):
                    logger.error(f'Async response returned bad, its {response}')
                    continue

                response = xmltodict.parse(response)
                if not (isinstance(response, dict) and
                        isinstance(response.get('deviceConfigResponse'), dict) and
                        isinstance(response.get('deviceConfigResponse').get('device'), dict)):
                    logger.warning(f'Invalid response returned: {response}')
                    continue

                device_raw = response.get('deviceConfigResponse').get('device')
                if devices_by_gid.get(device_raw.get('gid')):
                    device_raw.update(devices_by_gid.get(device_raw.get('gid')))

                yield device_raw
                total_fetched_devices += 1

            logger.info(f'Got total of {total_fetched_devices} devices')
        except Exception:
            logger.exception(f'Invalid request made while fetching devices')
            raise

    # pylint: disable=arguments-differ
    def _async_post(self, list_of_requests, chunks: int, *args, **kwargs):
        """ Override _async_post in order to refresh token for requests if token expired """
        for higher_level_chunk in split_to_chunks(chunks, list_of_requests):
            self._refresh_token()
            yield from super()._async_post(higher_level_chunk, *args, **kwargs)

    # pylint: disable=arguments-differ
    def get_device_list(self, async_chunks: int):
        try:
            yield from self._async_get_devices(async_chunks=async_chunks)
        except RESTException as err:
            logger.exception(str(err))
            raise
