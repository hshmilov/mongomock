import logging
import copy

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from f5_icontrol_adapter.consts import MAX_NUMBER_OF_DEVICES, MAX_EXCEPTION_COUNT, DEVICE_PER_PAGE, SERVER_TYPES
logger = logging.getLogger(f'axonius.{__name__}')


class F5IcontrolConnection(RESTConnection):
    """ rest client for F5Icontrol adapter """

    def __init__(self, login_provider, *args, **kwargs):
        super().__init__(*args, url_base_prefix='',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._login_provider = login_provider

    def _get_ltm(self, name, top, skip=0, expand_subcollections=True):
        """ perform one ltm get request """
        url = f'mgmt/tm/ltm/{name}'
        params = {
            '$top': top,
        }
        if skip:
            params['$skip'] = skip
        if expand_subcollections:
            params['expandSubcollections'] = 'true'
        return self._get(url, url_params=params)

    def _get_ltm_iter(self, name, expand_subcollections=True):
        """ yield all values from given ltm name """
        for page in range(0, MAX_NUMBER_OF_DEVICES, DEVICE_PER_PAGE):
            for _ in range(MAX_EXCEPTION_COUNT):
                try:
                    result = self._get_ltm(name,
                                           skip=(page * DEVICE_PER_PAGE),
                                           top=DEVICE_PER_PAGE)
                    items = result.get('items') or []
                    yield from items
                    if len(items) < DEVICE_PER_PAGE:
                        return
                    break
                except Exception:
                    logger.error('get ltm failed')
            else:
                raise RESTException(f'Failed to get ltm iter {name}')

    def _connect(self):
        if not self._username or not self._password or not self._login_provider:
            raise RESTException('No username or password')
        creds = {
            'username': self._username,
            'password': self._password,
            'loginProviderName': self._login_provider,
        }

        resp = self._post('mgmt/shared/authn/login', body_params=creds)
        token = (resp.get('token') or {}).get('token')
        if not token:
            raise RESTException(f'Unable to find token in {resp}')
        self._session_headers['X-F5-Auth-Token'] = token

        session_timeout = {
            'timeout': '36000',
        }

        self._patch(f'mgmt/shared/authz/tokens/{token}', body_params=session_timeout)
        self._validate_permission()

    def _validate_permission(self):
        """ validate the given user has enough permission by fetching
            one pool and one server list.
            Throws RESTException if fail. """
        self._get_ltm('virtual', top=1)
        self._get_ltm('pool', top=1)

    def get_device_list(self):
        yield from self._get_ltm_iter('virtual')
        for pool in self._get_ltm_iter('pool'):
            try:
                members = copy.deepcopy(((pool.get('membersReference') or {}).get('items') or []))
                del pool['membersReference']
                if not members:
                    logger.warning(f'no members for pool {pool}')
                    continue
                for member in members:
                    kind = member.get('kind')
                    if kind != SERVER_TYPES.pool_members:
                        logger.warning(f'Invalid kind {kind}')
                        continue
                    pool_raw = copy.deepcopy(pool)
                    pool_raw['member'] = member
                    yield pool_raw
            except Exception:
                logger.exception('Failed to fetch pool')
                continue
