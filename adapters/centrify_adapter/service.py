import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.utils.files import get_local_config_file
from centrify_adapter.connection import CentrifyConnection
from centrify_adapter.client_id import get_client_id
from centrify_adapter.structures import CentrifyUserInstance, CentrifyAccessListItem, \
    CentrifyUPData

logger = logging.getLogger(f'axonius.{__name__}')


class CentrifyAdapter(AdapterBase):

    class MyUserAdapter(CentrifyUserInstance):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'),
                                                https_proxy=client_config.get('https_proxy'))

    @staticmethod
    def get_connection(client_config):
        connection = CentrifyConnection(
            domain=client_config['domain'],
            verify_ssl=client_config['verify_ssl'],
            https_proxy=client_config.get('https_proxy'),
            username=client_config['username'],
            password=client_config['password'],
            app_id=client_config['app_id'],
            scope=client_config['scope']
        )
        with connection:
            pass  # check that the connection credentials are valid
        return connection

    def _connect_client(self, client_config):
        try:
            return self.get_connection(client_config)
        except RESTException as e:
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                client_config.get('domain'), str(e))
            logger.exception(message)
            raise ClientConnectionException(message)

    @staticmethod
    def _query_devices_by_client(client_name, client_data):
        """
        Get all devices from a specific  domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        with client_data:
            yield from client_data.get_device_list()

    @staticmethod
    # pylint: disable=arguments-differ
    def _query_users_by_client(client_name, client_data):
        """
        Get all users from a specific  domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        with client_data:
            yield from client_data.get_user_list()

    @staticmethod
    def _clients_schema():
        """
        The schema CentrifyAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Centrify Tenant URL',
                    'type': 'string'
                },
                {
                    'name': 'app_id',
                    'title': 'Application ID',
                    'type': 'string'
                },
                {
                    'name': 'scope',
                    'title': 'Client Scope',
                    'type': 'string'
                },
                {
                    'name': 'username',
                    'title': 'Client ID',
                    'type': 'string',
                },
                {
                    'name': 'password',
                    'title': 'Client Secret',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': 'verify_ssl',
                    'title': 'Verify SSL',
                    'type': 'bool'
                },
                {
                    'name': 'https_proxy',
                    'title': 'HTTPS Proxy',
                    'type': 'string'
                }
            ],
            'required': [
                'domain',
                'app_id',
                'scope',
                'username',
                'password',
                'verify_ssl'
            ],
            'type': 'array'
        }

    @staticmethod
    def _parse_bool(value):
        if isinstance(value, bool):
            return value
        return None

    @staticmethod
    def _parse_int(value):
        try:
            return int(value)
        except Exception:
            return None

    @classmethod
    def _fill_centrify_user_fields(cls, user_raw: dict, user: MyUserAdapter):
        try:
            user.uuid = user_raw.get('Uuid')
            user.reports_to = user_raw.get('ReportsTo')
            user.preferred_culture = user_raw.get('PreferredCulture')
            user.office_number = user_raw.get('OfficeNumber')
            user.mobile_number = user_raw.get('MobileNumber')
            user.home_number = user_raw.get('HomeNumber')
            updata = user_raw.get('x_apps')
            apps = list()
            if isinstance(updata, list):
                for app_raw in updata:
                    app_data = cls._parse_apo_data(app_raw)
                    if app_data:
                        apps.append(app_data)
            user.centrify_apps = apps or None
        except Exception:
            logger.exception(f'Failed creating instance for user {user_raw}')

    @classmethod
    def _parse_apo_data(cls, app_raw: dict):
        if not isinstance(app_raw, dict):
            return None
        try:
            access_raw = app_raw.get('AccessList')
            access_list = list()
            if isinstance(access_raw, list):
                for item in access_raw:
                    if not isinstance(item, dict):
                        continue
                    try:
                        access_list.append(CentrifyAccessListItem(
                            access_type=item.get('Type'),
                            item_id=item.get('ID'),
                            name=item.get('Name')
                        ))
                    except Exception as e:
                        logger.warning(f'Failed to parse access list item {item}: {str(e)}')
                        continue
            return CentrifyUPData(
                is_intranet=cls._parse_bool(app_raw.get('Intranet')),
                rowkey=app_raw.get('ID'),
                admin_tag=app_raw.get('AdminTag'),
                category=app_raw.get('Category'),
                shortcut=cls._parse_bool(app_raw.get('Shortcut')),
                display_name=app_raw.get('DisplayName'),
                app_type=app_raw.get('AppType'),
                is_username_ro=cls._parse_bool(app_raw.get('UsernameRO')),
                is_password_set=cls._parse_bool(app_raw.get('PasswordIsSet')),
                app_key=app_raw.get('AppKey'),
                rank=cls._parse_int(app_raw.get('Rank')),
                webapp_type_name=app_raw.get('WebAppTypeDisplayName'),
                app_username=app_raw.get('Username'),
                template_name=app_raw.get('TemplateName'),
                app_type_name=app_raw.get('AppTypeDisplayName'),
                automatic=cls._parse_bool(app_raw.get('Automatic')),
                access_list=access_list or None,
                url=app_raw.get('Url'),
                webapp_type=app_raw.get('WebAppType'),
                description=app_raw.get('Description'),
                name=app_raw.get('Name')
            )
        except Exception as e:
            logger.warning(f'Failed to parse app info for {app_raw}: {str(e)}')
            return None

    def _create_user(self, user_raw: dict, user: MyUserAdapter):
        try:
            user_id = user_raw.get('Uuid')
            if user_id is None:
                logger.warning(f'Bad user with no ID {user_raw}')
                return None
            user.id = user_id + '_' + (user_raw.get('Mail') or '')
            user.name = user_raw.get('Name')
            user.display_name = user_raw.get('DisplayName')
            user.mail = user_raw.get('Mail')
            user.description = user_raw.get('Description')
            user.user_telephone_number = user_raw.get('OfficeNumber')
            user.image = user_raw.get('PictureUri')
            updata = user_raw.get('x_apps')
            if isinstance(updata, list):
                for app_data in updata:
                    if not isinstance(app_data, dict):
                        continue
                    try:
                        app_links = app_data.get('Url')
                        user.add_user_application(
                            app_name=app_data.get('DisplayName'),
                            app_links=[app_links] if app_links else None
                        )
                    except Exception as e:
                        logger.warning(f'Failed to parse Axonius app data from {app_data}: {str(e)}')
            self._fill_centrify_user_fields(user_raw, user)

            user.set_raw(user_raw)

            return user
        except Exception:
            logger.exception(f'Problem with fetching Centrify User for {user_raw}')
            return None

    # pylint: disable=arguments-differ
    def _parse_users_raw_data(self, users_raw_data):
        """
        Gets raw data and yields User objects.
        :param users_raw_data: the raw data we get.
        :return:
        """
        for user_raw in users_raw_data:
            if not user_raw:
                continue
            try:
                # noinspection PyTypeChecker
                user = self._create_user(user_raw, self._new_user_adapter())
                if user:
                    yield user
            except Exception:
                logger.exception(f'Problem with fetching Centrify User for {user_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets, AdapterProperty.UserManagement]
