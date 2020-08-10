import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from ibm_qradar_adapter.consts import API_PREFIX, API_LOG_SOURCE_SUFFIX, API_LOG_SOURCE_TYPE_SUFFIX, \
    API_LOG_SOURCE_GROUP_SUFFIX, DEVICE_PER_PAGE, MAX_NUMBER_OF_DEVICES, LOG_SOURCE_TYPE, LOG_SOURCE_GROUP

logger = logging.getLogger(f'axonius.{__name__}')

# pylint: disable=logging-format-interpolation


class IbmQradarConnection(RESTConnection):
    """ rest client for IbmQradar adapter """

    def __init__(self, *args, token: str, **kwargs):
        super().__init__(*args, url_base_prefix=API_PREFIX,
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._token = token

    def _connect(self):
        if not self._token:
            raise RESTException('No token')

        try:
            self._session_headers['SEC'] = self._token

            extra_headers = {
                'Range': 'items=0-1'
            }
            self._get(API_LOG_SOURCE_SUFFIX, extra_headers=extra_headers)

        except Exception as e:
            raise ValueError(f'Error: Invalid response from server, please check domain or credentials. {str(e)}')

    def _get_log_source_extra_info(self, obj_type: str, suffix: str):
        log_sources_extra_info = {}
        total_obj = 0
        try:
            # Both groups and types, return dict
            # add info

            for i in range(0, int(MAX_NUMBER_OF_DEVICES / DEVICE_PER_PAGE)):
                extra_headers = {
                    'Range': f'items={i * DEVICE_PER_PAGE}-{(i * DEVICE_PER_PAGE) + DEVICE_PER_PAGE - 1}'
                }

                response = self._get(suffix, extra_headers=extra_headers)
                if not isinstance(response, list):
                    logger.warning(f'Received invalid response while paginating log sources {obj_type}, {response}')
                    return {}

                for log_source_extra_info in response:
                    if isinstance(log_source_extra_info, dict) and log_source_extra_info.get('id'):
                        log_sources_extra_info[log_source_extra_info.get('id')] = log_source_extra_info
                        total_obj += 1

                if len(response) != DEVICE_PER_PAGE:
                    logger.info(f'fetching {obj_type} stopped due to small page response {len(response)}')
                    break

                if total_obj >= MAX_NUMBER_OF_DEVICES:
                    logger.info(f'Exceeded max number of {obj_type} : {total_obj}')
                    break

            logger.info(f'Got total {total_obj} of {obj_type}')
            return log_sources_extra_info
        except Exception as e:
            logger.exception(f'Invalid request made while paginating {obj_type}')
            return log_source_extra_info

    def _paginated_device_get(self):
        try:
            total_assets = 0
            log_source_types = self._get_log_source_extra_info(obj_type=LOG_SOURCE_TYPE,
                                                               suffix=API_LOG_SOURCE_TYPE_SUFFIX)
            log_source_groups = self._get_log_source_extra_info(obj_type=LOG_SOURCE_GROUP,
                                                                suffix=API_LOG_SOURCE_GROUP_SUFFIX)

            for i in range(0, int(MAX_NUMBER_OF_DEVICES / DEVICE_PER_PAGE)):
                extra_headers = {
                    'Range': f'items={i * DEVICE_PER_PAGE}-{(i * DEVICE_PER_PAGE) + DEVICE_PER_PAGE - 1}'
                }

                response = self._get(API_LOG_SOURCE_SUFFIX, extra_headers=extra_headers)
                if not isinstance(response, list):
                    logger.warning(f'Received invalid response while paginating log sources {response}')
                    return

                for log_source in response:
                    if isinstance(log_source, dict):
                        yield log_source, log_source_types, log_source_groups
                        total_assets += 1

                if len(response) != DEVICE_PER_PAGE:
                    logger.info(f'Fetching log sources stopped due to small page response {len(response)}')
                    break

                if total_assets >= MAX_NUMBER_OF_DEVICES:
                    logger.info(f'Exceeded max number of log sources : {total_assets}')
                    break

            logger.info(f'Got total of {total_assets} assets')
        except Exception:
            logger.exception(f'Invalid request made while paginating devices')
            raise

    def get_device_list(self):
        try:
            yield from self._paginated_device_get()
        except RESTException as err:
            logger.exception(str(err))
            raise
