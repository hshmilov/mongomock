import csv
import logging
import re
import json

import copy
from codecs import BOM_UTF8
from io import StringIO
from ipaddress import ip_network

import pymongo
import requests
from flask import (jsonify, request)

from axonius.clients.aws.utils import aws_list_s3_objects
from axonius.consts.adapter_consts import LAST_FETCH_TIME, AVAILABLE_CSV_LOCATION_FIELDS
from axonius.consts.core_consts import CORE_CONFIG_NAME
from axonius.consts.gui_consts import (PROXY_ERROR_MESSAGE,
                                       GETTING_STARTED_CHECKLIST_SETTING,
                                       RootMasterNames, GUI_CONFIG_NAME, DEFAULT_ROLE_ID, ROLE_ASSIGNMENT_RULES)
from axonius.consts.metric_consts import GettingStartedMetric
from axonius.consts.plugin_consts import (AGGREGATOR_PLUGIN_NAME,
                                          GUI_PLUGIN_NAME,
                                          PLUGIN_UNIQUE_NAME, PROXY_SETTINGS,
                                          SYSTEM_SCHEDULER_PLUGIN_NAME,
                                          EXECUTION_PLUGIN_NAME, RESET_PASSWORD_LINK_EXPIRATION,
                                          RESET_PASSWORD_SETTINGS, STATIC_ANALYSIS_SETTINGS,
                                          DEVICE_LOCATION_MAPPING, CSV_IP_LOCATION_FILE, DISCOVERY_CONFIG_NAME,
                                          DISCOVERY_RESEARCH_DATE_TIME)
