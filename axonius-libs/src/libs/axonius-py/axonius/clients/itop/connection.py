import logging
import json

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from axonius.clients.itop.consts import OBJECTS_PER_PAGE, MAX_NUMBER_OF_OBJECTS, API_URL_BASE_PREFIX, API_URL_SUFFIX, \
    DEVICE_CLASS, DEVICE_OBJECT, USER_CLASS, USER_OBJECT

logger = logging.getLogger(f'axonius.{__name__}')

# pylint: disable=logging-format-interpolation


class ItopConnection(RESTConnection):
    """ rest client for iTOP adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix=API_URL_BASE_PREFIX,
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)

    def _get_version(self):
        json_data = {
            'operation': 'list_operations'
        }
        body_params = {
            'auth_user': self._username,
            'auth_pwd': self._password,
            'json_data': json.dumps(json_data),
        }
        response = self._post(API_URL_SUFFIX, body_params=body_params)
        if not (isinstance(response, dict) and response.get('version')):
            message = f'Invalid response from the server while getting version and operations {str(response)}'
            logger.exception(message)
            raise RESTException(message)

        return response.get('version')

    def _connect(self):
        if not (self._username and self._password):
            raise RESTException('No username or password')

        try:
            version = self._get_version()

            json_data = {
                'operation': 'core/get',
                'class': DEVICE_CLASS,
                'key': f'SELECT {DEVICE_CLASS}',
                'output_fields': '*',
                'limit': '1',  # Amount of results to return (0 means unlimited)
                'page': '1'  # Page number to return (cant be < 1)
            }
            body_params = {
                'auth_user': self._username,
                'auth_pwd': self._password,
                'json_data': json.dumps(json_data),
            }
            url_params = {
                'version': version
            }
            self._post(API_URL_SUFFIX, url_params=url_params, body_params=body_params)
        except Exception as e:
            raise ValueError(f'Error: Invalid response from server, please check domain or credentials. {str(e)}')

    def _paginated_device_get(self):
        json_data = {
            'operation': 'core/get',
            'class': DEVICE_CLASS,
            'key': f'SELECT {DEVICE_CLASS}',
            'output_fields': '*',
            'limit': str(OBJECTS_PER_PAGE),
            'page': '1'
        }

        yield self._paginated_object_get(object_type=DEVICE_OBJECT, json_data=json_data)

    def get_device_list(self):
        try:
            yield from self._paginated_device_get()
        except RESTException as err:
            logger.exception(str(err))
            raise

    def _paginated_user_get(self):
        json_data = {
            'operation': 'core/get',
            'class': USER_CLASS,
            'key': f'SELECT {USER_CLASS}',
            'output_fields': '*',
            'limit': str(OBJECTS_PER_PAGE),
            'page': '1'
        }

        yield self._paginated_object_get(object_type=USER_OBJECT, json_data=json_data)

    def get_user_list(self):
        try:
            yield from self._paginated_user_get()
        except RESTException as err:
            logger.exception(str(err))
            raise

    def _paginated_object_get(self, object_type: str, json_data: dict):
        try:
            total_fetched_objects = 0

            version = self._get_version()

            body_params = {
                'auth_user': self._username,
                'auth_pwd': self._password,
                'json_data': json.dumps(json_data),
            }
            url_params = {
                'version': version
            }

            while int(json_data['limit']) * int(json_data['page']) < MAX_NUMBER_OF_OBJECTS:
                response = self._post(API_URL_SUFFIX, url_params=url_params, body_params=body_params)
                if not (isinstance(response, dict) and
                        isinstance(response.get('objects'), dict) and
                        response.get('objects')):
                    logger.warning(f'Received invalid response for {object_type}: {response}')
                    return

                for obj_id, obj_raw in response.get('objects').items():
                    if not (isinstance(obj_raw, dict) and
                            isinstance(obj_raw.get('fields'), dict) and
                            obj_raw.get('fields')):
                        logger.warning(f'Received invalid response for {object_type} raw, {obj_id}:{obj_raw}')
                        continue

                    obj_fields_raw = obj_raw.get('fields')
                    obj_fields_raw['key'] = obj_raw.get('key')
                    yield obj_fields_raw
                    total_fetched_objects += 1

                if total_fetched_objects >= MAX_NUMBER_OF_OBJECTS:
                    logger.info(f'Exceeded max number ({MAX_NUMBER_OF_OBJECTS}) of {object_type}')
                    break

                if len(response.get('objects')) < OBJECTS_PER_PAGE:
                    logger.info(f'Finished paginating {object_type}, last page received '
                                f'{len(response.get("objects"))} / {OBJECTS_PER_PAGE}')
                    break

                json_data['page'] = str(int(json_data['page']) + 1)
                body_params['json_data'] = json.dumps(json_data)

            logger.info(f'Got total of {total_fetched_objects} {object_type}')
        except Exception as err:
            logger.exception(f'Invalid request made while paginating {object_type} {str(err)}')
            raise
