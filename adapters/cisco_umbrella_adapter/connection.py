import logging
import time

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from cisco_umbrella_adapter.consts import (DEVICE_PER_PAGE, MAX_PAGES_NUMBER,
                                           MAX_REQUEST_TRIES, RATE_LIMIT_SLEEP)

logger = logging.getLogger(f'axonius.{__name__}')


class CiscoUmbrellaConnection(RESTConnection):
    """ rest client for CiscoUmbrella adapter """

    def __init__(self, *args, network_api_key, network_api_secret,
                 management_api_key, management_api_secret, msp_id, **kwargs):
        self._network_api_key = network_api_key
        self._network_api_secret = network_api_secret
        self._management_api_key = management_api_key
        self._management_api_secret = management_api_secret
        self._msp_id = msp_id
        super().__init__(*args, url_base_prefix='v1', headers={'Content-Type': 'application/json',
                                                               'Accept': 'application/json'}, **kwargs)
    # pylint: disable=arguments-differ

    def _do_request(self, *args, **kwargs):
        nkwargs = kwargs.copy()
        nkwargs.pop('raise_for_status', None)
        nkwargs.pop('return_response_raw', None)
        nkwargs.pop('use_json_in_response', None)
        nkwargs.pop('do_basic_auth', None)
        for try_ in range(MAX_REQUEST_TRIES):
            response = super()._do_request(
                *args,
                do_basic_auth=True,
                raise_for_status=False,
                return_response_raw=True,
                use_json_in_response=False,
                **nkwargs
            )
            if response.status_code == 429:
                time.sleep(RATE_LIMIT_SLEEP)
                continue
            break
        else:
            raise RESTException(f'Failed to fetch because rate limit')
        return self._handle_response(response)
    # pylint: enable=arguments-differ

    def _set_management_auth(self):
        self._username = self._management_api_key
        self._password = self._management_api_secret

    def _set_network_auth(self):
        self._username = self._network_api_key
        self._password = self._network_api_secret

    def _get_organizations(self):
        organizations = set()

        self._set_network_auth()

        result = self._get('organizations/')
        if isinstance(result, list):
            customers = filter(None, [org_raw.get('organizationId') for org_raw in result])
            organizations = organizations.union(set(customers))

        self._set_management_auth()

        if self._msp_id:
            result = self._get(f'msps/{self._msp_id}/customers')
            if isinstance(result, list):
                customers = filter(None, [org_raw.get('customerId') for org_raw in result])
                organizations = organizations.union(set(customers))

        return list(organizations)

    def _connect(self):
        if not self._network_api_key or not self._network_api_secret \
                or not self._management_api_key or not self._management_api_secret:
            raise RESTException('Missing API keys')

        organizations = self._get_organizations()
        if not organizations:
            raise RESTException('Unable to fetch organization ID')

    def get_device_list(self):
        organizations = self._get_organizations()

        self._set_management_auth()

        for org_id in organizations:
            try:
                yield from self.get_device_list_from_org(org_id)
            except Exception:
                logger.exception(f'Problem getting org {org_id}')

    def get_device_list_from_org(self, org_id):
        if not org_id:
            return

        for page in range(1, MAX_PAGES_NUMBER):
            try:
                devices_raw = self._get(f'organizations/{org_id}/roamingcomputers',
                                        url_params={'page': page,
                                                    'limit': DEVICE_PER_PAGE})
                if not devices_raw:
                    break
                yield from devices_raw
            except Exception:
                logger.exception(f'Org {org_id}: Failed to get page {page}')
                break
