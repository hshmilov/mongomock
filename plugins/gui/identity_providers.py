import logging

import requests
# pylint: disable=import-error
from onelogin.saml2.idp_metadata_parser import OneLogin_Saml2_IdPMetadataParser

from axonius.clients.ldap.ldap_group_cache import set_ldap_groups_cache, get_ldap_groups_cache_ttl
from axonius.consts.gui_consts import IDENTITY_PROVIDERS_CONFIG, EMAIL_ADDRESS, EMAIL_DOMAIN, LDAP_GROUP, \
    NO_ACCESS_ROLE, ROLE_ASSIGNMENT_RULES, DEFAULT_ROLE_ID, EVALUATE_ROLE_ASSIGNMENT_ON_SCHEMA, \
    ASSIGNMENT_RULE, DEFAULT_ASSIGNMENT_RULE_SCHEMA, ASSIGNMENT_RULE_VALUE, \
    ASSIGNMENT_RULE_ROLE_ID, ASSIGNMENT_RULE_KEY, ASSIGNMENT_RULE_TYPE, ASSIGNMENT_RULE_ARRAY, ROLES_SOURCE, \
    NEW_USERS_ONLY, EVALUATE_ROLE_ASSIGNMENT_ON
from axonius.consts.plugin_consts import GUI_PLUGIN_NAME
from axonius.mixins.configurable import Configurable
from axonius.plugin_base import PluginBase
from axonius.types.ssl_state import COMMON_SSL_CONFIG_SCHEMA, COMMON_SSL_CONFIG_SCHEMA_DEFAULTS

logger = logging.getLogger(f'axonius.{__name__}')

# pylint: disable=R0201,E0203,useless-super-delegation,no-member,import-error,protected-access


