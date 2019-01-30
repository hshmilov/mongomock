import time
import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from crowd_strike_adapter import consts

logger = logging.getLogger(f'axonius.{__name__}')

# XXX: For some reason this file doesn't ignore logging-fstring-interpolation
# although we got it in pylintrc ignore. add disable for it, and disable the disable warning
# pylint: disable=I0021
# pylint: disable=W1203


class CrowdStrikeConnection(RESTConnection):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _connect(self):
        if self._username is not None and self._password is not None:
            self._get('devices/queries/devices/v1',
                      do_basic_auth=True,
                      url_params={'limit': consts.DEVICES_PER_PAGE, 'offset': 0})
        else:
            raise RESTException('No user name or API key')

    def get_device_list(self):
        # pylint: disable=R0912
        ids_list = []
        offset = 0
        response = self._get('devices/queries/devices/v1',
                             url_params={'limit': consts.DEVICES_PER_PAGE, 'offset': offset},
                             do_basic_auth=True)
        try:
            ids_list.extend(response['resources'])
        except Exception:
            logger.exception(f'Problem getting resource')
            raise RESTException('Cant get resources')
        try:
            total_count = response['meta']['pagination']['total']
        except Exception:
            logger.exception(f'Cant get total count')
            raise RESTException('Cant get total count')
        offset += consts.DEVICES_PER_PAGE
        while offset < total_count and offset < consts.MAX_NUMBER_OF_DEVICES:
            try:
                ids_list.extend(self._get('devices/queries/devices/v1',
                                          url_params={'limit': consts.DEVICES_PER_PAGE,
                                                      'offset': offset},
                                          do_basic_auth=True)['resources'])
            except Exception:
                logger.exception(f'Problem getting offset {offset}')
            offset += consts.DEVICES_PER_PAGE

        # Now use asyncio to get all of these requests
        async_requests = []
        for device_id in ids_list:
            try:
                if device_id is None or device_id == '':
                    logger.warning(f'Bad device {device_id}')
                    continue
                async_requests.append({'name': f'devices/entities/devices/v1?ids={device_id}',
                                       'do_basic_auth': True})
            except Exception:
                logger.exception(f'Got problem with id {device_id}')
        if len(async_requests) < 480:
            for response in self._async_get_only_good_response(async_requests):
                try:
                    yield response['resources'][0]
                except Exception:
                    logger.exception(f'Problem getting async response {str(response)}')
        async_requests_first = async_requests[:480]
        async_requests = async_requests[480:]
        for response in self._async_get_only_good_response(async_requests_first, chunks=1):
            try:
                yield response['resources'][0]
            except Exception:
                logger.exception(f'Problem getting async response {str(response)}')
        time.sleep(5)
        while async_requests:
            async_requests_first = async_requests[:500]
            for response in self._async_get_only_good_response(async_requests_first, chunks=1):
                try:
                    yield response['resources'][0]
                except Exception:
                    logger.exception(f'Problem getting async response {str(response)}')
            time.sleep(5)
            async_requests = async_requests[500:]
