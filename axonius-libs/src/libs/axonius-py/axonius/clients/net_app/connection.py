import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from axonius.clients.net_app.consts import USER_PER_PAGE, DEVICE_PER_PAGE, MAX_NUMBER_OF_DEVICES, MAX_NUMBER_OF_USERS, \
    URL_CLUSTER_NODES, URL_SECURITY_ACCOUNTS, API_PREFIX, DEFAULT_MAX_VALUE, DEFAULT_PAGINATED_VALUE, \
    PAGINATION_URL_PREFIX

logger = logging.getLogger(f'axonius.{__name__}')


# pylint: disable=logging-format-interpolation


class NetAppConnection(RESTConnection):
    """ rest client for NetApp adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix=API_PREFIX,
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)

    @staticmethod
    def _get_next_page_url(_links: dict) -> str:
        """ Returns the url for the next page of results if it exists and is different from the current page's url """
        next_url = ''
        current_url = ''
        if isinstance(_links, dict):
            next_dict = _links.get('next') if isinstance(_links.get('next'), dict) else None
            current_dict = _links.get('self') if isinstance(_links.get('self'), dict) else None
            if next_dict:
                if isinstance(next_dict.get('href'), str):
                    next_url = next_dict.get('href')
            if current_dict:
                if isinstance(current_dict.get('href'), str):
                    current_url = current_dict.get('href')
            if next_url and current_url and next_url != current_url:
                if next_url.startswith(PAGINATION_URL_PREFIX):
                    return next_url[len(PAGINATION_URL_PREFIX):]
        return None

    def _connect(self):
        if not self._username:
            raise RESTException('No username')
        if not self._password:
            raise RESTException('No password')

        try:
            url_params = {
                'max_records': 1
            }

            device_response = self._get(URL_CLUSTER_NODES, url_params=url_params, do_basic_auth=True)
            if not (isinstance(device_response, dict) and not device_response.get('error')):
                raise RESTException(f'Invalid response from {URL_CLUSTER_NODES}: {device_response}')

            user_response = self._get(URL_SECURITY_ACCOUNTS, url_params=url_params, do_basic_auth=True)
            if not (isinstance(user_response, dict) and not user_response.get('error')):
                raise RESTException(f'Invalid response from {URL_SECURITY_ACCOUNTS}: {user_response}')
        except Exception as e:
            raise ValueError(f'Error: Invalid response from server, please check domain or credentials. {str(e)}')

    def _paginated_get(self, url: str, object_per_page: int = DEFAULT_PAGINATED_VALUE,
                       max_object: int = DEFAULT_MAX_VALUE):
        try:
            obj_type = 'unknown'
            if url == URL_CLUSTER_NODES:
                obj_type = 'devices'
            elif url == URL_SECURITY_ACCOUNTS:
                obj_type = 'users'
            url_params = {
                'max_records': object_per_page
            }
            object_counter = 0
            while object_counter < max_object:
                response = self._get(url, url_params=url_params, do_basic_auth=True)
                if not isinstance(response, dict):
                    logger.warning(f'Response not a dictionary for {url}: {response}')
                    continue
                if response.get('error'):
                    logger.error(f'Invalid NetApp response from {url}: {response}')
                    raise RESTException(f'Invalid NetApp response from {url}: {response}')
                if response.get('records') and isinstance(response.get('records'), list):
                    for obj in response.get('records'):
                        if isinstance(obj, dict):
                            yield obj
                            object_counter += 1
                    url = self._get_next_page_url(response.get('_links'))
                    if not url:
                        break

            logger.info(f'Fetched total of {object_counter} {obj_type}')
        except Exception as e:
            logger.exception(f'Invalid request paginating for {url}: {e}')
            raise

    def get_device_list(self):
        try:
            yield from self._paginated_get(URL_CLUSTER_NODES, DEVICE_PER_PAGE, MAX_NUMBER_OF_DEVICES)
        except Exception as e:
            logger.exception(f'Invalid request made while paginating devices {e}')
            raise

    def get_user_list(self):
        try:
            yield from self._paginated_get(URL_SECURITY_ACCOUNTS, USER_PER_PAGE, MAX_NUMBER_OF_USERS)
        except Exception as e:
            logger.exception(f'Invalid request made while paginating users {e}')
            raise
