# pylint: disable=import-error
import logging
from collections import defaultdict

from requests import Session
from requests.auth import HTTPBasicAuth
from zeep import Client
from zeep.transports import Transport
from zeep.helpers import serialize_object
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException

logger = logging.getLogger(f'axonius.{__name__}')

# pylint: disable=logging-format-interpolation

TEST_SERVICE_CONST = 123


class SkyboxConnection(RESTConnection):
    """ rest client for Skybox adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            url_base_prefix='',
            headers={'Content-Type': 'application/json', 'Accept': 'application/json'},
            **kwargs
        )
        self.client = None
        self.vclient = None

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')
        session = Session()
        session.auth = HTTPBasicAuth(self._username, self._password)
        if self._verify_ssl:
            session.verify = self._verify_ssl
        if self._proxies:
            session.proxies = self._proxies

        # Send a requests just to make sure this isa valid ssl. This has to be on a seperate thread, as the other
        # line uses the regular requests.get of the system which is preconfigured to ignore invalid certs
        session.get(f'{self._url}skybox/webservice/jaxws/network?wsdl', verify=self._verify_ssl)

        client = Client(f'{self._url}skybox/webservice/jaxws/network?wsdl', transport=Transport(session=session))

        with client.settings(raw_response=True):
            response = client.service.testService(TEST_SERVICE_CONST)
            if response.status_code == 401:
                raise ValueError(f'Error: Invalid Credentials')
            if response.status_code != 200:
                raise ValueError(f'Error in response: status code {response.status_code}. Content: {response.content}')

        # Do not try to fetch assets, as there is no pagination, and this can take time.
        self.client = client

        try:
            vclient = Client(f'{self._url}skybox/webservice/jaxws/vulnerabilities?wsdl',
                             transport=Transport(session=session))

            self.vclient = vclient
        except Exception:
            logger.exception(f'Problem connecting to vulnerabilities wsdl')
            self.vclient = None

    # pylint: disable=arguments-differ
    def get_device_list(self, fetch_fw=True):
        # The documentation does not specify any sign of pagination
        assets = serialize_object(self.client.service.findAssetsByNames(''))
        assets_status = assets.get('status') or {}
        if assets_status.get('code') != 0:
            raise ValueError(f'Bad Response: {assets_status}')

        assets_raw = assets['assets']

        vulnerabilities_by_host = defaultdict(list)
        try:
            if self.vclient:
                vulnerabilities_answer = serialize_object(self.vclient.service.getVulnerabilities(''))
                for vulnerability_raw in (vulnerabilities_answer or []):
                    host_id = vulnerability_raw.get('hostId')
                    if host_id:
                        vulnerabilities_by_host[str(host_id)].append(vulnerability_raw)
        except Exception:
            logger.exception(f'Problem fetching vulnerabilities')

        # Fetch firewalls rules
        firewalls_rules_by_id = defaultdict(list)
        if fetch_fw:
            try:
                firewalls = serialize_object(self.client.service.findFirewallsByName(''))
                if not isinstance(firewalls, dict):
                    logger.debug(f'Invalid firewalls type: {firewalls}')
                    raise Exception('Invalid firewalls type')
                firewalls_list = firewalls.get('fwElements')
                if not isinstance(firewalls_list, list):
                    logger.debug(f'Invalid firewalls_list type: {firewalls_list}')
                    raise Exception('Invalid firewalls type')
                for firewall_element in firewalls_list:
                    firewall_id = firewall_element.get('id')
                    if firewall_id:
                        firewall_access_rules = serialize_object(self.client.service.getAccessRules(firewall_element))
                        if not (isinstance(firewall_access_rules, dict) and
                                isinstance(firewall_access_rules.get('accessRules'), list)):
                            continue
                        firewalls_rules_by_id[str(firewall_id)].extend(firewall_access_rules.get('accessRules'))
            except Exception:
                logger.exception(f'Problem fetching firewall rules')

        return assets_raw, vulnerabilities_by_host, firewalls_rules_by_id
