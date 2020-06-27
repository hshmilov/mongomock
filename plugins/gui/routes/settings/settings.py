import logging
import shutil
import secrets

from flask import (jsonify,
                   request)

from axonius.consts.gui_consts import (TEMP_MAINTENANCE_THREAD_ID)
from axonius.consts.plugin_consts import (SYSTEM_SCHEDULER_PLUGIN_NAME)
from axonius.consts.scheduler_consts import SCHEDULER_CONFIG_NAME, SCHEDULER_SAVE_HISTORY_CONFIG_NAME
from axonius.plugin_base import EntityType, return_error
from axonius.utils.datetime import time_from_now
from axonius.utils.gui_helpers import get_connected_user_id
from axonius.utils.mongo_administration import (get_collection_capped_size,
                                                get_collection_stats)
from axonius.utils.permissions_helper import PermissionCategory, PermissionAction, PermissionValue
from gui.logic.routing_helper import gui_category_add_rules, gui_route_logged_in
from gui.routes.settings.audit.audit import Audit
from gui.routes.settings.getting_started.getting_started import GettingStarted
from gui.routes.settings.plugins.plugins import Plugins
from gui.routes.settings.roles.roles import Roles
from gui.routes.settings.users.bulk.users_bulk import UserBulk
from gui.routes.settings.users.tokens.user_token import UserToken
from gui.routes.settings.users.users import Users
from gui.routes.settings.offline.configuration import Configuration

# pylint: disable=no-member,inconsistent-return-statements

logger = logging.getLogger(f'axonius.{__name__}')


@gui_category_add_rules('settings')
class Settings(Audit, Plugins, GettingStarted, Users, Roles, Configuration, UserToken, UserBulk):

    @gui_route_logged_in(methods=['GET'], enforce_permissions=False)
    def system_config(self):
        """
        Get only the GUIs settings as well as whether Mail Server and Syslog Server are enabled.
        This is needed for the case that user is restricted from the settings but can view pages that use them.
        The pages should render the same, so these settings must be permitted to read anyway.

        :return: Settings for the system and Global settings, indicating if Mail and Syslog are enabled
        """
        history_setting = self.plugins.system_scheduler.configurable_configs[SCHEDULER_CONFIG_NAME]
        return jsonify({
            'system': self._system_settings,
            'global': {
                'mail': self._email_settings['enabled'] if self._email_settings else False,
                'syslog': self._syslog_settings['enabled'] if self._syslog_settings else False,
                'httpsLog': self._https_logs_settings['enabled'] if self._https_logs_settings else False,
                'jira': self._jira_settings['enabled'] if self._jira_settings else False,
                'opsgenie': self._opsgenie_settings['enabled'] if self._opsgenie_settings else False,
                'gettingStartedEnabled': self._getting_started_settings['enabled'],
                'passwordManagerEnabled': self._vault_settings['enabled'],
                'customerId': self.node_id,
                'historyEnabled': (history_setting['discovery_settings'][SCHEDULER_SAVE_HISTORY_CONFIG_NAME]
                                   if history_setting else False)
            }
        })

    def _stop_temp_maintenance(self):
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

    @gui_route_logged_in('maintenance', methods=['GET'])
    def get_maintenance(self):
        """
        Manage the maintenance features which can be customly set by user or switched all on for a limited time.
        GET returns current config for the features

        """
        match_maintenance = {
            'type': 'maintenance'
        }

        return jsonify(self.system_collection.find_one(match_maintenance))

    @gui_route_logged_in('maintenance', methods=['POST', 'PUT', 'DELETE'], required_permission=PermissionValue.get(
        PermissionAction.Update, PermissionCategory.Settings))
    def update_maintenance(self):
        """
        Manage the maintenance features which can be customly set by user or switched all on for a limited time.
        POST updates current config for the features
        PUT start all features for given duration of time
        DELETE stop all features (should be available only if they are temporarily on)

        """
        match_maintenance = {
            'type': 'maintenance'
        }
        if request.method == 'POST':
            # For any enable/disable config
            self.system_collection.update_one(match_maintenance, {
                '$set': self.get_request_data_as_object()
            })
            self._stop_temp_maintenance()

        if request.method == 'DELETE':
            # Not sure when this is called
            self._stop_temp_maintenance()

        if request.method == 'PUT':
            # For timeout
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

    @gui_route_logged_in('<config_name>', methods=['POST', 'GET'])
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

    @gui_route_logged_in('historical_sizes', methods=['GET'])
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

    @gui_route_logged_in('metadata', methods=['GET'])
    def get_metadata(self):
        """
        Gets the system metadata.
        :return:
        """
        return jsonify(self.metadata)

    @gui_route_logged_in('run_manual_discovery', methods=['POST'])
    def schedule_research_phase(self):
        """
        Schedules or initiates research phase.

        :return: Map between each adapter and the number of devices it has, unless no devices
        """
        return self._schedule_research_phase()

    def _schedule_research_phase(self):
        """Add for public API usage."""
        self._trigger_remote_plugin(SYSTEM_SCHEDULER_PLUGIN_NAME, blocking=False, external_thread=False)

        self._lifecycle.clean_cache()
        return ''

    @gui_route_logged_in('stop_research_phase', methods=['POST'], required_permission=PermissionValue.get(
        PermissionAction.RunManualDiscovery, PermissionCategory.Settings))
    def stop_research_phase(self):
        """
        Stops currently running research phase.
        """
        return self._stop_research_phase()

    def _stop_research_phase(self):
        """
        Stops currently running research phase.
        """
        logger.info('Stopping research phase')
        response = self.request_remote_plugin('stop_all', SYSTEM_SCHEDULER_PLUGIN_NAME, 'POST')

        if response.status_code != 200:
            logger.error(
                f'Could not stop research phase. returned code: {response.status_code}, '
                f'reason: {str(response.content)}')
            return return_error(f'Could not stop research phase {str(response.content)}', response.status_code)

        self._lifecycle.clean_cache()
        return ''

    @staticmethod
    def _jsonify_api_data(api_key, api_secret):
        return jsonify({
            'api_key': api_key,
            'api_secret': api_secret
        })

    @gui_route_logged_in('api_key', methods=['GET'], enforce_permissions=False)
    def get_api_key(self):
        api_data = self._users_collection.find_one({
            '_id': get_connected_user_id()
        })
        return self._jsonify_api_data(api_data['api_key'], api_data['api_secret'])

    @gui_route_logged_in('reset_api_key', methods=['POST'])
    def update_api_key(self):
        """
        Get or change the API key
        """
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
        return self._jsonify_api_data(new_api_key, new_token)
