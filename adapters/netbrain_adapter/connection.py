import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from netbrain_adapter.consts import DEVICE_PER_PAGE, MAX_NUMBER_OF_DEVICES, URL_LOGIN, URL_SETDOMAIN, URL_LOGOUT, \
    URL_DEVICES, URL_ATTRIBUTES, API_VERSION

logger = logging.getLogger(f'axonius.{__name__}')


class NetbrainConnection(RESTConnection):
    """ rest client for Netbrain adapter """

    def __init__(self,
                 *args,
                 auth_id: str = None,
                 tenant_id: str = None,
                 domain_id: str = None,
                 backwards_compatible: bool = True,
                 **kwargs):
        super().__init__(*args, url_base_prefix='ServicesAPI/API/V1/',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._auth_id = auth_id
        self._tenant_id = tenant_id
        self._domain_id = domain_id
        self._use_backcompat_api = backwards_compatible
        self._token = None

    def _login(self):
        url = URL_LOGIN
        body_params = {'username': self._username, 'password': self._password}
        if self._auth_id:
            body_params['authentication_id'] = self._auth_id
        try:
            response = self._post(url, body_params=body_params)
        except Exception as e:
            message = f'Get token failed! Details: {str(e)}'
            logger.error(message)
            raise RESTException(message)
        if not isinstance(response, dict):
            raise RESTException(f'Bad response to login: {str(response)}')
        token = response.get('token')
        if not token:
            raise RESTException(f'Could not get token for username {self._username}! Auth failed?, got {response}')
        self._token = token
        self._session_headers['Token'] = self._token

    def _set_domain_id(self):
        url = URL_SETDOMAIN
        body_params = {
            'tenantId': self._tenant_id,
            'domainId': self._domain_id,
        }
        try:
            self._put(url, body_params=body_params)
        except RESTException as e:
            message = f'Failed to set working domain! Details: {str(e)}'
            logger.error(message)
            raise RESTException(message)

    def _prepare_connection(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')
        if not self._tenant_id or not self._domain_id:
            raise RESTException('No tenant_id or domain_id')
        if self._token:
            logger.warning('Token already exists. Trying to recycle.')
            try:
                self._logout()
            except Exception as e:
                logger.exception(f'Login: Got an exception trying to recycle token: {str(e)}')
            finally:
                self._token = None

    def _connect(self):
        self._prepare_connection()
        self._login()
        self._set_domain_id()  # This also verifies permissions to get devices

    def _logout(self):
        if not self._token:
            logger.debug('Tried to logout of a session that is not logged in!')
            return
        url = URL_LOGOUT
        try:
            self._delete(url)
        except Exception as e:
            message = f'Delete token failed! - {str(e)}'
            logger.warning(message, exc_info=RESTException(message))
        else:
            logger.info(f'Successfully logged out from {self._domain} with {self._username}')
        finally:
            self._token = None
            self._session_headers.clear()

    def close(self):
        self._logout()
        super().close()

    def _get_switch_port(self, device_ip):
        url_topology = f'CMDB/Topology/Devices/{device_ip}/ConnectedSwitchPort'
        try:
            response = self._get(url_topology)
            if response.get('hostname') and response.get('interface'):
                return {
                    'hostname': response['hostname'],
                    'interface': response['interface']
                }
        except Exception as e:
            logger.warning(f'Failed to get connected switch port information for {device_ip}: got {str(e)}')
        return None

    def _paginated_get_devices(self):
        """
        Get devices paginated for API versions 8.01+
        Handles api documentation mismatches.
        Raise any exception, to be handled by get_device_list.
        While API docs specify a possible "total result count",
        they are extremely unreliable so we ignore them (as of SEP 30 2020)
        :return: yield a list of devices
        """
        count_so_far = 0
        this_page = DEVICE_PER_PAGE
        url_params = {
            'version': API_VERSION,  # set this for new API
            'fullattr': 1,  # Requires version 1
            'skip': count_so_far,
            'limit': this_page,  # max 100 min 10
        }
        # a partial page means end of output
        while this_page == DEVICE_PER_PAGE and count_so_far < MAX_NUMBER_OF_DEVICES:
            url_params['skip'] = count_so_far
            try:
                response = self._get(URL_DEVICES, url_params=url_params)
                # validate response and yield devices
                yield from self._handle_devices_response(response)
            except Exception:
                logger.exception(f'Failed to get devices after {count_so_far}')
                break
            if len(response.get('devices')) < DEVICE_PER_PAGE:
                logger.info(f'Pagination finished, got total of {count_so_far}')
                break
            # increment counters
            this_page = len(response.get('devices'))
            count_so_far += this_page

    def _get_devices_backcompat(self):
        """
        Get devices non-paginated, for old api
        :return: yield a list of devices
        """
        try:
            response = self._get(URL_DEVICES)
        except Exception as e:
            message = f'Get devices failed! Details: {str(e)}'
            logger.error(message)
            raise RESTException(message)
        yield from self._handle_devices_response(response)

    @staticmethod
    def _handle_devices_response(response):
        err_message = None
        if not isinstance(response, dict):
            err_message = f'Expected response as dict, got instead {str(type(response))}'
        elif not isinstance(response.get('devices'), list):
            resp_type = type(response.get('devices'))
            err_message = f'Expected devices as list, got instead {str(resp_type)}'
        elif 'devices' not in response:
            err_message = f'Expected devices in dict, got instead {response}'
        if err_message:
            raise RESTException(err_message)
        yield from response.get('devices') or []

    def get_device_list(self):
        if self._use_backcompat_api:
            # if this raises an exception, let it rise up (means failed to get data)
            devices_raw = self._get_devices_backcompat()
        else:
            # if this raises an exception, let it rise up (means failed to get data)
            devices_raw = self._paginated_get_devices()
        # iterate over resulting devices
        for device in devices_raw:
            if not isinstance(device, dict):
                logger.warning(f'Bad device result. expected dict, got {str(type(device))}')
                logger.debug(f'Bad device result: got {str(device)}')
                continue
            hostname = device.get('hostname')  # needed for attributes in old api
            # Only check that hostname is str. Rhe request checks the hostname actual validity
            # and keeps minimum reliable information if details request fails, so we at least get _something_.
            if self._use_backcompat_api and isinstance(hostname, str):
                try:
                    url_params = {
                        'hostname': hostname,
                        'attributeName': None
                    }
                    attrs_response = self._get(URL_ATTRIBUTES, url_params=url_params)
                    attrs = attrs_response.get('attributes')
                    device.update(attrs)  # Flattening the dictionary to stay consistent across different API versions
                except Exception as e:
                    logger.warning(f'Got {str(e)} trying to fetch attributes for hostname {hostname}, device {device}')
            device['x_connected_switch'] = self._get_switch_port(device.get('mgmtIP'))
            yield device
