import logging
import secrets
import shutil

from flask import (jsonify,
                   request)

from axonius.consts.gui_consts import (TEMP_MAINTENANCE_THREAD_ID, FeatureFlagsNames)
from axonius.plugin_base import EntityType, return_error
from axonius.utils.datetime import time_from_now
from axonius.utils.gui_helpers import (Permission, PermissionLevel,
                                       PermissionType, ReadOnlyJustForGet,
                                       get_connected_user_id, add_rule_unauth)
from axonius.utils.mongo_administration import (get_collection_capped_size,
                                                get_collection_stats)
from gui.logic.routing_helper import gui_add_rule_logged_in
from gui.routes.settings.plugins.plugins import Plugins
from gui.routes.settings.getting_started.getting_started import GettingStarted
from gui.routes.settings.roles.roles import Roles
from gui.routes.settings.users.users import Users
# pylint: disable=no-member,inconsistent-return-statements

logger = logging.getLogger(f'axonius.{__name__}')


class Settings(Plugins, GettingStarted, Users, Roles):

    @add_rule_unauth('system/expired')
    def get_expiry_status(self):
        """
        Whether system has currently expired it's trial or contract.
        If no trial or contract expiration date, answer will be false.
        """
        feature_flags_config = self.feature_flags_config()
        if feature_flags_config.get(FeatureFlagsNames.TrialEnd):
            return jsonify(self.trial_expired())
        if feature_flags_config.get(FeatureFlagsNames.ExpiryDate):
            return jsonify(self.contract_expired())
        return jsonify(False)

    @gui_add_rule_logged_in('api_key', methods=['GET', 'POST'])
    def api_creds(self):
        """
        Get or change the API key
        """
        if request.method == 'POST':
            new_token = secrets.token_urlsafe()
            new_api_key = secrets.token_urlsafe()
            self._users_collection.update_one(
                {
                    '_id': get_connected_user_id(),
                },
                {
                    '$set': {
                        'api_key': new_api_key,
                        'api_secret': new_token
                    }
                }
            )
        api_data = self._users_collection.find_one({
            '_id': get_connected_user_id()
        })
        return jsonify({
            'api_key': api_data['api_key'],
            'api_secret': api_data['api_secret']
        })

    def _stop_temp_maintenance(self):
        if self.trial_expired():
            logger.error('Support access not stopped - system trial has expired')
            return

        if self.contract_expired():
            logger.error('Support access not stopped - system contract has expired')
            return

        logger.info('Stopping Support Access')
        self._update_temp_maintenance(None)
        temp_maintenance_job = self._job_scheduler.get_job(TEMP_MAINTENANCE_THREAD_ID)
        if temp_maintenance_job:
            temp_maintenance_job.remove()

    def _update_temp_maintenance(self, timeout):
        self.system_collection.update_one({
            'type': 'maintenance'
        }, {
            '$set': {
                'timeout': timeout
            }
        })

    @gui_add_rule_logged_in('config/maintenance', methods=['GET', 'POST', 'PUT', 'DELETE'],
                            required_permissions={Permission(PermissionType.Settings,
                                                             ReadOnlyJustForGet)})
    def maintenance(self):
        """
        Manage the maintenance features which can be customly set by user or switched all on for a limited time.
        GET returns current config for the features
        POST updates current config for the features
        PUT start all features for given duration of time
        DELETE stop all features (should be available only if they are temporarily on)

        """
        match_maintenance = {
            'type': 'maintenance'
        }
        if request.method == 'GET':
            return jsonify(self.system_collection.find_one(match_maintenance))

        if request.method == 'POST':
            self.system_collection.update_one(match_maintenance, {
                '$set': self.get_request_data_as_object()
            })
            self._stop_temp_maintenance()

        if request.method == 'DELETE':
            self._stop_temp_maintenance()

        if request.method == 'PUT':
            temp_maintenance_job = self._job_scheduler.get_job(TEMP_MAINTENANCE_THREAD_ID)
            duration_param = self.get_request_data_as_object().get('duration', 24)
            try:
                next_run_time = time_from_now(float(duration_param))
            except ValueError:
                message = f'Value for "duration" parameter must be a number, instead got {duration_param}'
                logger.exception(message)
                return return_error(message, 400)

            logger.info('Starting Support Access')
            self._update_temp_maintenance(next_run_time)
            if temp_maintenance_job is not None:
                # Job exists, not creating another
                logger.info(f'Job already existing - updating its run time to {next_run_time}')
                temp_maintenance_job.modify(next_run_time=next_run_time)
                # self._job_scheduler.reschedule_job(SUPPORT_ACCESS_THREAD_ID, trigger='date')
            else:
                logger.info(f'Creating a job for stopping the maintenance access at {next_run_time}')
                self._job_scheduler.add_job(func=self._stop_temp_maintenance,
                                            trigger='date',
                                            next_run_time=next_run_time,
                                            name=TEMP_MAINTENANCE_THREAD_ID,
                                            id=TEMP_MAINTENANCE_THREAD_ID,
                                            max_instances=1)
            return jsonify({'timeout': next_run_time})

        return ''

    @gui_add_rule_logged_in('config/<config_name>', methods=['POST', 'GET'],
                            required_permissions={Permission(PermissionType.Settings,
                                                             ReadOnlyJustForGet)})
    def configuration(self, config_name):
        """
        Get or set config by name
        :param config_name: Config to fetch
        :return:
        """
        configs_collection = self._get_collection('config')
        if request.method == 'GET':
            return jsonify(
                configs_collection.find_one({'name': config_name},
                                            )['value'])
        if request.method == 'POST':
            config_to_add = request.get_json(silent=True)
            if config_to_add is None:
                return return_error('Invalid filter', 400)
            configs_collection.update({'name': config_name},
                                      {'name': config_name, 'value': config_to_add},
                                      upsert=True)
            return ''

    @gui_add_rule_logged_in('configuration', methods=['GET'])
    def system_config(self):
        """
        Get only the GUIs settings as well as whether Mail Server and Syslog Server are enabled.
        This is needed for the case that user is restricted from the settings but can view pages that use them.
        The pages should render the same, so these settings must be permitted to read anyway.

        :return: Settings for the system and Global settings, indicating if Mail and Syslog are enabled
        """
        return jsonify({
            'system': self._system_settings,
            'global': {
                'mail': self._email_settings['enabled'] if self._email_settings else False,
                'syslog': self._syslog_settings['enabled'] if self._syslog_settings else False,
                'httpsLog': self._https_logs_settings['enabled'] if self._https_logs_settings else False,
                'jira': self._jira_settings['enabled'] if self._jira_settings else False,
                'gettingStartedEnabled': self._getting_started_settings['enabled'],
                'cyberark_vault': self._vault_settings['enabled'],
                'customerId': self.node_id
            }
        })

    @gui_add_rule_logged_in('historical_sizes', methods=['GET'],
                            required_permissions={Permission(PermissionType.Settings,
                                                             PermissionLevel.ReadOnly)})
    def get_historical_size_stats(self):
        return self._get_historical_size_stats()

    def _get_historical_size_stats(self):
        sizes = {}
        for entity_type in EntityType:
            try:
                col = self._historical_entity_views_db_map[entity_type]

                # find the date of the last historical point
                last_date = col.find_one(projection={'accurate_for_datetime': 1},
                                         sort=[('accurate_for_datetime', -1)])['accurate_for_datetime']

                axonius_entities_in_last_historical_point = col.count_documents({
                    'accurate_for_datetime': last_date
                })

                stats = get_collection_stats(col)

                d = {
                    'size': stats['storageSize'],
                    'capped': get_collection_capped_size(col),
                    'avg_document_size': stats['avgObjSize'],
                    'entities_last_point': axonius_entities_in_last_historical_point
                }
                sizes[entity_type.name] = d
            except Exception:
                logger.exception(f'failed calculating stats for {entity_type}')

        disk_usage = shutil.disk_usage('/')
        return jsonify({
            'disk_free': disk_usage.free,
            'disk_used': disk_usage.used,
            'entity_sizes': sizes
        })

    @gui_add_rule_logged_in('metadata', methods=['GET'], required_permissions={
        Permission(PermissionType.Settings, PermissionLevel.ReadOnly)})
    def get_metadata(self):
        """
        Gets the system metadata.
        :return:
        """
        return jsonify(self.metadata)
