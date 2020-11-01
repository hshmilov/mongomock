import datetime
import hashlib
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.smart_json_class import SmartJsonClass
from axonius.clients.rest.connection import RESTConnection
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field, ListField
from axonius.users.user_adapter import UserAdapter
from axonius.utils.files import get_local_config_file
from axonius.utils.datetime import parse_date
from axonius.mixins.configurable import Configurable
from okta_adapter.connection import OktaConnection

logger = logging.getLogger(f'axonius.{__name__}')


class ClientData(SmartJsonClass):
    published = Field(datetime.datetime, 'Published')
    ip = Field(str, 'IP')
    device = Field(str, 'Device')
    browser = Field(str, 'Browser')
    os = Field(str, 'OS')
    city = Field(str, 'City')
    state = Field(str, 'State')
    country = Field(str, 'Country')


class OktaAdapter(AdapterBase, Configurable):
    class MyDeviceAdapter(DeviceAdapter):
        pass

    class MyUserAdapter(UserAdapter):
        # pylint: disable=R0902
        manager_id = Field(str, 'Manager ID')
        user_clients = ListField(ClientData, 'User Clients')
        worker_status = Field(str, 'Worker Status')
        worker_type = Field(str, 'Worker Type')
        worker_sub_type = Field(str, 'Worker Sub Type')
        user_type = Field(str, 'User Type')
        hire_date = Field(datetime.datetime, 'Hire Date')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    def _get_client_id(self, client_config):
        api_declassified = hashlib.md5(client_config['api_key'].encode('utf-8')).hexdigest()
        return client_config['url'] + '_' + api_declassified

    def _test_reachability(self, client_config):
        return RESTConnection.test_reachability(client_config.get('url'),
                                                https_proxy=client_config.get('https_proxy'))

    def _connect_client(self, client_config):
        connection = OktaConnection(url=client_config['url'],
                                    api_key=client_config['api_key'],
                                    https_proxy=client_config.get('https_proxy'),
                                    parallel_requests=client_config.get('parallel_requests'))
        try:
            connection.is_alive()
        except Exception as e:
            raise ClientConnectionException(e)
        return connection

    # pylint: disable=W0221
    def _query_users_by_client(self, client_name, client_data):
        return client_data.get_users(fetch_apps=self.__fetch_apps,
                                     fetch_groups=self.__fetch_groups,
                                     fetch_factors=self.__fetch_factors,
                                     sleep_between_requests_in_sec=self.__sleep_between_requests_in_sec,
                                     fetch_logs=self.__fetch_logs)

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
                {
                    'name': 'parallel_requests',
                    'title': 'Number of parallel requests',
                    'type': 'integer',
                    'default': 75
                },
                {
                    'name': 'https_proxy',
                    'title': 'HTTPS Proxy',
                    'type': 'string'
                }

            ],
            'required': [
                'url',
                'api_key',
                'parallel_requests'
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
                try:
                    user.groups = user_raw.get('groups_data')
                except Exception:
                    logger.exception(f'Problem with groups for {user_raw}')
                user.account_disabled = user_raw.get('status') not in ('PROVISIONED', 'ACTIVE')
                user.user_status = user_raw.get('status')
                user.last_seen = parse_date(user_raw.get('lastLogin'))
                user.last_password_change = parse_date(user_raw.get('passwordChanged'))
                user.user_created = parse_date(user_raw.get('created'))
                mail = profile.get('email')
                user.mail = mail
                if self.__email_domain_whitelist and mail and '@' in str(mail):
                    domain_email = mail.lower().split('@')[-1]
                    if domain_email not in self.__email_domain_whitelist:
                        continue
                user.employee_id = profile.get('employeeNumber')
                user.hire_date = parse_date(profile.get('hire_date'))
                user.username = profile.get('login') or user.mail
                if not user.username:
                    # according to `user_adapter.py` - a username is required for every User adapter
                    logger.error('User without email and login from Okta')
                    continue
                log_data = user_raw.get('log_data')
                if not isinstance(log_data, list):
                    log_data = []
                for log_raw in log_data:
                    try:
                        client_raw = log_raw.get('client')
                        if not isinstance(client_raw, dict):
                            client_raw = {}
                        user_agent = client_raw.get('userAgent')
                        if not isinstance(user_agent, dict):
                            user_agent = {}
                        geographical_context = client_raw.get('geographicalContext')
                        if not isinstance(geographical_context, dict):
                            geographical_context = {}

                        client_obj = ClientData(published=parse_date(log_raw.get('published')),
                                                ip=client_raw.get('ipAddress'),
                                                device=client_raw.get('device'),
                                                browser=user_agent.get('browser'),
                                                os=user_agent.get('os'),
                                                city=geographical_context.get('city'),
                                                state=geographical_context.get('state'),
                                                country=geographical_context.get('country'))
                        user.user_clients.append(client_obj)
                    except Exception:
                        logger.exception(f'Problem with log {log_raw}')
                user.first_name = profile.get('firstName')
                user.last_name = profile.get('lastName')
                user.user_telephone_number = profile.get('mobilePhone')
                user.user_title = profile.get('Job_Title') or profile.get('title')
                user.last_logon = parse_date(user_raw.get('lastLogin'))
                user.last_password_change = parse_date(user_raw.get('passwordChanged'))
                user.user_department = profile.get('department')
                user.user_country = profile.get('countryCode')
                user.manager_id = profile.get('managerId')
                user.worker_status = profile.get('workerStatus')
                user.worker_type = profile.get('workerType')
                user.worker_sub_type = profile.get('workerSubType')
                user.user_type = profile.get('userType')
                try:
                    for app in user_raw.get('apps_data') or []:
                        if app.get('status') != 'ACTIVE':
                            # We want only active apps
                            continue
                        app_name = app.get('label') or app.get('name')
                        if not app_name:
                            continue
                        app_links = []
                        try:
                            for item_raw in ((app.get('settings') or {}).get('app') or {}).values():
                                try:
                                    if isinstance(item_raw, str) and item_raw.lower().startswith('http'):
                                        app_links.append(item_raw)
                                except Exception:
                                    pass
                        except Exception:
                            logger.exception(f'Problem getting loginURl')
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
                    'name': 'email_domain_whitelist',
                    'type': 'string',
                    'title': 'Email domain whitelist'
                },
                {
                    'name': 'fetch_apps',
                    'title': 'Fetch users apps',
                    'type': 'bool'
                },
                {
                    'name': 'fetch_groups',
                    'title': 'Fetch users groups',
                    'type': 'bool'
                },
                {
                    'name': 'fetch_factors',
                    'title': 'Fetch users authentication factors',
                    'type': 'bool'
                },
                {
                    'name': 'sleep_between_requests_in_sec',
                    'type': 'integer',
                    'title': 'Time in seconds to sleep between each request'
                },
                {
                    'name': 'fetch_logs',
                    'type': 'bool',
                    'title': 'Fetch logs'
                }
            ],
            'required': [
                'fetch_apps',
                'fetch_factors',
                'fetch_groups',
                'fetch_logs'
            ],
            'pretty_name': 'Okta Configuration',
            'type': 'array'
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'fetch_apps': False,
            'fetch_factors': False,
            'fetch_logs': False,
            'email_domain_whitelist': None,
            'sleep_between_requests_in_sec': None,
            'fetch_groups': True
        }

    def _on_config_update(self, config):
        self.__fetch_apps = config['fetch_apps']
        self.__fetch_factors = config.get('fetch_factors')
        self.__fetch_logs = config.get('fetch_logs')
        self.__sleep_between_requests_in_sec = config.get('sleep_between_requests_in_sec') or 0
        self.__fetch_groups = config.get('fetch_groups') if 'fetch_groups' in config else True
        self.__email_domain_whitelist = config['email_domain_whitelist'].lower().split(',') \
            if config.get('email_domain_whitelist') else None
