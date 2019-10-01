import hashlib
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field
from axonius.users.user_adapter import UserAdapter
from axonius.utils.files import get_local_config_file
from axonius.utils.datetime import parse_date
from axonius.mixins.configurable import Configurable
from okta_adapter.connection import OktaConnection

logger = logging.getLogger(f'axonius.{__name__}')


class OktaAdapter(AdapterBase, Configurable):
    class MyDeviceAdapter(DeviceAdapter):
        pass

    class MyUserAdapter(UserAdapter):
        # pylint: disable=R0902
        manager_id = Field(str, 'Manager ID')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    def _get_client_id(self, client_config):
        api_declassified = hashlib.md5(client_config['api_key'].encode('utf-8')).hexdigest()
        return client_config['url'] + '_' + api_declassified

    def _test_reachability(self, client_config):
        return RESTConnection.test_reachability(client_config.get('url'))

    def _connect_client(self, client_config):
        connection = OktaConnection(url=client_config['url'],
                                    api_key=client_config['api_key'])
        try:
            connection.is_alive()
        except Exception as e:
            raise ClientConnectionException(e)
        return connection

    # pylint: disable=W0221
    def _query_users_by_client(self, client_name, client_data):
        return client_data.get_users(self.__parallel_requests,
                                     fetch_apps=self.__fetch_apps,
                                     fetch_factors=self.__fetch_factors)

    def _clients_schema(self):
        return {
            'items': [
                {
                    'name': 'url',
                    'title': 'Okta URL',
                    'type': 'string'
                },
                {
                    'name': 'api_key',
                    'title': 'Okta API key',
                    'type': 'string',
                    'format': 'password'
                },
            ],
            'required': [
                'url',
                'api_key',
            ],
            'type': 'array'
        }

    # pylint: disable=W0221
    # pylint: disable=too-many-branches, too-many-statements, too-many-locals, too-many-nested-blocks
    def _parse_users_raw_data(self, raw_data):
        for user_raw in raw_data:
            try:
                # Schema defined here https://developer.okta.com/docs/api/resources/users#user-model
                user = self._new_user_adapter()
                profile = user_raw['profile']
                user.id = user_raw['id']
                user.groups = user_raw.get('groups_data')
                user.account_disabled = user_raw.get('status') not in ('PROVISIONED', 'ACTIVE')
                user.user_status = user_raw.get('status')
                user.last_seen = parse_date(user_raw.get('last_login'))
                user.last_password_change = parse_date(user_raw.get('passwordChanged'))
                user.user_created = parse_date(user_raw.get('created'))
                user.mail = profile.get('email')
                user.username = profile.get('login') or user.mail
                if not user.username:
                    # according to `user_adapter.py` - a username is required for every User adapter
                    logger.error('User without email and login from Okta')
                    continue
                user.first_name = profile.get('firstName')
                user.last_name = profile.get('lastName')
                user.user_telephone_number = profile.get('mobilePhone')
                user.user_title = profile.get('Job_Title') or profile.get('title')
                user.last_logon = parse_date(user_raw.get('lastLogin'))
                user.last_password_change = parse_date(user_raw.get('passwordChanged'))
                user.user_department = profile.get('department')
                user.user_country = profile.get('countryCode')
                user.manager_id = profile.get('managerId')
                try:
                    for app in user_raw.get('apps') or []:
                        if app.get('status') != 'ACTIVE':
                            # We want only active apps
                            continue
                        app_name = app.get('label') or app.get('name')
                        if not app_name:
                            continue
                        app_links = []
                        try:
                            for link_raw in app.get('_links').get('appLinks'):
                                if link_raw.get('href'):
                                    app_links.append(link_raw.get('href'))
                        except Exception:
                            logger.exception(f'Problem getting link for {app}')
                        if not app_links:
                            app_links = None
                        user.add_user_application(app_name=app_name,
                                                  app_links=app_links)

                except Exception:
                    logger.exception(f'Problem getting apps for {user_raw}')
                try:
                    for factor_raw in (user_raw.get('factors_raw') or []):
                        try:
                            user.add_user_factor(factor_type=factor_raw.get('factorType'),
                                                 factor_status=factor_raw.get('status'),
                                                 vendor_name=factor_raw.get('vendorName'),
                                                 provider=factor_raw.get('provider'),
                                                 last_updated=parse_date(factor_raw.get('lastUpdated')),
                                                 created=parse_date(factor_raw.get('created')))
                        except Exception:
                            logger.exception(f'Problem with factor {factor_raw}')
                except Exception:
                    logger.exception(f'Problem parsing factors')
                user.set_raw(user_raw)
                yield user
            except Exception:
                logger.exception(f'Problem parsing user: {str(user_raw)}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.UserManagement]

    @classmethod
    def _db_config_schema(cls) -> dict:
        return {
            'items': [
                {
                    'name': 'fetch_apps',
                    'title': 'Should fetch Users Apps',
                    'type': 'bool'
                },
                {
                    'name': 'fetch_factors',
                    'title': 'Should fetch Users Authentication Factors',
                    'type': 'bool'
                },
                {
                    'name': 'parallel_requests',
                    'title': 'Number of parallel requests',
                    'type': 'integer'
                }
            ],
            'required': [
                'fetch_apps',
                'parallel_requests',
                'fetch_factors'
            ],
            'pretty_name': 'Okta Configuration',
            'type': 'array'
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'fetch_apps': False,
            'fetch_factors': False,
            'parallel_requests': 75
        }

    def _on_config_update(self, config):
        self.__fetch_apps = config['fetch_apps']
        self.__parallel_requests = config['parallel_requests']
        self.__fetch_factors = config.get('fetch_factors')
