import logging
from collections import defaultdict
# pylint: disable=import-error

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from vectra_adapter.consts import URL_API_PREFIX, DEVICE_PER_PAGE, MAX_NUMBER_OF_DEVICES

logger = logging.getLogger(f'axonius.{__name__}')


# pylint: disable=logging-format-interpolation


class VectraConnection(RESTConnection):
    def __init__(self, *args, token, **kwargs):
        super().__init__(*args, url_base_prefix=URL_API_PREFIX,
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._token = token
        self._session_headers = {
            'Authorization': 'Token ' + self._token
        }

    def _connect(self):
        if not self._token:
            raise RESTException('No token')

        try:
            url_params = {
                'page': 1,
                'page_size': 1
            }
            self._get('hosts', url_params=url_params)
        except RESTException as e:
            raise RESTException(f'Error: Invalid response from server, please check domain or credentials. {str(e)}')

    def _get_detections_by_id(self):
        detections_by_id = defaultdict(list)
        try:
            url_params = {
                'page': 1,
                'page_size': DEVICE_PER_PAGE
            }
            total_detections = 0
            while (url_params['page'] * url_params['page_size']) < MAX_NUMBER_OF_DEVICES:
                response = self._get('detections', url_params=url_params)
                if not (isinstance(response, dict) and isinstance(response.get('results'), list)):
                    logger.warning(f'Received invalid response for detections: {response}')
                    break

                for detection in response.get('results'):
                    if isinstance(detection, dict):
                        if detection.get('id'):
                            total_detections += 1
                            detections_by_id[str(detection.get('id'))].append(detection)

                if len(response.get('results')) < DEVICE_PER_PAGE:
                    logger.info(f'Done detections pagination, got {total_detections} detections')
                    break

                url_params['page'] += 1
        except Exception:
            logger.exception('Invalid request made, failed get detections by id')

        return detections_by_id

    #pylint: disable=too-many-nested-blocks
    def _paginated_get(self):
        try:
            detections_by_id = self._get_detections_by_id()

            url_params = {
                'page': 1,
                'page_size': DEVICE_PER_PAGE
            }
            total_devices = 0
            while (url_params['page'] * url_params['page_size']) < MAX_NUMBER_OF_DEVICES:
                response = self._get('hosts', url_params=url_params)
                if not (isinstance(response, dict) and isinstance(response.get('results'), list)):
                    logger.warning(f'Received invalid response for hosts: {response}')
                    break

                for device in response.get('results'):
                    device['detections_by_id'] = []
                    if isinstance(device.get('detection_ids'), list):
                        for detection_id in device.get('detection_ids'):
                            if detections_by_id.get(str(detection_id)):
                                device['detections_by_id'].append(detections_by_id[str(detection_id)])
                    yield device
                    total_devices += 1

                if len(response.get('results')) < DEVICE_PER_PAGE:
                    logger.info(f'Done hosts pagination, got {total_devices} devices')
                    break

                url_params['page'] += 1
        except Exception:
            logger.exception(f'Invalid request made, failed getting hosts')

    def get_device_list(self):
        try:
            yield from self._paginated_get()
        except RESTException as err:
            logger.exception(err)
            raise
