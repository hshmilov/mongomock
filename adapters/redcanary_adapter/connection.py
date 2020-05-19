import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from redcanary_adapter.consts import DEVICE_PER_PAGE, MAX_NUMBER_OF_DEVICES

logger = logging.getLogger(f'axonius.{__name__}')


class RedcanaryConnection(RESTConnection):
    """ rest client for Redcanary adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='openapi/v3',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._permanent_headers['X-Api-Key'] = self._apikey

    def _connect(self):
        if not self._apikey:
            raise RESTException('No API KEY')
        page = 1
        self._get('endpoints',
                  url_params={'per_page': DEVICE_PER_PAGE,
                              'page': page})

    def get_device_list(self):
        detections_dict = dict()
        try:
            for detection_raw in self._get_api_endpoint('detections'):
                try:
                    relationships = detection_raw.get('relationships') or {}
                    affected_endpoint = relationships.get('affected_endpoint') or {}
                    endpoint_data = affected_endpoint.get('data') or {}
                    endpoint_id = endpoint_data.get('id')
                    if not endpoint_id:
                        continue
                    endpoint_id = str(endpoint_id)
                    if endpoint_id not in detections_dict:
                        detections_dict[endpoint_id] = []
                    detections_dict[endpoint_id].append(detection_raw)
                except Exception:
                    logger.exception(f'Prbolem with detecion {detection_raw}')
        except Exception:
            logger.exception(f'Problem with detcionns')
        for device_raw in self._get_api_endpoint('endpoints'):
            yield device_raw, detections_dict

    def _get_api_endpoint(self, endpoint):
        page = 1
        response = self._get(endpoint,
                             url_params={'per_page': DEVICE_PER_PAGE,
                                         'page': page}
                             )
        yield from response['data']
        while page * DEVICE_PER_PAGE < MAX_NUMBER_OF_DEVICES:
            try:
                page += 1
                response = self._get(endpoint,
                                     url_params={'per_page': DEVICE_PER_PAGE,
                                                 'page': page}
                                     )
                if not response['data']:
                    break
                yield from response['data']
            except Exception:
                logger.exception(f'Problem getting page {page}')
                break
