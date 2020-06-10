import csv
import logging
import urllib.parse
import json

import copy
from io import StringIO
from ipaddress import ip_network

import OpenSSL
import pymongo
import requests
from flask import (jsonify, request)

from axonius.clients.aws.utils import aws_list_s3_objects
from axonius.consts.adapter_consts import ADAPTER_SETTINGS
from axonius.consts.core_consts import CORE_CONFIG_NAME
from axonius.consts.gui_consts import (PROXY_ERROR_MESSAGE,
                                       GETTING_STARTED_CHECKLIST_SETTING,
                                       CONFIG_CONFIG, RootMasterNames)
from axonius.consts.metric_consts import GettingStartedMetric
from axonius.consts.plugin_consts import (AGGREGATOR_PLUGIN_NAME,
                                          CONFIGURABLE_CONFIGS_COLLECTION,
                                          GUI_PLUGIN_NAME,
                                          PLUGIN_UNIQUE_NAME, PROXY_SETTINGS,
                                          SYSTEM_SCHEDULER_PLUGIN_NAME,
                                          EXECUTION_PLUGIN_NAME, RESET_PASSWORD_LINK_EXPIRATION,
                                          RESET_PASSWORD_SETTINGS, DEFAULT_ROLE_ID, STATIC_ANALYSIS_SETTINGS,
                                          DEVICE_LOCATION_MAPPING, CSV_IP_LOCATION_FILE, DISCOVERY_CONFIG_NAME,
                                          DISCOVERY_RESEARCH_DATE_TIME)
from axonius.email_server import EmailServer
from axonius.logging.metric_helper import log_metric
from axonius.plugin_base import return_error
from axonius.types.ssl_state import (SSLState)
from axonius.utils.backup import verify_preshared_key
from axonius.utils.permissions_helper import PermissionCategory, PermissionAction
from axonius.utils.proxy_utils import to_proxy_string
from axonius.utils.ssl import check_associate_cert_with_private_key, validate_cert_with_ca
from gui.feature_flags import FeatureFlags
from gui.logic.login_helper import clear_passwords_fields, refill_passwords_fields
from gui.logic.routing_helper import gui_section_add_rules, gui_route_logged_in

# pylint: disable=too-many-statements,too-many-return-statements,fixme,no-member,too-many-locals,too-many-branches

logger = logging.getLogger(f'axonius.{__name__}')


