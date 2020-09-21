import logging
import datetime

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from axonius.utils.parsing import int_or_none
from axonius.clients.cyberark_epm.consts import DEVICE_PER_PAGE, MAX_NUMBER_OF_DEVICES, API_URL_BASE_PREFIX, \
    API_URL_AUTH_SUFFIX, AuthenticationMethods, DEFAULT_SESSION_REFRESH_SEC, API_URL_SETS_SUFFIX, \
    API_URL_COMPUTERS_SUFFIX, EXTRA_SET, API_URL_POLICIES_SUFFIX, POLICIES_PER_PAGE, EXTRA_POLICY

logger = logging.getLogger(f'axonius.{__name__}')

# pylint: disable=logging-format-interpolation


class CyberarkEpmConnection(RESTConnection):
    """ rest client for CyberarkEpm adapter """

    def __init__(self, *args, auth_method: str, app_id: str, **kwargs):
        super().__init__(*args, url_base_prefix=API_URL_BASE_PREFIX,
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._auth_method = auth_method
        self._api_suffix = API_URL_AUTH_SUFFIX.format(self._auth_method)
        self._app_id = app_id
        self._session_refresh = None

    def _refresh_token(self):
        if self._session_refresh and self._session_refresh > datetime.datetime.now():
            return

        self._get_token()

    def _get_token(self):
        try:
            body_params = {
                'ApplicationID': self._app_id
            }
            if self._auth_method == AuthenticationMethods.EPM.value:
                body_params['Username'] = self._username
                body_params['Password'] = self._password

            response = self._post(self._api_suffix, body_params=body_params)
            if not (isinstance(response, dict) and response.get('EPMAuthenticationResult')):
                raise RESTException(f'Failed getting token, received invalid response: {response}')

            self._session_refresh = datetime.datetime.now() + datetime.timedelta(sec=(DEFAULT_SESSION_REFRESH_SEC - 50))
            self._token = response.get('EPMAuthenticationResult')

            if self._auth_method == AuthenticationMethods.EPM.value:
                self._session_headers['Authorization'] = f'basic {self._token}'
            elif self._auth_method == AuthenticationMethods.Windows.value:
                self._session_headers['VFUser'] = self._token
            else:
                raise RESTException(f'Received unknown method for token authentication')

        except Exception as e:
            logger.exception('Error: Failed getting token, invalid request was made.')
            raise RESTException(f'Error: Failed getting token, invalid request was made. {str(e)}')

    def _connect(self):
        if not self._app_id:
            raise RESTException('No Application ID')

        if self._auth_method == AuthenticationMethods.EPM.value:
            if not (self._username and self._password):
                raise RESTException('No username or password')

        try:
            self._get_token()

            url_params = {
                'Offset': 0,  # Number to skip
                'Limit': 1  # Max number to return
            }
            self._get(API_URL_SETS_SUFFIX, url_params=url_params)

        except Exception as e:
            raise ValueError(f'Error: Invalid response from server, please check domain or credentials. {str(e)}')

    def _paginated_get_ids_of_sets(self):
        try:
            total_fetched_sets = 0

            url_params = {
                'Offset': 0,
                'Limit': 1
            }

            total_sets = MAX_NUMBER_OF_DEVICES
            self._refresh_token()
            response = self._get(API_URL_SETS_SUFFIX, url_params=url_params)
            if isinstance(response, dict) and int_or_none(response.get('SetsCount')):
                total_sets = min(int_or_none(response.get('SetsCount')), MAX_NUMBER_OF_DEVICES)

            url_params['Limit'] = DEVICE_PER_PAGE
            while url_params['Offset'] < total_sets:
                self._refresh_token()
                response = self._get(API_URL_SETS_SUFFIX, url_params=url_params)
                if not (isinstance(response, dict) and isinstance(response.get('Sets'), list)):
                    logger.warning(f'Received invalid response for sets: {response}')
                    continue

                for set_obj in response.get('Sets'):
                    if isinstance(set_obj, dict) and set_obj.get('Id'):
                        yield set_obj.get('Id'), set_obj
                        total_fetched_sets += 1

                if total_fetched_sets >= total_sets:
                    logger.info('Exceeded max number of sets.')
                    break

                if len(response.get('Sets')) < DEVICE_PER_PAGE:
                    logger.info(f'Done Sets pagination, last page got '
                                f'{len(response.get("Sets"))} / {DEVICE_PER_PAGE}')
                    break

                url_params['Offset'] += DEVICE_PER_PAGE

            logger.info(f'Got total of {total_fetched_sets} sets')
        except Exception:
            logger.exception(f'Invalid request made while paginating sets')
            raise

    def _paginated_get_ids_of_policies(self):
        try:
            policies = {}
            total_fetched_policies = 0

            for set_obj_id, set_obj_raw in self._paginated_get_ids_of_sets():
                total_set_fetched_policies = 0

                url_params = {
                    'Offset': 0,
                    'Limit': 1
                }

                total_policies = MAX_NUMBER_OF_DEVICES
                api_url_suffix = f'{API_URL_SETS_SUFFIX}/{set_obj_id}/{API_URL_POLICIES_SUFFIX}'
                self._refresh_token()
                response = self._get(api_url_suffix, url_params=url_params)
                if isinstance(response, dict) and int_or_none(response.get('TotalCount')):
                    total_policies = min(int_or_none(response.get('TotalCount')), MAX_NUMBER_OF_DEVICES)
                    logger.info(f'Total count of policies in set {set_obj_id} is {total_policies}')

                url_params['Limit'] = POLICIES_PER_PAGE
                while url_params['Offset'] < total_policies:
                    self._refresh_token()
                    response = self._get(api_url_suffix, url_params=url_params)
                    if not (isinstance(response, dict) and isinstance(response.get('Policies'), list)):
                        logger.warning(f'Received invalid response for Policies: {response}')
                        continue

                    for policy_raw in response.get('Policies'):
                        if not (isinstance(policy_raw, dict) and policy_raw.get('PolicyId')):
                            logger.warning(f'Received invalid policy_raw {policy_raw} of type {type(policy_raw)}')
                            continue

                        policy_url_suffix = f'{api_url_suffix}/{policy_raw.get("PolicyId")}'
                        response = self._get(policy_url_suffix)
                        if not (isinstance(response, dict) and
                                isinstance(response.get('IncludeComputersInSet'), list)):
                            logger.warning(f'Received invalid response for specific policy, ID: '
                                           f'{policy_raw.get("PolicyId")}')
                            continue

                        for computer_id in response.get('IncludeComputersInSet'):
                            # response has more detailed information about the computer
                            # policy_raw has extra information that not shown in the response
                            # we want all of the information and response will override policy_raw if have the same keys
                            policies[computer_id] = policy_raw
                            policies[computer_id].update(response)

                        total_set_fetched_policies += 1

                    if total_set_fetched_policies >= total_policies:
                        logger.info('Exceeded max number of policies.')
                        break

                    if len(response.get('Policies')) < DEVICE_PER_PAGE:
                        logger.info(f'Done Policies pagination in set {set_obj_id}, last page got '
                                    f'{len(response.get("Policies"))} / {POLICIES_PER_PAGE}')
                        break

                    url_params['Offset'] += POLICIES_PER_PAGE

                logger.info(f'Got Total of {total_set_fetched_policies} policies from set {set_obj_id}')
                total_fetched_policies += total_set_fetched_policies

            logger.info(f'Got total of {total_fetched_policies} Policies')
            return policies
        except Exception:
            logger.exception(f'Invalid request made while paginating policies')
            return {}

    def _paginated_computer_get(self):
        try:
            policies = self._paginated_get_ids_of_policies()

            total_fetched_computers = 0

            for set_obj_id, set_obj_raw in self._paginated_get_ids_of_sets():
                url_params = {
                    'Offset': 0,
                    'Limit': 1
                }

                total_computers = MAX_NUMBER_OF_DEVICES
                api_url_suffix = f'{API_URL_SETS_SUFFIX}/{set_obj_id}/{API_URL_COMPUTERS_SUFFIX}'
                self._refresh_token()
                response = self._get(api_url_suffix, url_params=url_params)
                if isinstance(response, dict) and int_or_none(response.get('TotalCount')):
                    total_computers = min(int_or_none(response.get('TotalCount')), MAX_NUMBER_OF_DEVICES)

                url_params['Limit'] = DEVICE_PER_PAGE
                while url_params['Offset'] < total_computers:
                    response = self._get(api_url_suffix, url_params=url_params)
                    if not (isinstance(response, dict) and isinstance(response.get('Computers'), list)):
                        logger.warning(f'Received invalid response for computers: {response}')
                        continue

                    for computer in response.get('Computers'):
                        if not isinstance(computer, dict):
                            logger.warning(f'Received invalid response for computer {computer}')
                            continue

                        if policies.get(computer.get('AgentId')):
                            computer[EXTRA_POLICY] = policies.get(computer.get('AgentId'))

                        computer[EXTRA_SET] = set_obj_raw
                        yield computer
                        total_fetched_computers += 1

                    if total_fetched_computers >= total_computers:
                        logger.info('Exceeded max number of computers.')
                        break

                    if len(response.get('Computers')) < DEVICE_PER_PAGE:
                        logger.info(f'Done Computers pagination, last page got '
                                    f'{len(response.get("Sets"))} / {DEVICE_PER_PAGE}')
                        break

                    url_params['Offset'] += DEVICE_PER_PAGE

                logger.info(f'Got total of {total_fetched_computers} Computers')
        except Exception:
            logger.exception(f'Invalid request made while paginating computers')
            raise

    def get_device_list(self):
        try:
            yield from self._paginated_computer_get()
        except RESTException as err:
            logger.exception(str(err))
            raise
