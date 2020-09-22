import logging
import ipaddress
from collections import defaultdict

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from iboss_cloud_adapter.consts import API_LOGIN_IDS, API_LOGIN_IDS_SUFFIX, API_DEVICES_ENDPOINTS, API_PAGINATION, \
    API_LOCALSUBNETS_SUFFIX, API_USER_ENDPOINT_SUFFIX, NODE_DEVICE, API_TOKEN_URL, API_SETTING_ID_URL, \
    API_DOMAINS_URL, API_CLOUD_NODES_URL, MAX_NUMBER_OF_DEVICES, MAX_NUMBER_OF_USERS, DEVICE_PER_PAGE, \
    CLOUD_CONNECTED_DEVICE, API_CLOUD_CONNECTED_SUFFIX, DOMAIN_CONFIG

logger = logging.getLogger(f'axonius.{__name__}')

# pylint: disable=logging-format-interpolation


# pylint: disable=invalid-triple-quote
class IbossCloudConnection(RESTConnection):
    """ rest client for IbossCloud adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)

        self._uid = None
        self._token = None
        self._setting_ids = []
        self._api_domains_swg = []
        self._api_domains_reports = []
        self._b64_auth_str = None

    def _get_login_ids(self, api_domain: str):
        try:
            if not self._token:
                error_message = 'Token is not set, cant make api calls'
                logger.exception(error_message)
                raise RESTException(error_message)

            body_params = dict(API_LOGIN_IDS)
            body_params['userName'] = self._token

            url = api_domain + API_LOGIN_IDS_SUFFIX
            response = self._post(url, body_params=body_params, force_full_url=True)
            if not isinstance(response, dict) or 'sessionId' not in response or 'uid' not in response:
                raise RESTException(f'Login IDS failed, received invalid response: {response}')

            return response.get('uid'), response.get('sessionId')
        except RESTException as e:
            raise RESTException(f'Error: API login failed, {str(e)}')

    # pylint: disable=too-many-nested-blocks
    def _get_reports_domains(self):
        api_domains_reports = set()

        for account_settings_id in self._setting_ids:
            try:
                url_params = {
                    'accountSettingsId': account_settings_id
                }
                response = self._get(API_DOMAINS_URL, url_params=url_params, force_full_url=True)
                if not isinstance(response, list):
                    raise RESTException(f'Get reports domains failed, received invalid response: {response}')

                for domain in response:
                    if not isinstance(domain, dict):
                        continue

                    if domain.get('productFamily') == 'reports':
                        api_domain_report = domain.get('adminInterfaceDns')

                        if api_domain_report and isinstance(api_domain_report, str):
                            if api_domain_report.endswith('/'):
                                api_domain_report = api_domain_report[:-1]
                            api_domain_report_url = f'https://{api_domain_report}'
                            api_domains_reports.add(api_domain_report_url)

            except RESTException as e:
                logger.exception(f'Error: Failed fetching IBoss reports domains for {account_settings_id}')

        self._api_domains_reports = list(api_domains_reports)

    def _get_swg_domain(self):
        api_domains_swg = set()

        for account_settings_id in self._setting_ids:
            try:
                url_params = {
                    'accountSettingsId': account_settings_id
                }
                response = self._get(API_DOMAINS_URL, url_params=url_params, force_full_url=True)
                if not isinstance(response, list):
                    raise RESTException(f'Get swg domain failed, received invalid response: {response}')

                for domain in response:
                    if not isinstance(domain, dict):
                        continue

                    if domain.get('productFamily') == 'swg':
                        api_domain_swg = domain.get('adminInterfaceDns')

                        if api_domain_swg and isinstance(api_domain_swg, str):
                            if api_domain_swg.endswith('/'):
                                api_domain_swg = api_domain_swg[:-1]
                            api_domain_swg_url = f'https://{api_domain_swg}'
                            api_domains_swg.add(api_domain_swg_url)

                            break

            except RESTException as e:
                logger.exception('Error: Failed fetching IBoss swg domain')

        self._api_domains_swg = list(api_domains_swg)

    def _get_domains(self):
        try:
            if not self._token:
                error_message = 'Token is not set, cant make api calls'
                logger.exception(error_message)
                raise RESTException(error_message)

            self._get_swg_domain()
            self._get_reports_domains()

            if not (self._api_domains_swg or self._api_domains_reports):
                raise ValueError('Error: Failed fetching IBoss domains')

        except RESTException as e:
            raise RESTException(f'Error: Failed fetching IBoss domains {str(e)}')

    def _get_setting_ids(self):
        try:
            if not self._token:
                error_message = 'Token is not set, cant make api calls'
                logger.exception(error_message)
                raise RESTException(error_message)

            response = self._get(API_SETTING_ID_URL, force_full_url=True)
            if not isinstance(response, list):
                raise RESTException(f'Get account settings id failed, received invalid response: {response}')

            setting_ids = set()
            for setting in response:
                if not isinstance(setting, dict):
                    continue

                if setting.get('accountSettingsId'):
                    setting_ids.add(setting.get('accountSettingsId'))

            if not setting_ids:
                raise ValueError(f'Error: Failed fetching IBoss setting ID. {response}')

            self._setting_ids = list(setting_ids)[::-1]

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
        First we get the token, with the token we get the accountSettingsIds.
        Using the Token and the accountSettingId we get the domain used for swg and report.
        Using the Token and the Domain we get the uid and sessionId.

        Now for each request we use Token as a header and uid and sessionId as url_params
        """
        if not self._username or not self._password:
            raise RESTException('No username or password')

        try:
            self._get_token()
            self._get_setting_ids()
            self._get_domains()
            uid, session_id = self._get_login_ids(self._api_domains_swg[0])

            url_params = dict(API_PAGINATION)
            url_params['maxItems'] = 1
            url_params['sessionId'] = session_id
            url_params['uid'] = uid

            url = self._api_domains_swg[0] + API_USER_ENDPOINT_SUFFIX
            self._get(url, url_params=url_params, force_full_url=True)

        except Exception as e:
            raise ValueError(f'Error: Invalid response from server, please check domain or credentials. {str(e)}')

    def _get_local_subnets(self):
        try:
            policies_by_network = defaultdict(list)  # type: Dict[IPv4Network, List[dict]]

            for api_domain in self._api_domains_swg:
                uid, session_id = self._get_login_ids(api_domain)
                url_params = {
                    'uid': uid,
                    'sessionId': session_id
                }
                url = api_domain + API_LOCALSUBNETS_SUFFIX
                try:
                    response = self._get(url, url_params=url_params, force_full_url=True)
                    if not (isinstance(response, dict) and isinstance(response.get('entries'), list)):
                        logger.error(f'Received invalid response in {url} for local subnets: {response}')
                        continue

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

                    logger.info(f'Got total of {len(policies_by_network)} subnets from {url}')
                except Exception:
                    logger.exception(f'Failed fetching local subnets for {url}')

            logger.info(f'Got total of {len(policies_by_network)} subnets')
            return policies_by_network
        except Exception:
            logger.exception(f'Failed fetching Local Subnets')
            return {}

    @staticmethod
    def _is_last_device_page(response: dict, total_devices: int, max_items: int):
        if response.get('staticDeviceCount') and total_devices >= response.get('staticDeviceCount'):
            return True

        if response.get('dynamicDeviceCount') and total_devices >= response.get('dynamicDeviceCount'):
            return True

        if len(response.get('entries')) < max_items:
            return True

        return False

    def _paginated_device_get(self):
        try:
            local_subnets = self._get_local_subnets()
            total_fetched_devices = 0

            for api_domain in self._api_domains_swg:
                for api_device_endpoint, device_instance in API_DEVICES_ENDPOINTS:

                    try:
                        full_url = api_domain + api_device_endpoint
                        url_params = dict(API_PAGINATION)
                        total_devices = 0
                        while total_devices < MAX_NUMBER_OF_DEVICES:
                            url_params['uid'], url_params['sessionId'] = self._get_login_ids(api_domain)
                            response = self._get(full_url, url_params=url_params, force_full_url=True)
                            if not (isinstance(response, dict) and isinstance(response.get('entries'), list)):
                                logger.warning(f'Received invalid response for devices: {response}')
                                continue

                            for device in response.get('entries'):
                                yield device, local_subnets, device_instance, api_domain
                                total_devices += 1

                            if self._is_last_device_page(response, total_devices, url_params['maxItems']):
                                logger.info(f'Last page had {len(response.get("entries"))} < {url_params["maxItems"]}')
                                break

                            url_params['currentRow'] += url_params['maxItems']
                    except Exception:
                        logger.exception(f'Failed paginating devices for {api_domain}')

                logger.info(f'Got total of {total_devices} of {device_instance} from {full_url}')
                total_fetched_devices += total_devices

            logger.info(f'Got total of {total_fetched_devices} of Devices')
        except Exception as e:
            logger.exception(f'Invalid request made while paginating devices {str(e)}')
            raise

    def _paginated_node_get(self):
        try:
            local_subnets = self._get_local_subnets()
            url_params = {
                'accountSettingsId': self._setting_ids[0]
            }
            response = self._get(API_CLOUD_NODES_URL, url_params=url_params, force_full_url=True)
            if not isinstance(response, list):
                logger.warning(f'Received invalid response for nodes: {response}')
                return

            for node in response:
                if not isinstance(node, dict):
                    logger.warning(f'Received invalid node in response: {node}')
                    continue
                yield node, local_subnets, NODE_DEVICE, DOMAIN_CONFIG

        except Exception as e:
            logger.exception(f'Invalid request made while paginating nodes {str(e)}')
            raise

    def _paginated_cloud_connected_device_get(self):
        for api_domain_report in self._api_domains_reports:
            try:
                full_url = api_domain_report + API_CLOUD_CONNECTED_SUFFIX

                url_params = {
                    'currentRowNumber': 1,  # Row 1 return same values as row 0
                    'maxItemsToReturn': DEVICE_PER_PAGE
                }
                total_devices = 0

                while total_devices < MAX_NUMBER_OF_DEVICES:
                    response = self._get(full_url, url_params=url_params, force_full_url=True)
                    if not isinstance(response, list):
                        logger.warning(f'Received invalid response for cloud connected devices: {response}')
                        continue

                    for device in response:
                        if isinstance(device, dict):
                            yield device, None, CLOUD_CONNECTED_DEVICE, api_domain_report
                            total_devices += 1

                    if len(response) != DEVICE_PER_PAGE:
                        logger.info(f'Last page had {len(response)} < {DEVICE_PER_PAGE}')
                        break

                    url_params['currentRowNumber'] += url_params['maxItemsToReturn']

                logger.info(f'Got total of {total_devices} from {api_domain_report} of {CLOUD_CONNECTED_DEVICE}')
            except Exception:
                logger.exception(f'Invalid request made while paginating {CLOUD_CONNECTED_DEVICE} '
                                 f'from {api_domain_report}')
                continue

    def get_device_list(self):
        try:
            yield from self._paginated_device_get()
        except RESTException as e:
            logger.exception(f'Failed paginating devices. {str(e)}')

        try:
            yield from self._paginated_node_get()
        except RESTException as e:
            logger.exception(f'Failed paginating nodes. {str(e)}')

        try:
            yield from self._paginated_cloud_connected_device_get()
        except RESTException as e:
            logger.exception(f'Failed paginating cloud connected devices. {str(e)}')

    def _paginated_user_get(self):
        try:
            total_fetched_users = 0

            for api_domain in self._api_domains_swg:
                url_params = dict(API_PAGINATION)
                total_users = 0
                try:
                    while total_fetched_users < MAX_NUMBER_OF_USERS:
                        url_params['uid'], url_params['sessionId'] = self._get_login_ids(api_domain)
                        url = api_domain + API_USER_ENDPOINT_SUFFIX
                        response = self._get(url, url_params=url_params, force_full_url=True)
                        if not (isinstance(response, dict) and isinstance(response.get('entries'), list)):
                            logger.warning(f'Received invalid response for users: {response}')
                            continue

                        for user in response.get('entries'):
                            yield user, None, None, url
                            total_users += 1

                        if (response.get('userCount') and total_users >= response.get('userCount')) or \
                                len(response.get('entries')) < url_params['maxItems']:
                            logger.info(f'Done Users pagination for {url}, got {total_users}')
                            break

                        url_params['currentRow'] += url_params['maxItems']

                    logger.info(f'Got total of {total_users} from Users from {url}')
                    total_fetched_users += total_users
                except Exception:
                    logger.exception(f'Failed paginating users for {api_domain}')

            logger.info(f'Got total of {total_fetched_users} from Users')
        except Exception as e:
            logger.exception(f'Invalid request made while paginating users {str(e)}')
            raise

    def get_user_list(self):
        try:
            # Using device get because it also contains information about users
            yield from self._paginated_device_get()
        except RESTException as e:
            logger.exception(f'Failed paginating devices. {str(e)}')

        try:
            # Using cloud connected device get because it also contains information about users
            yield from self._paginated_cloud_connected_device_get()
        except RESTException as e:
            logger.exception(f'Failed paginating cloud connected users. {str(e)}')

        try:
            yield from self._paginated_user_get()
        except RESTException as e:
            logger.exception(f'Failed paginating users. {str(e)}')