class IdentityProviders(Configurable):
    def __init__(self, *args, **kwargs):
        self._saml_login = None
        self._ldap_login = None
        super().__init__(*args, **kwargs)

    def identity_providers_config(self) -> dict:
        return self.plugins.gui.configurable_configs[IDENTITY_PROVIDERS_CONFIG]

    @classmethod
    def get_default_external_role_id(cls, roles_collection):
        no_access_role = roles_collection.find_one({
            'name': NO_ACCESS_ROLE
        }, projection={'_id': 1})
        return str(no_access_role.get('_id')) if no_access_role else None

    def _on_config_update(self, config):
        if config['saml_login_settings'] == self._saml_login\
                and config['ldap_login_settings'] == self._ldap_login:
            return

        saml_login = config['saml_login_settings']
        ldap_login = config['ldap_login_settings']

        metadata_url = saml_login.get('metadata_url')
        if metadata_url:
            try:
                logger.info(f'Requesting metadata url for SAML Auth')
                requests.get(metadata_url, timeout=10)  # If the metadataurl is not accessible, fail before
                saml_login['idp_data_from_metadata'] = \
                    OneLogin_Saml2_IdPMetadataParser.parse_remote(metadata_url)
            except Exception:
                logger.exception(f'SAML Configuration change: Metadata parsing error')
                self.create_notification(
                    'SAML config change failed',
                    content='The metadata URL provided is invalid.',
                    severity_type='error'
                )

        try:
            new_ttl = ldap_login.get('cache_time_in_hours')
            new_ttl = new_ttl if new_ttl is not None else 1

            if (get_ldap_groups_cache_ttl() / 3600) != new_ttl:
                logger.info(f'Setting a new cache with ttl of {new_ttl} hours')
                set_ldap_groups_cache(new_ttl * 3600)
        except Exception:
            logger.exception(f'Failed - could not add LDAP groups cached')

        logger.info(f'Loading IdentityProviders config: {config}')
        current_id_providers_config = self.identity_providers_config()
        self._saml_login = current_id_providers_config['saml_login_settings']
        if saml_login.get('idp_data_from_metadata'):
            self._saml_login['idp_data_from_metadata'] = saml_login['idp_data_from_metadata']
        self._ldap_login = current_id_providers_config['ldap_login_settings']

    @classmethod
    def _db_config_schema(cls) -> dict:
        return {
            'items': [
                {
                    'items': [
                        {
                            'name': 'enabled',
                            'title': 'Allow LDAP logins',
                            'type': 'bool'
                        },
                        {
                            'name': 'dc_address',
                            'title': 'The host domain controller IP or DNS',
                            'type': 'string'
                        },
                        {
                            'name': 'group_cn',
                            'title': 'Group the user must be part of',
                            'type': 'string'
                        },
                        {
                            'name': 'use_group_dn',
                            'title': 'Match group name by DN',
                            'type': 'bool'
                        },
                        {
                            'name': 'default_domain',
                            'title': 'Default domain to present to the user',
                            'type': 'string'
                        },
                        {
                            'name': 'cache_time_in_hours',
                            'title': 'LDAP group hierarchy cache refresh rate (hours)',
                            'type': 'integer'
                        },
                        *COMMON_SSL_CONFIG_SCHEMA,
                        {
                            'name': ROLE_ASSIGNMENT_RULES,
                            'title': 'Role Assignment Settings',
                            'type': 'array',
                            'items': [
                                EVALUATE_ROLE_ASSIGNMENT_ON_SCHEMA,
                                {
                                    'name': DEFAULT_ROLE_ID,
                                    'title': 'Default role for new LDAP user (if no matching assignment rule found)',
                                    'type': 'string',
                                    'enum': [],
                                    'source': ROLES_SOURCE,
                                },
                                {
                                    'name': ASSIGNMENT_RULE_ARRAY,
                                    'title':
                                        'Role Assignment Rules (users will be assigned to the first matching role)',
                                    'type': 'array',
                                    'ordered': True,
                                    'collapsible': True,
                                    'items':
                                        {
                                            'name': ASSIGNMENT_RULE,
                                            'type': 'array',
                                            'items': [
                                                {
                                                    'name': 'type',
                                                    'title': 'Rule type',
                                                    'placeholder': 'Rule type',
                                                    'type': 'string',
                                                    'enum': [EMAIL_ADDRESS, EMAIL_DOMAIN, LDAP_GROUP],
                                                },
                                                *DEFAULT_ASSIGNMENT_RULE_SCHEMA,
                                            ],
                                            'required': [
                                                ASSIGNMENT_RULE_TYPE,
                                                ASSIGNMENT_RULE_VALUE,
                                                ASSIGNMENT_RULE_ROLE_ID
                                            ],
                                        },
                                }
                            ],
                            'required': [EVALUATE_ROLE_ASSIGNMENT_ON, DEFAULT_ROLE_ID]
                        },

                    ],
                    'required': ['enabled', 'dc_address', 'use_group_dn', 'cache_time_in_hours'],
                    'name': 'ldap_login_settings',
                    'title': 'LDAP Login Settings',
                    'type': 'array'
                },
                {
                    'items': [
                        {
                            'name': 'enabled',
                            'title': 'Allow SAML-based logins',
                            'type': 'bool'
                        },
                        {
                            'name': 'idp_name',
                            'title': 'Name of the identity provider',
                            'type': 'string'
                        },
                        {
                            'name': 'metadata_url',
                            'title': 'Metadata URL',
                            'type': 'string'
                        },
                        {
                            'name': 'axonius_external_url',
                            'title': 'Axonius external URL',
                            'type': 'string'
                        },
                        {
                            'name': 'sso_url',
                            'title': 'Single sign-on service URL',
                            'type': 'string'
                        },
                        {
                            'name': 'entity_id',
                            'title': 'Entity ID',
                            'type': 'string'
                        },
                        {
                            'name': 'certificate',
                            'title': 'Signing certificate (Base64 encoded)',
                            'type': 'file'
                        },
                        {
                            'name': 'configure_authncc',
                            'type': 'array',
                            'items': [
                                {
                                    'name': 'dont_send_authncc',
                                    'title': 'Do not send AuthnContextClassRef',
                                    'type': 'bool',
                                    'default': False,
                                },
                            ],
                            'required': ['dont_send_authncc'],
                        },
                        {
                            'name': ROLE_ASSIGNMENT_RULES,
                            'title': 'Role Assignment Settings',
                            'type': 'array',
                            'items': [
                                EVALUATE_ROLE_ASSIGNMENT_ON_SCHEMA,
                                {
                                    'name': DEFAULT_ROLE_ID,
                                    'title': 'Default role for new SAML user (if no matching assignment rule found)',
                                    'type': 'string',
                                    'enum': [],
                                    'source': ROLES_SOURCE,
                                },
                                {
                                    'name': ASSIGNMENT_RULE_ARRAY,
                                    'title':
                                        'Role Assignment Rules (users will be assigned to the first matching role)',
                                    'type': 'array',
                                    'ordered': True,
                                    'collapsible': True,
                                    'items':
                                        {
                                            'name': ASSIGNMENT_RULE,
                                            'type': 'array',
                                            'items': [
                                                {
                                                    'placeholder': 'Key',
                                                    'name': 'key',
                                                    'title': 'Key',
                                                    'type': 'string',
                                                    'errorMsg': 'Role assignment rule - missing key'

                                                },
                                                *DEFAULT_ASSIGNMENT_RULE_SCHEMA,
                                            ],
                                            'required': [
                                                ASSIGNMENT_RULE_KEY,
                                                ASSIGNMENT_RULE_VALUE,
                                                ASSIGNMENT_RULE_ROLE_ID
                                            ],
                                        },
                                }
                            ],
                            'required': [EVALUATE_ROLE_ASSIGNMENT_ON, DEFAULT_ROLE_ID]
                        },
                    ],
                    'required': ['enabled', 'idp_name'],
                    'name': 'saml_login_settings',
                    'title': 'SAML-Based Login Settings',
                    'type': 'array'
                },
            ],
            'type': 'array',
            'name': 'identity_providers',
            'pretty_name': 'Identity Providers Settings'
        }

    @classmethod
    def _db_config_default(cls):
        roles_collection = PluginBase.Instance._get_collection('roles', GUI_PLUGIN_NAME)
        no_access_role_id = cls.get_default_external_role_id(roles_collection)
        return {
            'ldap_login_settings': {
                'enabled': False,
                'dc_address': '',
                'default_domain': '',
                'group_cn': '',
                'use_group_dn': False,
                'cache_time_in_hours': 720,
                **COMMON_SSL_CONFIG_SCHEMA_DEFAULTS,
                ROLE_ASSIGNMENT_RULES: {
                    EVALUATE_ROLE_ASSIGNMENT_ON: NEW_USERS_ONLY,
                    DEFAULT_ROLE_ID: no_access_role_id,
                    ASSIGNMENT_RULE_ARRAY: [],
                }
            },
            'saml_login_settings': {
                'enabled': False,
                'idp_name': None,
                'metadata_url': None,
                'axonius_external_url': None,
                'sso_url': None,
                'entity_id': None,
                'certificate': None,
                'configure_authncc': {
                    'dont_send_authncc': False,
                },
                ROLE_ASSIGNMENT_RULES: {
                    EVALUATE_ROLE_ASSIGNMENT_ON: NEW_USERS_ONLY,
                    DEFAULT_ROLE_ID: no_access_role_id,
                    'rules': [],
                }
            },
        }
