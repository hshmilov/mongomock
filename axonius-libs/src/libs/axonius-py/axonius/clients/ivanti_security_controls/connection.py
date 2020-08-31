import logging
from requests_ntlm import HttpNtlmAuth  # pylint: disable=import-error

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from axonius.clients.ivanti_security_controls.consts import API_URL_PREFIX, AGENTS_PER_PAGE, MAX_NUMBER_OF_AGENTS, \
    API_AGENTS_SUFFIX, API_POLICIES_SUFFIX, MAX_NUMBER_OF_POLICIES, EXTRA_POLICY_INFO

logger = logging.getLogger(f'axonius.{__name__}')

# pylint: disable=logging-format-interpolation


class IvantiSecurityControlsConnection(RESTConnection):
    """ rest client for IvantiSecurityControls adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix=API_URL_PREFIX,
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)

    def _connect(self):
        if not (self._username and self._password):
            raise RESTException('No username or password')

        try:
            self._session.auth = HttpNtlmAuth(self._username, self._password)

            url_params = {
                'start': 1,
                'count': 1
            }
            self._get(API_AGENTS_SUFFIX, url_params=url_params)
        except Exception as e:
            raise ValueError(f'Error: Invalid response from server, please check domain or credentials. {str(e)}')

    def _get_agent_policies_by_id(self):
        policies = {}
        total_policies = 0
        try:
            response = self._get(API_POLICIES_SUFFIX)
            if not (isinstance(response, dict) and isinstance(response.get('value'), list) and response.get('count')):
                logger.warning(f'Received invalid response while getting policies. {response}')
                return policies

            for policy in response.get('value') or []:
                if not (isinstance(policy, dict) and policy.get('id')):
                    logger.warning(f'Received invalid policy - {type(policy)}. {policy}')
                    continue

                if total_policies >= MAX_NUMBER_OF_POLICIES:
                    logger.debug(f'Got too many policies, {total_policies} out of {len(response.get("value"))}')
                    break

                policies[policy.get('id')] = policy
                total_policies += 1

            logger.info(f'Got total of {total_policies} policies')
            return policies
        except Exception:
            logger.exception(f'Invalid request was made while fetching policies')
            return policies

    def _paginated_agent_get(self):
        try:
            total_agents = 0
            policies = self._get_agent_policies_by_id()

            url_params = {
                'start': 1,
                'count': AGENTS_PER_PAGE
            }

            while url_params['start'] * AGENTS_PER_PAGE < MAX_NUMBER_OF_AGENTS:
                response = self._get(API_AGENTS_SUFFIX, url_params=url_params)

                if not (isinstance(response, dict) and isinstance(response.get('value'), list)):
                    logger.warning(f'Received invalid response while getting agents. {response}')
                    break

                for agent in response.get('value'):
                    if not isinstance(agent, dict):
                        logger.warning(f'Received invalid format of agent - {type(agent)}. {agent}')
                        continue

                    if agent.get('assignedPolicyId'):
                        agent[EXTRA_POLICY_INFO] = policies.get(agent.get('assignedPolicyId'))

                    yield agent
                    total_agents += 1

                if len(response.get('value')) != AGENTS_PER_PAGE:
                    logger.info('Finished paginating agents')
                    break

                url_params['start'] += 1

            logger.info(f'Got total of {total_agents} agents')
        except Exception:
            logger.exception(f'Invalid request made while paginating agents')
            raise

    def get_device_list(self):
        try:
            yield from self._paginated_agent_get()
        except RESTException as err:
            logger.exception(str(err))
            raise
