import datetime
import logging

# pylint: disable=import-error
from keycloak import KeycloakAdmin

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection, RESTException
from axonius.fields import Field, ListField
from axonius.smart_json_class import SmartJsonClass
from axonius.users.user_adapter import UserAdapter
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file

logger = logging.getLogger(f'axonius.{__name__}')


class UserConsentRepresentation(SmartJsonClass):
    client_id = Field(str, 'Client ID')
    created = Field(datetime.datetime, 'Created Date')
    granted_client_scopes = ListField(str, 'Granted Client Scopes')
    updated = Field(datetime.datetime, 'Last Updated Date')


class FederatedIdentity(SmartJsonClass):
    prov = Field(str, 'Identity Provider')
    user_id = Field(str, 'User ID')
    username = Field(str, 'User Name')


class KeycloakMapObj(SmartJsonClass):
    key = Field(str, 'Key')
    val = Field(str, 'Value')


class KeycloakAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyUserAdapter(UserAdapter):
        count_creds = Field(int, 'Credentials Count')
        enabled = Field(bool, 'Enabled')
        email_verified = Field(bool, 'Email Verified')
        fed_link = Field(str, 'Federation Link')
        self_str = Field(str, 'Self')
        origin = Field(str, 'Origin')
        svc_acct_client_id = Field(str, 'Service Account Client ID')
        realm_roles = ListField(str, 'Realm Roles')
        req_actions = ListField(str, 'Required Actions')
        disableable_cred_types = ListField(str, 'Disableable Credential Types')
        access = ListField(KeycloakMapObj, 'Access')
        attrs = ListField(KeycloakMapObj, 'Attributes')
        consent = ListField(UserConsentRepresentation, 'User Consent')
        fed_ids = ListField(FederatedIdentity, 'Federated Identities')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return f'Keycloak_{client_config["domain"]}_{client_config["username"]}'

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'))

    @staticmethod
    def get_connection(client_config):
        domain = client_config['domain']
        if not (domain.endswith('auth') or domain.endswith('auth/')):
            if domain.endswith('/'):
                domain = domain + 'auth/'
            else:
                domain = domain + '/auth/'
        connection = KeycloakAdmin(server_url=domain,
                                   username=client_config['username'],
                                   password=client_config['password'],
                                   realm_name=client_config.get('realm_name') or 'master',
                                   client_id=client_config.get('client_id') or 'admin-cli',
                                   verify=client_config['verify_ssl'],
                                   client_secret_key=client_config['client_secret'])
        return connection

    def _connect_client(self, client_config):
        try:
            return self.get_connection(client_config)
        except RESTException as e:
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                client_config['domain'], str(e))
            logger.exception(message)
            raise ClientConnectionException(message)

    # pylint: disable=arguments-differ
    @staticmethod
    def _query_users_by_client(client_name, client_data):
        """
        Get all users from a specific  domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        users = client_data.get_users({})
        if users:
            yield from users

    @staticmethod
    def _clients_schema():
        """
        The schema KeycloakAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Keycloak domain',
                    'type': 'string'
                },
                {
                    'name': 'username',
                    'title': 'User name',
                    'type': 'string'
                },
                {
                    'name': 'password',
                    'title': 'Password',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': 'realm_name',
                    'title': 'Realm name',
                    'type': 'string',
                    'default': 'master'
                },
                {
                    'name': 'client_id',
                    'title': 'Client ID',
                    'type': 'string',
                    'default': 'admin-cli'
                },
                {
                    'name': 'client_secret',
                    'title': 'Client secret key',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': 'verify_ssl',
                    'title': 'Verify SSL',
                    'type': 'bool'
                }
            ],
            'required': [
                'domain',
                'username',
                'password',
                'client_secret',
                'verify_ssl'
            ],
            'type': 'array'
        }

    # pylint: disable=arguments-differ
    def _parse_users_raw_data(self, users):
        for user_raw in users:
            user = self._create_user(user_raw)
            if user:
                yield user

    # pylint: disable=arguments-differ,too-many-branches,too-many-statements,too-many-locals
    def _create_user(self, user_raw):
        try:
            user = self._new_user_adapter()
            # BEFORE we check ID, make sure we don't put anyone's credentials in plaintext into logs!!!

            # Keep user credentials out of plaintext!
            user_creds = user_raw.pop('credentials', None)
            if user_creds is not None:
                user_creds = len(user_creds)
            user.count_creds = user_creds

            # Now proceed.
            user_id = user_raw.get('id')
            if user_id is None:
                logger.warning(f'Bad user with no ID: {user_raw}')
                return None

            # Axonius Generic stuff

            user_email = user_raw.get('email')
            user.id = f'{user_id}_{user_email or ""}'
            user.username = user_raw.get('username')
            user.mail = user_email
            user.first_name = user_raw.get('firstName')
            user.last_name = user_raw.get('lastName')
            groups = user_raw.get('groups')
            if isinstance(groups, list):
                user.groups = groups
            user.display_name = f'{user_raw.get("firstName", "")} {user_raw.get("lastName", "")}'

            # complex generic stuff

            acct_enabled = user_raw.get('enabled')
            if isinstance(acct_enabled, bool):
                user.account_disabled = not acct_enabled

            try:
                user.user_created = parse_date(user_raw.get('createdTimestamp'))
            except Exception as e:
                logger.warning(f'Error parsing creation timestamp for user {user_id}: {str(e)}')

            # Keycloak-specific stuff
            user.enabled = acct_enabled
            user.email_verified = user_raw.get('emailVerified')
            user.fed_link = user_raw.get('federationLink')
            user.self_str = user_raw.get('self')
            user.origin = user_raw.get('origin')
            user.svc_acct_client_id = user_raw.get('serviceAccountClientId')

            realm_roles = user_raw.get('realmRoles')
            if isinstance(realm_roles, list):
                try:
                    user.realm_roles = realm_roles
                except Exception:
                    logger.warning(f'Failed to parse realm roles for user {user_raw}')

            req_actions = user_raw.get('requiredActions')
            if isinstance(req_actions, list):
                try:
                    user.req_actions = req_actions
                except Exception:
                    logger.warning(f'Failed to parse required actions for user {user_raw}')

            dis_cred_types = user_raw.get('disableableCredentialTypes')
            if isinstance(dis_cred_types, list):
                try:
                    user.disableable_cred_types = dis_cred_types
                except Exception:
                    logger.warning(f'Failed to parse disableableCredentialTypes for user {user_raw}')

            user_access_raw = user_raw.get('access')
            if isinstance(user_access_raw, dict):
                user_access = list()
                for acc_key, acc_val in user_access_raw.items():
                    try:
                        user_access.append(KeycloakMapObj(key=acc_key, val=acc_val))
                    except Exception as e:
                        logger.warning(f'Got {str(e)} trying to parse access info for user {user_id}')
                        continue
                user.access = user_access

            user_attrs_raw = user_raw.get('attributes')
            if isinstance(user_attrs_raw, dict):
                user_attrs = list()
                for attr_key, attr_val in user_attrs_raw.items():
                    try:
                        user_attrs.append(KeycloakMapObj(key=attr_key, val=attr_val))
                    except Exception as e:
                        logger.warning(f'Got {str(e)} trying to parse attributes info for user {user_id}')
                        continue
                user.attrs = user_attrs

            consents_list = user_raw.get('clientConsents')
            if isinstance(consents_list, list):
                user_consent = list()
                for consent_dict in user_raw.get('clientConsents'):
                    try:
                        create_time = parse_date(consent_dict.get('createdDate'))
                    except Exception:
                        create_time = None
                    try:
                        update_time = parse_date(consent_dict.get('lastUpdatedDate'))
                    except Exception:
                        update_time = None
                    try:
                        granted_scopes = consent_dict.get('grantedClientScopes')
                        if not isinstance(granted_scopes, list):
                            granted_scopes = None
                    except Exception:
                        granted_scopes = None
                    try:
                        user_consent.append(UserConsentRepresentation(
                            client_id=consent_dict.get('clientId'),
                            creted=create_time,
                            updated=update_time,
                            granted_client_scopes=granted_scopes
                        ))
                    except Exception as e:
                        logger.warning(f'Got {str(e)} trying to parse consent info for user {user_id}')
                        continue
                user.consent = user_consent

            fed_dict_list = user_raw.get('federatedIdentities')
            if isinstance(fed_dict_list, list):
                user_fed_ids = list()
                for fed_dict in fed_dict_list:
                    if not isinstance(fed_dict, dict):
                        continue
                    try:
                        user_fed_ids.append(FederatedIdentity(
                            prov=fed_dict.get('identityProvider'),
                            user_id=fed_dict.get('userId'),
                            username=fed_dict.get('userName')
                        ))
                    except Exception as e:
                        logger.warning(f'Got {str(e)} trying to parse federated identity info for user {user_id}')
                user.fed_ids = user_fed_ids

            # set raw
            user.set_raw(user_raw)
            return user
        except Exception:
            logger.exception(f'Problem fetching Keycloak user for {user_raw}')
            return None

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.UserManagement]
