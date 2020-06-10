import logging
from typing import Optional

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from firemon_adapter import consts

logger = logging.getLogger(f'axonius.{__name__}')


class FiremonConnection(RESTConnection):
    """ rest client for Firemon adapter """

    def __init__(self,
                 *args,
                 enrich_ios_version: bool = False,
                 **kwargs):
        super().__init__(*args,
                         url_base_prefix=consts.FIREMON_API_PREFIX,
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)

        self.__enrich_ios_version = enrich_ios_version

    def _connect(self):
        try:
            self._refresh_token()
        except Exception as e:
            raise RESTException(f'Failed authenticating with Firemon. {str(e)}')

        # Device Permissions check
        try:
            _ = next(self._iter_devices_for_domain(consts.DEFAULT_DOMAIN_ID, limit=1))
        except Exception as e:
            raise RESTException(f'Failed querying devices. {str(e)}')

        # Controls Permissions check
        if self.__enrich_ios_version:
            control_dict = self._create_control_if_needed(consts.DEFAULT_DOMAIN_ID,
                                                          consts.CONTROL_NAME_ENRICH_IOS,
                                                          consts.CONTROL_DETAILS_ENRICH_IOS)
            if not control_dict:
                raise RESTException(f'Failed creating control {consts.CONTROL_NAME_ENRICH_IOS}.'
                                    f' Please check you have sufficient permissions.')

    def _paginated_get(self, *args, limit: int = consts.MAX_NUMBER_OF_DEVICES, **kwargs):
        url_params = kwargs.setdefault('url_params', {})
        url_params.setdefault('page', 0)
        url_params.setdefault('pageSize', min(consts.DEVICE_PER_PAGE, limit))

        count_so_far = 0
        total_count = None
        has_more = True
        while has_more:
            try:
                response = self._get(*args, **kwargs)
                if not isinstance(response, dict):
                    logger.warning(f'Got invalid response: {response}')
                    break

                results = response.get('results')
                if not isinstance(results, list):
                    logger.warning(f'Got invalid results in response: {response}')
                    break

                curr_count = len(results)
                if curr_count == 0:
                    logger.warning('Got 0 results')
                    break

                count_so_far += curr_count
                if total_count is None:
                    total_count = response.get('total')

                logger.debug(f'Yielding {curr_count} devices ({count_so_far} incl. / {total_count})')
                yield from results

                url_params['page'] += 1

                if total_count is not None:
                    has_more = (count_so_far < min(total_count, limit))
                else:
                    has_more = False
            except Exception:
                logger.exception(f'Unexpected error occurred in paginated_get for params {url_params}')
                break
        logger.info(f'Done pagination after {count_so_far} / {total_count} results ')

    def _refresh_token(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')

        # Response Example:
        # { "authorized": true, "authCode": 0, "token": "Access_token", "tokenTTL": 599940 }
        response = self._post('authentication/login', body_params={
            'username': self._username,
            'password': self._password,
        })

        if not isinstance(response, dict):
            raise RESTException(f'Invalid response received: {response}')

        is_authorized = response.get('authorized')
        if not isinstance(is_authorized, bool):
            raise RESTException(f'Invalid authorization status received: {response}')
        if not is_authorized:
            raise RESTException(f'The provided credentials are not authorized by Firemon.')

        token = response.get('token')
        if not isinstance(token, str):
            raise RESTException(f'Invalid token received: {response}')

        self._session_headers['X-FM-AUTH-Token'] = token

    def _get_control(self, domain_id: str, control_name: str) -> Optional[dict]:
        try:
            response = self._get(f'domain/{domain_id}/control/name/{control_name}')
            if not isinstance(response, dict):
                logger.error(f'Got unexpected result for control {control_name}: {response}')
                return None
            return response
        except Exception:
            logger.warning(f'Unable to get control {control_name}', exc_info=True)
            return None

    def _create_control(self, domain_id, details: dict):
        control_name = details.get('name')
        try:
            response = self._post(f'domain/{domain_id}/control', body_params=details)
            if not isinstance(response, dict):
                logger.warning(f'Invalid response returned when creating control {control_name}: {response}')
                return None
            return response
        except Exception as e:
            logger.exception(f'Failed creating control {control_name}: {str(e)}')
            return None

    def _create_control_if_needed(self, domain_id, control_name, control_details):
        # retrieve control
        control_dict = self._get_control(domain_id, control_name)

        # if non-existent, create it
        if not control_dict:
            logger.info(f'unable to locate control {consts.CONTROL_NAME_ENRICH_IOS}, creating it.')
            control_dict = self._create_control(domain_id, control_details)
            if isinstance(control_dict, dict):
                logger.info(f'Created control {control_name} succesfully: {control_dict}')

        # if still non-existent, fail
        if not control_dict:
            logger.warning(f'Failed locating and creating control {control_name}')
            return None

        return control_dict

    def _execute_control_on_device(self, domain_id, control_id: str, device_dict: dict):

        if not (isinstance(device_dict, dict) and device_dict.get('id')):
            logger.warning(f'Invalid device given to run control {control_id} on: {device_dict}')
            return None

        device_id = device_dict.get('id')
        url_params = {
            **consts.ASSESSMENT_RESULT_PARAMS
        }
        try:
            response = self._get(f'domain/{domain_id}/control/{control_id}/execute/device/{device_id}',
                                 url_params=url_params)
            if not isinstance(response, dict):
                logger.warning(f'Invalid response receivied for device {device_id}'
                               f' while executing control {control_id}: {response}')
                return None
            return response
        except Exception as e:
            logger.exception(f'Failed executing control {control_id} on device {device_id}. {str(e)}')
            return None

    def _enrich_device_with_control(self, domain_id, device_dict, control_name: str, control_details: dict):

        control_dict = self._create_control_if_needed(domain_id, control_name, control_details)
        if not isinstance(control_dict, dict):
            return

        control_id = control_dict.get('id')
        if not isinstance(control_id, str):
            logger.warning(f'Returned control has no id: {control_dict}')
            return

        control_output = self._execute_control_on_device(domain_id, control_id, device_dict)
        if not isinstance(control_output, dict):
            logger.warning(f'Invalid output returned for control execution: {control_output}')
            return

        # results are injected into device_dict inner objects
        device_dict[control_name] = control_output

    def _enrich_device_with_all_controls(self, domain_id, device_dict: dict):
        if self.__enrich_ios_version:
            try:
                # Make sure device is eligable
                if not (isinstance(device_dict, dict) and isinstance(device_dict.get('devicePack'), dict) and
                        (device_dict.get('devicePack').get('deviceType') == consts.CONTROL_ENRICH_IOS_DEVICE_TYPE) and
                        (device_dict.get('devicePack').get('vendor') == consts.CONTROL_ENRICH_IOS_DEVICE_VENDOR) and
                        (device_dict.get('devicePack').get('deviceName') == consts.CONTROL_ENRICH_IOS_DEVICE_NAME)):
                    # Ineligable device - skip enrichment silently
                    return

                self._enrich_device_with_control(domain_id, device_dict,
                                                 consts.CONTROL_NAME_ENRICH_IOS,
                                                 consts.CONTROL_DETAILS_ENRICH_IOS)
            except Exception:
                logger.warning(f'Failed iOS enrichment for device {device_dict}', exc_info=True)

    def _iter_devices_for_domain(self, domain_id, limit=consts.MAX_NUMBER_OF_DEVICES):
        yield from self._paginated_get(f'domain/{domain_id}/device', limit=limit)

    def get_device_list(self):
        for device_dict in self._iter_devices_for_domain(consts.DEFAULT_DOMAIN_ID):
            self._enrich_device_with_all_controls(consts.DEFAULT_DOMAIN_ID, device_dict)
            if device_dict:
                yield device_dict
