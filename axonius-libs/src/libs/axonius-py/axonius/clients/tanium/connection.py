# pylint: disable=E0401
# pylint: disable=invalid-triple-quote, pointless-string-statement
import json
import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException

logger = logging.getLogger(f'axonius.{__name__}')


# pylint: disable=abstract-method
class TaniumConnection(RESTConnection):
    def _get_workbenches_meta(self):
        try:
            return self._get(f'nocache/config/workbenches.json')
        except Exception as exc:
            raise RESTException(f'Tanium Platform: ERROR while fetching workbenches metadata: {exc}')

    def _connect(self):
        self._test_reachability()
        self._login()

    def _login(self):
        body_params = {'username': self._username, 'password': self._password}
        response = self._post('api/v2/session/login', body_params=body_params)
        if not response.get('data') or not response['data'].get('session'):
            raise RESTException(f'Bad login response: {response}')
        self._session_headers['session'] = response['data']['session']

    def _get_version(self):
        if not hasattr(self, '_platform_version'):
            try:
                response = self._get('config/console.json')
            except Exception as exc:
                raise RESTException(f'Error getting version from Tanium Platform: {exc}')
            version = response.get('serverVersion')
            if not version:
                raise RESTException(f'Tanium Platform: ERROR empty serverVersion in {response!r}')
            self._platform_version = version
            logger.info(f'Platform version: {self._platform_version!r}')
        return self._platform_version

    @property
    def module_name(self):
        return None

    def _get_module_version(self):
        if getattr(self, 'module_name', None):
            if not hasattr(self, '_module_version'):
                workbenches = self._get_workbenches_meta()
                if self.module_name not in workbenches:
                    raise RESTException(f'Module {self.module_name!r} not found in workbenches {list(workbenches)}')

                module = workbenches[self.module_name]
                if 'version' not in module:
                    msg = f'"version" not found in workbench module {self.module_name!r} in {list(module)}'
                    raise RESTException(msg)

                self._module_version = module['version']
                logger.info(f'Module {self.module_name!r} version: {self._module_version!r}')
            return self._module_version
        return None

    def _test_reachability(self):
        # get the tanium version, could be used as connectivity test as it's not an auth/api call
        self._get_version()
        self._get_module_version()

    def _tanium_get(self, endpoint, options=None):
        url = 'api/v2/' + endpoint
        response = self._get(url, extra_headers={'tanium-options': json.dumps(options or {})})
        if not response.get('data'):
            raise RESTException(f'Platform: Bad response with no data for endpoint {endpoint!r}')
        return response['data']

    def _get_by_hash(self, objtype: str, value: str) -> dict:
        return self._tanium_get(endpoint=f'{objtype}/by-hash/{value}')

    def _get_by_id(self, objtype: str, value: str) -> dict:
        return self._tanium_get(endpoint=f'{objtype}/{value}')

    def _get_by_name(self, objtype: str, value: str) -> dict:
        return self._tanium_get(endpoint=f'{objtype}/by-name/{value}')