from axonius.email_server import EmailServer
from axonius.logging.metric_helper import log_metric
from axonius.plugin_base import return_error
from axonius.types.ssl_state import (SSLState)
from axonius.utils.backup import verify_preshared_key, get_filename_from_format
from axonius.utils.permissions_helper import PermissionCategory, PermissionAction
from axonius.utils.proxy_utils import to_proxy_string
from axonius.utils.smb import SMBClient
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

    def _get_plugin_configs(self, config_name, plugin_unique_name):
        if re.search(r'_(\d+)$', plugin_unique_name):
            plugin_name = '_'.join(plugin_unique_name.split('_')[:-1])  # turn plugin unique name to plugin name
        else:
            plugin_name = plugin_unique_name

        schema = self.plugins.get_plugin_settings(plugin_name).config_schemas[config_name]

        config = clear_passwords_fields(
            self.plugins.get_plugin_settings(plugin_name).configurable_configs[config_name],
            schema
        )

        return config, schema

    @gui_route_logged_in('<plugin_name>/<config_name>', methods=['POST'], enforce_trial=False,
                         activity_params=['config_name'])
    def update_plugin_configs(self, plugin_name, config_name):
        response = self._save_plugin_config(plugin_name, config_name)
        if response:
            return response

        config_schema = self.plugins.get_plugin_settings(plugin_name).config_schemas[config_name]
        return json.dumps({
            'config_name': config_schema.get('pretty_name', '')
        }) if config_schema else ''

    def _save_plugin_config(self, plugin_unique_name, config_name):
        """
        Set a specific config on a specific plugin
        """

        if re.search(r'_(\d+)$', plugin_unique_name):
            plugin_name = '_'.join(plugin_unique_name.split('_')[:-1])  # turn plugin unique name to plugin name
        else:
            plugin_name = plugin_unique_name

        config_to_set = request.get_json(silent=True)
        if config_to_set is None:
            return return_error('Invalid config', 400)

        config_from_db = self.plugins.get_plugin_settings(plugin_name).configurable_configs[config_name]

        if config_from_db:
            config_to_set = refill_passwords_fields(config_to_set, config_from_db)

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

            try:
                data_enrichment_settings = config_to_set.get(STATIC_ANALYSIS_SETTINGS, None)
                if data_enrichment_settings and data_enrichment_settings.get(DEVICE_LOCATION_MAPPING, None) and \
                        data_enrichment_settings.get(DEVICE_LOCATION_MAPPING).get(CSV_IP_LOCATION_FILE, None):
                    csv_file = self._grab_file_contents(
                        data_enrichment_settings.get(DEVICE_LOCATION_MAPPING).get(CSV_IP_LOCATION_FILE),
                        stored_locally=False).replace(BOM_UTF8, b'').decode('utf-8')
                    reader = csv.DictReader(self.lower_and_strip_first_line(StringIO(csv_file)))
                    if any(field not in AVAILABLE_CSV_LOCATION_FIELDS for field in reader.fieldnames):
                        return return_error('Uploaded CSV with forbidden fields', 400)
                    if any(not ip_network(row['subnet'], strict=False) for row in reader):
                        return return_error('Uploaded CSV file is not in the desired format', 400)
            except ValueError:
                return return_error('Uploaded CSV file is not in the desired format', 400)
            except Exception:
                return return_error('Error while parsing the uploaded CSV file', 400)

            aws_s3_settings = config_to_set.get('aws_s3_settings')
            if aws_s3_settings and aws_s3_settings.get('enabled') is True:
                enable_backups = aws_s3_settings.get('enable_backups')
                preshared_key = aws_s3_settings.get('preshared_key') or ''
                filename_format = aws_s3_settings.get('filename_format') or ''
                if enable_backups is True:
                    try:
                        verify_preshared_key(preshared_key)
                        get_filename_from_format(filename_format)
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

            smb_settings = config_to_set.get('smb_settings')
            if smb_settings and smb_settings.get('enabled') is True:
                enable_backups = smb_settings.get('enable_backups')
                preshared_key = smb_settings.get('preshared_key') or ''
                if enable_backups is True:
                    try:
                        verify_preshared_key(preshared_key)
                    except Exception as e:
                        return return_error(str(e), http_status=400)

                try:
                    # Note: configuration validity and connect are performed within SMBClient.__init__
                    smb_client = SMBClient(ip=smb_settings.get('ip'),
                                           smb_host=smb_settings.get('hostname'),
                                           share_name=smb_settings.get('share_path'),
                                           username=smb_settings.get('username') or '',
                                           password=smb_settings.get('password') or '',
                                           port=smb_settings.get('port'),
                                           use_nbns=smb_settings.get('use_nbns'))

                    smb_client.check_read_write_permissions_unsafe()
                except Exception as e:
                    logger.exception(f'Error connecting to SMB: {str(e)}')
                    return return_error(f'Error connecting to SMB: {str(e)}', 400)

            getting_started_conf = config_to_set.get(GETTING_STARTED_CHECKLIST_SETTING)
            getting_started_feature_enabled = getting_started_conf.get('enabled')

            password_reset_config_from_db = config_from_db.get(RESET_PASSWORD_SETTINGS)
            password_reset_config_to_set = config_to_set.get(RESET_PASSWORD_SETTINGS)

            if password_reset_config_from_db and password_reset_config_to_set \
                    and password_reset_config_from_db.get(RESET_PASSWORD_LINK_EXPIRATION) != \
                    password_reset_config_to_set.get(RESET_PASSWORD_LINK_EXPIRATION):
                self._update_user_tokens_index(password_reset_config_to_set.get(RESET_PASSWORD_LINK_EXPIRATION))

            log_metric(logger, GettingStartedMetric.FEATURE_ENABLED_SETTING,
                       metric_value=getting_started_feature_enabled)

        elif plugin_name == 'gui' and config_name == GUI_CONFIG_NAME:
            user_settings_permission = self.get_user_permissions().get(PermissionCategory.Settings)
            if not user_settings_permission.get(PermissionAction.GetUsersAndRoles) and \
                    not user_settings_permission.get(PermissionCategory.Roles, {}).get(PermissionAction.Update):
                for external_service in ['ldap_login_settings', 'saml_login_settings']:
                    role_assignment_rules = config_to_set[external_service].get(ROLE_ASSIGNMENT_RULES, {})
                    role_assignment_rules[DEFAULT_ROLE_ID] = config_from_db.\
                        get(external_service, {}).get(ROLE_ASSIGNMENT_RULES, {}).get(DEFAULT_ROLE_ID)

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
        config_name = FeatureFlags.__name__

        return jsonify({
            'config': self.plugins.gui.configurable_configs[config_name],
            'schema': self.plugins.gui.plugin_settings.config_schemas[config_name],
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
        return jsonify(self.plugins.gui.configurable_configs[FeatureFlags.__name__][RootMasterNames.root_key])

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
        config_name = FeatureFlags.__name__
        central_core_key = RootMasterNames.root_key

        config_original = self.plugins.gui.configurable_configs[config_name]

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

    def _delete_last_fetch_on_discovery_change(self, plugin_name, current_config, config_to_set):
        """
        Check adapter custom discovery time, if fetch time was changed, delete adapter last fetch time,
        for making the adapter's next custom discovery cycle happen on the same day.
        :param plugin_name: plugin_name
        :param current_config: current adapter discovery config
        :param config_to_set: new config to set
        :return: None
        """
        # If the settings we not changed, don't do anything
        if current_config and config_to_set:
            if current_config.get(DISCOVERY_RESEARCH_DATE_TIME) == config_to_set.get(DISCOVERY_RESEARCH_DATE_TIME):
                return

        # Otherwise if the settings have changed somehow (whether thery are entirely new or they replace existing
        # settings) delete the last fetch time.
        del self.plugins.get_plugin_settings(plugin_name).plugin_settings_keyval[LAST_FETCH_TIME]

    def _update_plugin_config(self, plugin_name, config_name, config_to_set):
        """
        Update given configuration settings for given configuration name, under given plugin.
        Finally, updates the plugin on the change.

        :param plugin_name: Of whom to update the configuration
        :param config_name: To update
        :param config_to_set:
        """

        if config_name == DISCOVERY_CONFIG_NAME:
            try:
                current_discovery = self.plugins.get_plugin_settings(plugin_name).configurable_configs[
                    DISCOVERY_CONFIG_NAME]
                self._delete_last_fetch_on_discovery_change(plugin_name, current_discovery, config_to_set)
            except Exception:
                logger.exception(f'Failed deleting last fetch on discovery change')

        self.plugins.get_plugin_settings(plugin_name).configurable_configs[config_name] = config_to_set

        if plugin_name == 'core':
            # Core is a special plugin because the 'status' there is always 'ok', not 'up' or 'down'.
            all_online_plugin_unique_names = ['core']
        else:
            all_online_plugin_unique_names = [
                x['plugin_unique_name'] for x in self.core_configs_collection.find(
                    {
                        'plugin_name': plugin_name,
                        'status': 'up'
                    }
                )
            ]

        def update_plugin(plugin_unique_name):
            try:
                self.request_remote_plugin('update_config', plugin_unique_name, method='post', timeout=120)
            except Exception:
                logger.exception(f'Failed to update config on {plugin_name!r}')

        res = self._update_config_executor.map_async(update_plugin, all_online_plugin_unique_names)
        try:
            res.get(3)
        except Exception:
            logger.warning(f'Warning - Save config takes more than 3 seconds, returning')

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

    @gui_route_logged_in('<plugin_name>/upload_file', methods=['POST'], skip_activity=True)
    def plugins_upload_file(self, plugin_name):
        return self._upload_file(plugin_name)