@gui_section_add_rules('plugins')
class Plugins:
    @gui_route_logged_in()
    def plugins(self):
        """
        Get all plugins configured in core and update each one's status.
        Status will be "error" if the plugin is not registered.
        Otherwise it will be "success", if currently running or "warning", if  stopped.

        :mongo_filter
        :return: List of plugins with
        """
        plugins_available = self.get_available_plugins_from_core()
        db_connection = self._get_db_connection()
        plugins_from_db = db_connection['core']['configs'].find({'plugin_type': 'Plugin'}).sort(
            [(PLUGIN_UNIQUE_NAME, pymongo.ASCENDING)])
        plugins_to_return = []
        for plugin in plugins_from_db:
            # TODO check supported features
            if plugin['plugin_type'] != 'Plugin' or plugin['plugin_name'] in [AGGREGATOR_PLUGIN_NAME,
                                                                              GUI_PLUGIN_NAME,
                                                                              'watch_service',
                                                                              EXECUTION_PLUGIN_NAME,
                                                                              SYSTEM_SCHEDULER_PLUGIN_NAME]:
                continue

            processed_plugin = {'plugin_name': plugin['plugin_name'],
                                'unique_plugin_name': plugin[PLUGIN_UNIQUE_NAME],
                                'status': 'error',
                                'state': 'Disabled'
                                }
            if plugin[PLUGIN_UNIQUE_NAME] in plugins_available:
                processed_plugin['status'] = 'warning'
                response = self.request_remote_plugin(
                    'trigger_state/execute', plugin[PLUGIN_UNIQUE_NAME])
                if response.status_code != 200:
                    logger.error(f'Error getting state of plugin {plugin[PLUGIN_UNIQUE_NAME]}')
                    processed_plugin['status'] = 'error'
                else:
                    processed_plugin['state'] = response.json()
                    # pylint: disable=invalid-sequence-index
                    if processed_plugin['state']['state'] != 'Disabled':
                        # pylint: enable=invalid-sequence-index
                        processed_plugin['status'] = 'success'
            plugins_to_return.append(processed_plugin)

        return jsonify(plugins_to_return)

    @gui_route_logged_in('<plugin_name>/<config_name>', methods=['GET'], enforce_trial=False)
    def get_plugin_configs(self, plugin_name, config_name):
        """
        Get a specific config on a specific plugin
        """
        config, schema = self._get_plugin_configs(config_name, plugin_name)

        return jsonify({
            'config': config,
            'schema': schema
        })

    def _get_plugin_configs(self, config_name, plugin_name):
        db_connection = self._get_db_connection()
        config_collection = db_connection[plugin_name][CONFIGURABLE_CONFIGS_COLLECTION]
        schema_collection = db_connection[plugin_name]['config_schemas']
        schema = schema_collection.find_one({'config_name': config_name})['schema']
        config = clear_passwords_fields(config_collection.find_one({'config_name': config_name})['config'],
                                        schema)
        return config, schema

    @gui_route_logged_in('<plugin_name>/<config_name>', methods=['POST'], enforce_trial=False,
                         activity_params=['config_name'])
    def update_plugin_configs(self, plugin_name, config_name):
        response = self._save_plugin_config(plugin_name, config_name)
        if response:
            return response
        config_schema = self._get_collection('config_schemas', plugin_name).find_one({
            'config_name': config_name
        }, {
            'schema.pretty_name': 1
        })
        return json.dumps({
            'config_name': config_schema['schema'].get('pretty_name', '')
        }) if config_schema else ''

    def _save_plugin_config(self, plugin_name, config_name):
        """
        Set a specific config on a specific plugin
        """
        db_connection = self._get_db_connection()
        config_collection = db_connection[plugin_name][CONFIGURABLE_CONFIGS_COLLECTION]
        config_to_set = request.get_json(silent=True)
        if config_to_set is None:
            return return_error('Invalid config', 400)

        config_from_db = config_collection.find_one({
            'config_name': config_name
        })

        if config_from_db:
            config_to_set = refill_passwords_fields(config_to_set, config_from_db['config'])

        if plugin_name == 'core' and config_name == CORE_CONFIG_NAME:
            email_settings = config_to_set.get('email_settings')
            if email_settings and email_settings.get('enabled') is True:
                if not email_settings.get('smtpHost') or not email_settings.get('smtpPort'):
                    return return_error('Host and Port are required to connect to email server', 400)

                email_server = EmailServer(email_settings['smtpHost'], email_settings['smtpPort'],
                                           email_settings.get('smtpUser'), email_settings.get('smtpPassword'),
                                           ssl_state=SSLState[email_settings.get(
                                               'use_ssl', SSLState.Unencrypted.name)],
                                           keyfile_data=self._grab_file_contents(email_settings.get('private_key'),
                                                                                 stored_locally=False),
                                           certfile_data=self._grab_file_contents(email_settings.get('cert_file'),
                                                                                  stored_locally=False),
                                           ca_file_data=self._grab_file_contents(email_settings.get('ca_file'),
                                                                                 stored_locally=False))
                try:
                    with email_server:
                        # Just to test connection
                        logger.info(f'Connection to email server with host {email_settings["smtpHost"]}')
                except Exception:
                    message = f'Could not connect to mail server "{email_settings["smtpHost"]}"'
                    logger.exception(message)
                    return return_error(message, 400)

            proxy_settings = config_to_set.get(PROXY_SETTINGS)
            if not self.is_proxy_allows_web(proxy_settings):
                return return_error(PROXY_ERROR_MESSAGE, 400)

            global_ssl = config_to_set.get('global_ssl')
            if global_ssl and global_ssl.get('enabled') is True:
                config_cert = self._grab_file_contents(global_ssl.get('cert_file'), stored_locally=False)
                config_private = self._grab_file_contents(global_ssl.get('private_key'), stored_locally=False)
                try:
                    parsed_cert = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, config_cert)
                except Exception:
                    logger.exception(f'Error loading certificate')
                    return return_error(
                        f'Error loading certificate file. Please upload a pem-type certificate file.', 400)
                cn = dict(parsed_cert.get_subject().get_components())[b'CN'].decode('utf8')
                if cn != global_ssl['hostname']:
                    return return_error(f'Hostname does not match the hostname in the certificate file, '
                                        f'hostname in given cert is {cn}', 400)

                ssl_check_result = False
                try:
                    ssl_check_result = check_associate_cert_with_private_key(
                        config_cert, config_private, global_ssl.get('passphrase')
                    )
                except Exception as e:
                    return return_error(f'Error - can not load ssl settings: {str(e)}', 400)

                if not ssl_check_result:
                    return return_error(f'Private key and public certificate do not match each other', 400)

            try:
                data_enrichment_settings = config_to_set.get(STATIC_ANALYSIS_SETTINGS, None)
                if data_enrichment_settings and data_enrichment_settings.get(DEVICE_LOCATION_MAPPING, None) and \
                        data_enrichment_settings.get(DEVICE_LOCATION_MAPPING).get(CSV_IP_LOCATION_FILE, None):
                    csv_file = self._grab_file_contents(
                        data_enrichment_settings.get(DEVICE_LOCATION_MAPPING).get(CSV_IP_LOCATION_FILE),
                        stored_locally=False).decode('utf-8')
                    reader = csv.DictReader(self.lower_and_strip_first_line(StringIO(csv_file)))
                    if any(not row['location'] or not ip_network(row['subnet'], strict=False) for row in reader):
                        return return_error('Uploaded CSV file is not in the desired format', 400)
            except ValueError:
                return return_error('Uploaded CSV file is not in the desired format', 400)
            except KeyError:
                return return_error('Uploaded CSV file does not have the required headers', 400)
            except Exception:
                return return_error('Error while parsing the uploaded CSV file', 400)

            aws_s3_settings = config_to_set.get('aws_s3_settings')
            if aws_s3_settings and aws_s3_settings.get('enabled') is True:
                enable_backups = aws_s3_settings.get('enable_backups')
                preshared_key = aws_s3_settings.get('preshared_key') or ''
                if enable_backups is True:
                    try:
                        verify_preshared_key(preshared_key)
                    except Exception as e:
                        return return_error(str(e), non_prod_error=True, http_status=400)
                bucket_name = aws_s3_settings.get('bucket_name')
                aws_access_key_id = aws_s3_settings.get('aws_access_key_id')
                aws_secret_access_key = aws_s3_settings.get('aws_secret_access_key')
                if (aws_access_key_id and not aws_secret_access_key) \
                        or (aws_secret_access_key and not aws_access_key_id):
                    return return_error(f'Error: Please specify both AWS Access Key ID and AWS Secret Access Key', 400)
                try:
                    for _ in aws_list_s3_objects(
                            bucket_name=bucket_name,
                            access_key_id=aws_access_key_id,
                            secret_access_key=aws_secret_access_key,
                            just_one=True
                    ):
                        break
                except Exception as e:
                    logger.exception(f'Error listing AWS s3 objects')
                    return return_error(f'Error listing AWS S3 Objects: {str(e)}', 400)
            getting_started_conf = config_to_set.get(GETTING_STARTED_CHECKLIST_SETTING)
            getting_started_feature_enabled = getting_started_conf.get('enabled')

            password_reset_config_from_db = config_from_db['config'].get(RESET_PASSWORD_SETTINGS)
            password_reset_config_to_set = config_to_set.get(RESET_PASSWORD_SETTINGS)

            if password_reset_config_from_db and password_reset_config_to_set \
                    and password_reset_config_from_db.get(RESET_PASSWORD_LINK_EXPIRATION) != \
                    password_reset_config_to_set.get(RESET_PASSWORD_LINK_EXPIRATION):
                self._update_user_tokens_index(password_reset_config_to_set.get(RESET_PASSWORD_LINK_EXPIRATION))

            log_metric(logger, GettingStartedMetric.FEATURE_ENABLED_SETTING,
                       metric_value=getting_started_feature_enabled)

        elif plugin_name == 'gui' and config_name == CONFIG_CONFIG:
            user_settings_permission = self.get_user_permissions().get(PermissionCategory.Settings)
            if not user_settings_permission.get(PermissionAction.GetUsersAndRoles) and \
                    not user_settings_permission.get(PermissionCategory.Roles, {}).get(PermissionAction.Update):
                for external_service in ['ldap_login_settings', 'okta_login_settings', 'saml_login_settings']:
                    config_to_set[external_service][DEFAULT_ROLE_ID] = config_from_db['config']. \
                        get(external_service, {}).get(DEFAULT_ROLE_ID)

            mutual_tls_settings = config_to_set.get('mutual_tls_settings')
            if mutual_tls_settings.get('enabled'):
                is_mandatory = mutual_tls_settings.get('mandatory')
                client_ssl_cert = request.environ.get('HTTP_X_CLIENT_ESCAPED_CERT')

                if is_mandatory and not client_ssl_cert:
                    logger.error(f'Client certificate not found in request.')
                    return return_error(f'Client certificate not found in request. Please make sure your client '
                                        f'uses a certificate to access Axonius', 400)

                try:
                    ca_certificate = self._grab_file_contents(mutual_tls_settings.get('ca_certificate'))
                except Exception:
                    logger.exception(f'Error getting ca certificate from db')
                    return return_error(f'can not find uploaded certificate', 400)

                try:
                    OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, ca_certificate)
                except Exception:
                    logger.error(f'Can not load ca certificate', exc_info=True)
                    return return_error(f'The uploaded file is not a pem-format certificate', 400)
                try:
                    if is_mandatory and \
                            not validate_cert_with_ca(urllib.parse.unquote(client_ssl_cert), ca_certificate):
                        logger.error(f'Current client certificate is not trusted by the uploaded CA')
                        return return_error(f'Current client certificate is not trusted by the uploaded CA', 400)
                except Exception:
                    logger.error(f'Can not validate current client certificate with the uploaded CA', exc_info=True)
                    return return_error(f'Current client certificate can not be validated by the uploaded CA', 400)

        self._update_plugin_config(plugin_name, config_name, config_to_set)
        return ''

    @staticmethod
    def is_proxy_allows_web(config):
        if config['enabled'] is False:
            return True

        proxies = None
        try:
            logger.info(f'checking the following proxy config {config}')
            proxy_string = to_proxy_string(config)
            if proxy_string:
                proxy_string = to_proxy_string(config)
                proxies = {'https': f'https://{proxy_string}'}

            test_request = requests.get('https://manage.chef.io', proxies=proxies, timeout=7)
            retcode = test_request.status_code
            if retcode == 200:
                logger.info('Proxy test passed')
                return True
            logger.error(f'proxy test failed with code {retcode}')
            return False
        except Exception:
            logger.exception(f'proxy test failed')
            return False

    @gui_route_logged_in('gui/FeatureFlags', methods=['GET'], enforce_trial=False, enforce_permissions=False)
    def get_feature_flags(self):
        plugin_name = GUI_PLUGIN_NAME
        config_name = FeatureFlags.__name__
        db_connection = self._get_db_connection()
        config_collection = db_connection[plugin_name][CONFIGURABLE_CONFIGS_COLLECTION]
        schema_collection = db_connection[plugin_name]['config_schemas']
        return jsonify({
            'config': config_collection.find_one({'config_name': config_name})['config'],
            'schema': schema_collection.find_one({'config_name': config_name})['schema']
        })

    @gui_route_logged_in('gui/FeatureFlags', methods=['POST'], enforce_trial=False)
    def update_feature_flags(self):
        plugin_name = GUI_PLUGIN_NAME
        config_name = FeatureFlags.__name__

        if not self.is_axonius_user():
            logger.error(f'Request to modify {FeatureFlags.__name__} from a regular user!')
            return return_error('Illegal Operation', 400)  # keep gui happy, but don't show/change the flags

        config_to_set = request.get_json(silent=True)
        if config_to_set is None:
            return return_error('Invalid config', 400)

        self._update_plugin_config(plugin_name, config_name, config_to_set)
        self._invalidate_sessions()
        return ''

    def _get_central_core_settings(self):
        """Get the current central core (root master) configuration settings."""
        plugin_name = GUI_PLUGIN_NAME
        collection_name = CONFIGURABLE_CONFIGS_COLLECTION
        config_name = FeatureFlags.__name__
        central_core_key = RootMasterNames.root_key
        config_to_find = {'config_name': config_name}

        db_connection = self._get_db_connection()
        config_collection = db_connection[plugin_name][collection_name]
        config_doc = config_collection.find_one(config_to_find)
        config = config_doc['config']
        config_to_return = config[central_core_key]

        return jsonify(config_to_return)

    def _update_central_core_settings(self):
        """Set the central core (root master) configuration settings."""
        request_config = request.get_json(silent=True) or {}

        required = ['delete_backups', 'enabled']
        if not request_config or not all([x in request_config for x in required]):
            err = f'Must supply object with keys: {required}'
            return return_error(error_message=err, http_status=400, additional_data=None)

        delete_backups = request_config['delete_backups']
        enabled = request_config['enabled']

        plugin_name = GUI_PLUGIN_NAME
        collection_name = CONFIGURABLE_CONFIGS_COLLECTION
        config_name = FeatureFlags.__name__
        central_core_key = RootMasterNames.root_key
        config_to_find = {'config_name': config_name}

        db_connection = self._get_db_connection()
        config_collection = db_connection[plugin_name][collection_name]
        config_doc = config_collection.find_one(config_to_find)
        config_original = config_doc['config']

        config_to_set = {}
        config_to_set.update(copy.deepcopy(config_original))

        if delete_backups in [True, False]:
            config_to_set[central_core_key]['delete_backups'] = delete_backups

        if enabled in [True, False]:
            config_to_set[central_core_key]['enabled'] = enabled

        if config_to_set == config_original:
            err = f'No changes supplied!'
            return return_error(error_message=err, http_status=400, additional_data=None)

        self._update_plugin_config(plugin_name=plugin_name, config_name=config_name, config_to_set=config_to_set)
        return self._get_central_core_settings()

    def _delete_last_fetch_on_discovery_change(self, plugin_unique_name, current_config, config_to_set):
        """
        Check adapter custom discovery time, if fetch time was changed, delete adapter last fetch time,
        for making the adapter's next custom discovery cycle happen on the same day.
        :param plugin_unique_name: plugin unique name
        :param current_config: current adapter discovery config
        :param config_to_set: new config to set
        :return: None
        """
        if not config_to_set or not current_config:
            return
        try:
            db_connection = self._get_db_connection()
            if current_config.get(DISCOVERY_RESEARCH_DATE_TIME) == config_to_set.get(DISCOVERY_RESEARCH_DATE_TIME):
                return
            adapter_settings = db_connection[plugin_unique_name][ADAPTER_SETTINGS]
            adapter_settings.delete_one({
                'last_fetch_time': {
                    '$exists': True
                }
            })
        except Exception:
            logger.error(f'Error deleting adapter last fetch time: {plugin_unique_name}', exc_info=True)

    def _update_plugin_config(self, plugin_name, config_name, config_to_set):
        """
        Update given configuration settings for given configuration name, under given plugin.
        Finally, updates the plugin on the change.

        :param plugin_name: Of whom to update the configuration
        :param config_name: To update
        :param config_to_set:
        """
        db_connection = self._get_db_connection()
        if self.request_remote_plugin('register', params={'unique_name': plugin_name}).status_code != 200:
            unique_plugins_names = self.request_remote_plugin(
                f'find_plugin_unique_name/nodes/None/plugins/{plugin_name}').json()
        else:
            unique_plugins_names = [plugin_name]
        for current_unique_plugin in unique_plugins_names:
            config_collection = db_connection[current_unique_plugin][CONFIGURABLE_CONFIGS_COLLECTION]
            try:
                if config_name == DISCOVERY_CONFIG_NAME:
                    current_config = config_collection.find_one({
                        'config_name': DISCOVERY_CONFIG_NAME
                    })
                    if current_config:
                        self._delete_last_fetch_on_discovery_change(current_unique_plugin, current_config.get('config'),
                                                                    config_to_set)
            except Exception:
                logger.error('Error checking discovery settings', exc_info=True)
            config_collection.replace_one(filter={'config_name': config_name}, replacement={
                'config_name': config_name, 'config': config_to_set})
            self.request_remote_plugin('update_config', current_unique_plugin, method='POST')

    @gui_route_logged_in('<plugin_unique_name>/<command>', methods=['POST'])
    def run_plugin(self, plugin_unique_name, command):
        """
        Calls endpoint of given plugin_unique_name, according to given command
        The command should comply with the /supported_features of the plugin

        :param plugin_unique_name:
        :return:
        """
        request_data = self.get_request_data_as_object()
        response = self.request_remote_plugin(f'{command}/{request_data["trigger"]}', plugin_unique_name, method='post')
        if response and response.status_code == 200:
            return ''
        return response.json(), response.status_code

    @gui_route_logged_in('<plugin_name>/upload_file', methods=['POST'])
    def plugins_upload_file(self, plugin_name):
        return self._upload_file(plugin_name)
