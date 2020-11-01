import logging
import json

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from axonius.clients.itop.consts import OBJECTS_PER_PAGE, MAX_NUMBER_OF_OBJECTS, API_URL_BASE_PREFIX, API_URL_SUFFIX, \
    DEVICE_CLASS, DEVICE_OBJECT, USER_CLASS, USER_OBJECT, OPERATION_CHECK_CREDENTIALS, OPERATION_GET, \
    DEFAULT_API_VERSION

logger = logging.getLogger(f'axonius.{__name__}')

# pylint: disable=logging-format-interpolation


class ItopConnection(RESTConnection):
    """ rest client for iTOP adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix=f'{API_URL_BASE_PREFIX}',
                         headers={'Content-Type': 'application/x-www-form-urlencoded',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._api_version = DEFAULT_API_VERSION

    def _check_credentials(self):
        try:
            json_data = {
                'operation': OPERATION_CHECK_CREDENTIALS,
                'user': self._username,
                'password': self._password
            }

            body_params = {
                'version': self._api_version,
                'auth_user': self._username,
                'auth_pwd': self._password,
                'json_data': json.dumps(json_data),
            }

            response = self._post(API_URL_SUFFIX, body_params=body_params,  use_json_in_body=False)
            # authorized is a bool / does not exists.
            # if its bool and True credentials are ok
            # if its bool and False or does not exists -> Error will be raised (credentials are not ok)
            if not (isinstance(response, dict) and response.get('authorized')):
                message = f'Invalid response from the server while checking credentials {str(response)}'
                logger.exception(message)
                raise RESTException(message)

        except Exception as e:
            message = f'Error: Failed authorized credentials {str(e)}'
            logger.exception(message)
            raise RESTException(message)

    def _connect(self):
        if not (self._username and self._password):
            raise RESTException('No username or password')

        try:
            self._check_credentials()
        except Exception as e:
            raise ValueError(f'Error: Invalid response from server, please check domain or credentials. {str(e)}')

    def _paginated_device_get(self, exclude_obsolete: bool):
        json_data = {
            'operation': OPERATION_GET,
            'class': DEVICE_CLASS,
            'key': f'SELECT {DEVICE_CLASS}',
            'output_fields': '*',
            'limit': str(OBJECTS_PER_PAGE),
            'page': '1'
        }

        yield from self._paginated_object_get(object_type=DEVICE_OBJECT, json_data=json_data,
                                              exclude_obsolete=exclude_obsolete)

    # pylint: disable=arguments-differ
    def get_device_list(self, exclude_obsolete: bool=False):
        try:
            yield from self._paginated_device_get(exclude_obsolete=exclude_obsolete)
        except RESTException as err:
            logger.exception(str(err))
            raise

    def _paginated_user_get(self, exclude_obsolete: bool):
        json_data = {
            'operation': OPERATION_GET,
            'class': USER_CLASS,
            'key': f'SELECT {USER_CLASS}',
            'output_fields': '*',
            'limit': str(OBJECTS_PER_PAGE),
            'page': '1'
        }

        yield from self._paginated_object_get(object_type=USER_OBJECT, json_data=json_data,
                                              exclude_obsolete=exclude_obsolete)

    def get_user_list(self, exclude_obsolete: bool=False):
        try:
            yield from self._paginated_user_get(exclude_obsolete)
        except RESTException as err:
            logger.exception(str(err))
            raise

    def _paginated_object_get(self, object_type: str, json_data: dict, exclude_obsolete: bool=False):
        try:
            logger.info(f'Start querying for {object_type}')

            total_fetched_objects = 0

            body_params = {
                'version': self._api_version,
                'auth_user': self._username,
                'auth_pwd': self._password,
                'json_data': json.dumps(json_data),
            }

            while int(json_data['limit']) * int(json_data['page']) < MAX_NUMBER_OF_OBJECTS:
                response = self._post(API_URL_SUFFIX, body_params=body_params, use_json_in_body=False)
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

                    # Excluding objects with status "obsolete"
                    if exclude_obsolete and isinstance(obj_fields_raw.get('status'), str) and \
                            obj_fields_raw.get('status').lower() == 'obsolete':
                        continue

                    obj_fields_raw['key'] = obj_raw.get('key')
                    yield obj_fields_raw
                    total_fetched_objects += 1

                logger.debug(f'Currently fetched {total_fetched_objects} from type {object_type}')

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
