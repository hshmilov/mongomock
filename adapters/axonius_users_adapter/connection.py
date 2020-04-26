import logging

from typing import Generator, Tuple

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from axonius_users_adapter import consts

logger = logging.getLogger(f'axonius.{__name__}')


class AxoniusUsersConnection(RESTConnection):
    """ rest client for Axonius Users adapter """

    def __init__(self, *args, api_secret: str, **kwargs):
        super().__init__(*args, url_base_prefix='/api/V1',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._api_secret = api_secret

    def _connect(self):
        if not self._apikey or not self._api_secret:
            raise RESTException('No API Key or API Secret')
        self._session_headers.update({
            'api-key': self._apikey,
            'api-secret': self._api_secret,
        })
        _ = next(self._iter_system_users(limit=1))

    def _paginated_get(self, *args, offset=0, limit=consts.MAX_NUMBER_OF_DEVICES, **kwargs):
        url_params = kwargs.setdefault('url_params', {})
        url_params.setdefault('limit', consts.DEVICE_PER_PAGE)
        count_so_far = 0
        while count_so_far < limit:
            url_params['skip'] = offset + count_so_far
            response = self._get(*args, **kwargs)
            if not isinstance(response, list):
                logger.error(f'Got invalid response on offset {offset} after {count_so_far}: {response}')
                return

            yield from response
            if len(response) == 0:
                logger.info(f'Done pagination after {count_so_far}')
                return
            count_so_far += len(response)

    def _iter_system_users(self, limit=consts.MAX_NUMBER_OF_DEVICES):
        for user in self._paginated_get('system/users', limit=limit):
            if not isinstance(user, dict):
                logger.error(f'Invalid user received: {user}')
                continue
            if 'password' in user:
                # remove 'password' field if present, otherwise it'll be seen in the "View Advanced"
                del user['password']
            yield user

    def _iter_system_roles_by_id(self) -> Generator[Tuple[str, dict], None, None]:
        response = self._get('system/roles')
        if not isinstance(response, list):
            logger.error(f'Invalid roles receive: {response}')
            return
        for role in response:
            if not (isinstance(role, dict) and isinstance(role.get('uuid'), str)):
                logger.error(f'Invalid role encountered: {role}')
                continue
            yield (role['uuid'], role)

    def get_user_list(self):
        role_by_id = dict(self._iter_system_roles_by_id())

        def __try_get_user_role(user):
            if not (isinstance(user.get('role_id'), str) and role_by_id.get(user.get('role_id'))):
                logger.warning(f'User with no role or role doesnt exist: {user}')
                return None
            return role_by_id[user['role_id']]

        for user in self._iter_system_users():
            user_role = __try_get_user_role(user)
            if user_role:
                user['role'] = user_role
            yield user

    def get_device_list(self):
        pass
