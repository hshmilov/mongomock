import logging
import ipaddress
from collections import defaultdict

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from iboss_cloud_adapter.consts import API_LOGIN_IDS, API_LOGIN_IDS_SUFFIX, API_DEVICES_ENDPOINTS, API_PAGINATION, \
    API_LOCALSUBNETS_SUFFIX, API_USER_ENDPOINT_SUFFIX, NODE_DEVICE, API_TOKEN_URL, API_SETTING_ID_URL, \
    API_DOMAINS_URL, API_CLOUD_NODES_URL, MAX_NUMBER_OF_DEVICES, MAX_NUMBER_OF_USERS

logger = logging.getLogger(f'axonius.{__name__}')


# pylint: disable=logging-format-interpolation


class IbossCloudConnection(RESTConnection):
    """ rest client for IbossCloud adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)

        self._uid = None
        self._token = None
        self._session_id = None
        self._setting_id = None
        self._api_domain = None
        self._b64_auth_str = None

    def _get_login_ids(self):
        try:
            if not self._token:
                error_message = 'Token is not set, cant make api calls'
                logger.exception(error_message)
                raise RESTException(error_message)

            body_params = dict(API_LOGIN_IDS)
            body_params['userName'] = self._token

            url = self._api_domain + API_LOGIN_IDS_SUFFIX
            response = self._post(url, body_params=body_params, force_full_url=True)
            if not isinstance(response, dict) or 'sessionId' not in response or 'uid' not in response:
                raise RESTException(f'Login IDS failed, received invalid response: {response}')

            return response.get('uid'), response.get('sessionId')
        except RESTException as e:
            raise RESTException(f'Error: API login failed, {str(e)}')

    def _get_domain(self):
        try:
            if not self._token:
                error_message = 'Token is not set, cant make api calls'
                logger.exception(error_message)
                raise RESTException(error_message)

            url_params = {
                'accountSettingsId': self._setting_id
            }
            response = self._get(API_DOMAINS_URL, url_params=url_params, force_full_url=True)
            if not isinstance(response, list):
                raise RESTException(f'Get domains failed, received invalid response: {response}')

            for domain in response:
                if not isinstance(domain, dict):
                    continue
                if domain.get('productFamily') == 'swg':
                    api_domain = domain.get('adminInterfaceDns') or domain.get('nodeHostname') or domain.get(
                        'nodeAdminInterfaceDns') or domain.get('masterAdminInterfaceDns')

                    if api_domain:
                        self._api_domain = 'https://' + api_domain
                        break

            if not self._api_domain:
                raise ValueError(f'Error: Failed fetching IBoss domain from {response}')

        except RESTException as e:
            raise RESTException(f'Error: Failed fetching IBoss domains {str(e)}')

    def _get_setting_id(self):
        try:
            if not self._token:
                error_message = 'Token is not set, cant make api calls'
                logger.exception(error_message)
                raise RESTException(error_message)

            response = self._get(API_SETTING_ID_URL, force_full_url=True)
            if not isinstance(response, list):
                raise RESTException(f'Get account settings id failed, received invalid response: {response}')

            for setting in response:
                if not isinstance(setting, dict):
                    continue

                if setting.get('accountSettingsId'):
                    self._setting_id = setting.get('accountSettingsId')
                    break

            if not self._setting_id:
                raise ValueError(f'Error: Failed fetching IBoss setting ID. {response}')

        except RESTException as e:
            raise RESTException(f'Error: Failed fetching IBoss Setting ID. {str(e)}')

    def _get_token(self):
        try:
            response = self._get(API_TOKEN_URL, force_full_url=True, do_basic_auth=True)

            if not isinstance(response, dict) or 'token' not in response:
                raise RESTException(f'Login failed, received invalid response: {response}')

            self._token = response.get('token')
            self._session_headers = {
                'Authorization': 'Token ' + self._token.strip()
            }

        except RESTException as e:
            raise RESTException(f'Error: Could not login to the server, please check domain or credentials. {str(e)}')

    # pylint: disable=arguments-differ
    def _do_request(self, *args, **kwargs):
        """
        Overriding _do_request for deleting cookies and refresh session id automatic
        Cookies should be deleted for different domains requests.
        :param args: args for RESTConnection._do_request()
        :param kwargs: kwargs for RESTConnection._do_request()
        :return: see RESTConnection._do_request()
        """
        # self._refresh_token()
        self._session.cookies.clear()
        return super()._do_request(*args, **kwargs)

    # pylint: disable=invalid-triple-quote
    def _connect(self):
        """
        Authentication process is a bit messy over here
        First we get the token, with the token we get the accountSettingsId.
        Using the Token and the accountSettingId we get the domain used for swg.
        Using the Token and the Domain we get the uid and sessionId.

        Now for each request we use Token as a header and uid and sessionId as url_params
        """
        if not self._username or not self._password:
            raise RESTException('No username or password')

        try:
            self._get_token()
            self._get_setting_id()
            self._get_domain()
            uid, session_id = self._get_login_ids()

            url_params = dict(API_PAGINATION)
            url_params['maxItems'] = 1
            url_params['sessionId'] = session_id
            url_params['uid'] = uid

            url = self._api_domain + API_USER_ENDPOINT_SUFFIX
            self._get(url, url_params=url_params, force_full_url=True)

        except Exception as e:
            raise ValueError(f'Error: Invalid response from server, please check domain or credentials. {str(e)}')

    def _get_local_subnets(self):
        try:
            policies_by_network = defaultdict(list)  # type: Dict[IPv4Network, List[dict]]

            uid, session_id = self._get_login_ids()
            url_params = {
                'uid': uid,
                'sessionId': session_id
            }
            url = self._api_domain + API_LOCALSUBNETS_SUFFIX
            response = self._get(url, url_params=url_params, force_full_url=True)
            if not (isinstance(response, dict) and isinstance(response.get('entries'), list)):
                logger.warning(f'Received invalid response for local subnets: {response}')
                return {}

            for policy_dict in response.get('entries'):
                if not isinstance(policy_dict, dict):
                    logger.debug(f'Invalid type of local subnets entries {response.get("entries")}')
                    break
                try:
                    network = f'{policy_dict.get("ipAddress")}/{policy_dict.get("subnet")}'
                    ip_network = ipaddress.ip_network(network)
                except Exception:
                    logger.exception(f'Failed creating ip_network for {network}')
                    continue
                policies_by_network[ip_network].append(policy_dict)

            return policies_by_network
        except Exception:
            logger.exception(f'Failed fetching Local Subnets')
            return {}

    def _paginated_device_get(self):
        try:
            local_subnets = self._get_local_subnets()

            for api_device_endpoint, device_instance in API_DEVICES_ENDPOINTS:
                full_url = self._api_domain + api_device_endpoint
                url_params = dict(API_PAGINATION)
                total_devices = 0
                while total_devices < MAX_NUMBER_OF_DEVICES:
                    url_params['uid'], url_params['sessionId'] = self._get_login_ids()
                    response = self._get(full_url, url_params=url_params, force_full_url=True)
                    if not (isinstance(response, dict) and isinstance(response.get('entries'), list)):
                        logger.warning(f'Received invalid response for devices: {response}')
                        continue

                    for device in response.get('entries'):
                        yield device, local_subnets, device_instance
                        total_devices += 1

                    if (response.get('staticDeviceCount') and total_devices >= response.get('staticDeviceCount')) or (
                            response.get('dynamicDeviceCount') and total_devices >= response.get(
                                'dynamicDeviceCount')) or len(response.get('entries')) < url_params['maxItems']:
                        logger.info(f'Done {device_instance} pagination, got {total_devices}')
                        break

                    url_params['currentRow'] += url_params['maxItems']
        except Exception as e:
            logger.exception(f'Invalid request made while paginating devices {str(e)}')
            raise

    def _paginated_node_get(self):
        try:
            local_subnets = self._get_local_subnets()
            url_params = {
                'accountSettingsId': self._setting_id
            }
            response = self._get(API_CLOUD_NODES_URL, url_params=url_params, force_full_url=True)
            if not isinstance(response, list):
                logger.warning(f'Received invalid response for nodes: {response}')
                return

            for node in response:
                if not isinstance(node, dict):
                    logger.warning(f'Received invalid node in response: {node}')
                    continue
                yield node, local_subnets, NODE_DEVICE

        except Exception as e:
            logger.exception(f'Invalid request made while paginating nodes {str(e)}')
            raise

    def get_device_list(self):
        try:
            yield from self._paginated_device_get()
        except RESTException as e:
            logger.exception(f'Failed paginating devices. {str(e)}')

        try:
            yield from self._paginated_node_get()
        except RESTException as e:
            logger.exception(f'Failed paginating nodes. {str(e)}')

    def _paginated_user_get(self):
        try:
            url_params = dict(API_PAGINATION)
            total_users = 0
            while total_users < MAX_NUMBER_OF_USERS:
                url_params['uid'], url_params['sessionId'] = self._get_login_ids()
                url = self._api_domain + API_USER_ENDPOINT_SUFFIX
                response = self._get(url, url_params=url_params, force_full_url=True)
                if not (isinstance(response, dict) and isinstance(response.get('entries'), list)):
                    logger.warning(f'Received invalid response for users: {response}')
                    continue

                for user in response.get('entries'):
                    yield user
                    total_users += 1

                if (response.get('userCount') and total_users >= response.get('userCount')) or \
                        len(response.get('entries')) < url_params['maxItems']:
                    logger.info(f'Done user pagination, got {total_users}')
                    break

                url_params['currentRow'] += url_params['maxItems']
        except Exception as e:
            logger.exception(f'Invalid request made while paginating users {str(e)}')
            raise

    def get_user_list(self):
        try:
            yield from self._paginated_user_get()
        except RESTException as e:
            logger.exception(str(e))
            raise
