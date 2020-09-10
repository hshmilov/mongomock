import logging
from datetime import datetime
from typing import Dict

import pymongo
from bson import ObjectId
from flask import jsonify

from axonius.consts.gui_consts import (DASHBOARD_LIFECYCLE_ENDPOINT,
                                       DASHBOARD_SPACE_TYPE_CUSTOM,
                                       ResearchStatus, DashboardControlNames, DASHBOARD_CALL_LIMIT, TunnelStatuses,
                                       DASHBOARD_SPACE_TYPE_PERSONAL)
from axonius.consts.plugin_consts import SYSTEM_SCHEDULER_PLUGIN_NAME
from axonius.consts.scheduler_consts import (Phases, ResearchPhases,
                                             SchedulerState)
from axonius.logging.audit_helper import AuditCategory, AuditAction
from axonius.mixins.triggerable import TriggerStates
from axonius.plugin_base import EntityType, return_error
from axonius.utils.gui_helpers import (entity_fields, get_connected_user_id)
from axonius.utils.permissions_helper import (PermissionAction,
                                              PermissionCategory,
                                              PermissionValue)
from axonius.utils.revving_cache import (NoCacheException,
                                         rev_cached)
from gui.logic.dashboard_data import (adapter_data, generate_dashboard,
                                      generate_dashboard_uncached, dashboard_historical_uncached)
from gui.logic.fielded_plugins import get_fielded_plugins
from gui.logic.filter_utils import filter_archived
from gui.logic.historical_dates import (all_historical_dates,
                                        first_historical_date)
from gui.logic.routing_helper import (gui_category_add_rules,
                                      gui_route_logged_in)
from gui.routes.dashboard.charts import Charts, SPACE_NAME, SPACE_ID, NO_ACCESS_ERROR_MESSAGE
from gui.routes.dashboard.notifications import Notifications

logger = logging.getLogger(f'axonius.{__name__}')


# pylint: disable=no-member,invalid-name,inconsistent-return-statements,no-self-use
@gui_category_add_rules('dashboard')
class Dashboard(Charts, Notifications):

    def _is_personal_space(self, space_id: ObjectId) -> bool:
        space = self._dashboard_spaces_collection.find_one({
            '_id': space_id
        }, projection={'type': 1})
        return space and space.get('type') == DASHBOARD_SPACE_TYPE_PERSONAL

    def _insert_dashboard_chart(self, dashboard_name, dashboard_metric, dashboard_view, dashboard_data,
                                hide_empty=False, space_id=None):
        existed_dashboard_chart = self._dashboard_collection.find_one({'name': dashboard_name})
        if existed_dashboard_chart is not None and existed_dashboard_chart.get('archived'):
            logger.info(f'Report {dashboard_name} was removed')
            return None

        if dashboard_data.get('entity'):
            views_collection = self.gui_dbs.entity_query_views_db_map[EntityType(dashboard_data['entity'])]
            if 'base' in dashboard_data:
                dashboard_data['base'] = str(views_collection.find_one({
                    'name': dashboard_data['base']
                }, {'_id': 1})['_id']) if dashboard_data.get('base') else ''
                dashboard_data['intersecting'] = [str(views_collection.find_one({
                    'name': view
                }, {'_id': 1})['_id']) for view in dashboard_data.get('intersecting', [])]
        result = self._dashboard_collection.replace_one({
            'name': dashboard_name
        }, {
            'name': dashboard_name,
            'metric': dashboard_metric,
            'view': dashboard_view,
            'config': dashboard_data,
            'hide_empty': hide_empty,
            'user_id': '*',
            'space': space_id
        }, upsert=True)
        return result.upserted_id

    @gui_route_logged_in('first_use', methods=['GET'], enforce_trial=False)
    def dashboard_first(self):
        """
        __is_first_time_use maintains whether any adapter was connected with a client.
        Otherwise, user should be offered to take a walkthrough of the system.

        :return: Whether this is the first use of the system
        """
        return jsonify(self._is_system_first_use)

    @gui_route_logged_in('is_system_empty', methods=['GET'], enforce_trial=False)
    def dashboard_is_empty(self):
        """
        :return: Whether this is the first use of the system
        """

        try:
            is_users_seen = adapter_data(EntityType.Users).get('seen', False)
            is_devices_seen = adapter_data(EntityType.Devices).get('seen', False)
        except Exception:
            error = f'Could not get adapter data'
            logger.exception(error)
            return return_error(error, 400)
        entities_not_seen = (not is_devices_seen) and (not is_users_seen)
        return jsonify(self._is_system_first_use and entities_not_seen)

    @gui_route_logged_in('first_historical_date', methods=['GET'], enforce_permissions=False)
    def get_first_historical_date(self):
        return jsonify(first_historical_date())

    @gui_route_logged_in('get_allowed_dates', enforce_permissions=False)
    def all_historical_dates(self):
        return jsonify(all_historical_dates())

    @gui_route_logged_in(methods=['GET'], enforce_trial=False)
    def get_dashboards(self):
        """
        GET all the saved spaces.

        :return:
        """
        personal_space_filter = {
            '$and': [
                {'type': DASHBOARD_SPACE_TYPE_PERSONAL},
                {'user_id': get_connected_user_id()}
            ]
        }
        public_spaces_with_roles_filter = {
            '$and': [
                {
                    '$or': [
                        {'public': {'$in': [None, True]}},
                        {'roles': str(self.get_user_role_id())}
                    ]
                },
                {'type': {'$ne': DASHBOARD_SPACE_TYPE_PERSONAL}}
            ]
        }
        all_public_spaces_filter = {'type': {'$ne': DASHBOARD_SPACE_TYPE_PERSONAL}}
        spaces_filter = filter_archived({
            '$or': [
                personal_space_filter,
                public_spaces_with_roles_filter if not self.is_admin_user() else all_public_spaces_filter
            ]
        })
        spaces = [{
            'uuid': str(space['_id']),
            'name': space['name'],
            'roles': space.get('roles', []),
            'public': space.get('public', True),
            'type': space['type']
        } for space in self._dashboard_spaces_collection.find(spaces_filter)]

        return jsonify({
            'spaces': spaces
        })

    @gui_route_logged_in('<space_id>', methods=['GET'], activity_params=[SPACE_NAME])
    def get_space_by_id(self, space_id):

        if not space_id:
            return_error('space id is required', 400)
        space_filter = filter_archived({
            '_id': ObjectId(space_id)
        })
        space = self._dashboard_spaces_collection.find_one(space_filter)

        charts_filter = filter_archived({
            'space': ObjectId(space_id),
            'is_linked_dashboard': {'$ne': True}
        })

        def check_visible(chart):
            """
            Filter out chart with hide_empty flag, when they have no data
            :param chart:
            :return: Boolean
            """
            if not chart.get('hide_empty'):
                return True
            chart_sort_config = chart.get('config', {}).get('sort', {})
            try:
                chart_data = generate_dashboard(
                    chart['_id'],
                    sort_by=chart_sort_config.get('sort_by', None),
                    sort_order=chart_sort_config.get('sort_order', None))
                has_data = chart_data.get('data') and chart_data['data'][0].get('portion', 0) not in [0, 1]
            except NoCacheException:
                return False
            return has_data
        charts = [{
            'uuid': str(chart.get('_id')),
            'config': chart.get('config', {}),
            'metric': chart.get('metric'),
            'name': chart.get('name'),
            'space': str(chart.get('space')),
            'user_id': str(chart.get('user_id')),
            'view': chart.get('view'),
            'linked_dashboard': str(chart.get('linked_dashboard', ''))
        } for chart in self._dashboard_collection.find(charts_filter) if check_visible(chart)]

        if not space:
            return_error('Internal Server Error', 500)
        return jsonify({
            'uuid': str(space['_id']),
            'name': space['name'],
            'roles': space.get('roles', []),
            'public': space.get('public', True),
            'panels_order': space.get('panels_order', []),
            'type': space['type'],
            'charts': charts
        })

    @gui_route_logged_in('<space_id>', methods=['PUT'],
                         enforce_trial=False,
                         required_permission=PermissionValue.get(PermissionAction.Add,
                                                                 PermissionCategory.Dashboard,
                                                                 PermissionCategory.Spaces),
                         skip_activity=True)
    def update_dashboard_space(self, space_id):
        """
        PUT an updated name for an existing Dashboard Space

        :param space_id: The ObjectId of the existing space
        :return:         An error with 400 status code if failed, or empty response with 200 status code, otherwise
        """
        space_data = self.get_request_data_as_object()
        space_to_update = self._dashboard_spaces_collection.find_one({
            '_id': ObjectId(space_id)
        }, {
            'type': 1
        })
        if not space_to_update or space_to_update.get('type') == DASHBOARD_SPACE_TYPE_PERSONAL:
            return return_error(f'Requested Dashboard Space not found ({space_id})', 400)
        before_space_data = self._dashboard_spaces_collection.find_one_and_update({
            '_id': ObjectId(space_id)
        }, {
            '$set': space_data
        })
        self._log_activity_spaces(before_space_data, space_data)
        return jsonify({
            'before_space_name': before_space_data.get('name', ''),
            'name': space_data.get('name', ''),
            'roles': space_data.get('roles', []),
            'public': space_data.get('access', True)
        })

    def _log_activity_spaces(self, old_space, new_space):
        old_name = old_space.get('name', '')
        new_name = new_space.get('name', '')
        if new_name != old_name:
            self.log_activity_user(AuditCategory.Dashboard, AuditAction.ChangedName, {
                'before_space_name': old_name,
                'space_name': new_name
            })
        new_access = new_space.get('public', True)
        old_access = old_space.get('public', True)
        new_roles = new_space.get('roles', [])
        old_roles = old_space.get('roles', [])
        if new_access != old_access or new_roles != old_roles:
            self.log_activity_user(AuditCategory.Dashboard, AuditAction.ChangedPermissions, {
                'space_name': new_name
            })

    @gui_route_logged_in('<space_id>', methods=['DELETE'], enforce_trial=False,
                         required_permission=PermissionValue.get(PermissionAction.Delete,
                                                                 PermissionCategory.Dashboard,
                                                                 PermissionCategory.Spaces),
                         activity_params=[SPACE_NAME])
    def delete_dashboard_space(self, space_id):
        """
        DELETE an existing Dashboard Space

        :param space_id: The ObjectId of the existing space
        :return:         An error with 400 status code if failed, or empty response with 200 status code, otherwise
        """
        delete_result = self._dashboard_spaces_collection.find_one_and_delete({
            '_id': ObjectId(space_id)
        })
        # if not delete_result or delete_result.deleted_count == 0:
        if not delete_result:
            return return_error('Could not remove the requested Dashboard Space', 400)
        # return delete_result.get('name','')
        return jsonify({
            SPACE_ID: space_id,
            SPACE_NAME: delete_result.get('name', '')
        })

    @gui_route_logged_in(methods=['POST'], enforce_trial=False, required_permission=PermissionValue.get(
        PermissionAction.Add, PermissionCategory.Dashboard, PermissionCategory.Spaces))
    def update_dashboards(self):
        """
        POST a new space that will have the type 'custom'

        :return:
        """
        space_data = dict(self.get_request_data_as_object())
        space_data['type'] = DASHBOARD_SPACE_TYPE_CUSTOM
        insert_result = self._dashboard_spaces_collection.insert_one(space_data)
        if not insert_result or not insert_result.inserted_id:
            return return_error(f'Could not create a new space named {space_data["name"]}')
        return str(insert_result.inserted_id)

    @staticmethod
    def _process_initial_dashboard_data(dashboard_data: list) -> Dict[str, object]:
        """
        Truncates the given data to allow viewing the beginning and end of the values, if more than 100

        :param dashboard_data: List of values to be shown in the form of some dashboard chart
        :return: Tail and head of the list (50) or entire list, if up to 100 values and the total count
        """
        data_length = len(dashboard_data)
        data_limit, data_tail_limit = 50, -50
        if data_length <= 100:
            data_limit, data_tail_limit = 100, data_length
        return {
            'data': dashboard_data[:data_limit],
            'data_tail': dashboard_data[data_tail_limit:],
            'count': data_length
        }

    @staticmethod
    def get_string_value(base_value):
        if isinstance(base_value, datetime):
            return base_value.strftime('%a, %d %b %Y %H:%M:%S GMT')
        return str(base_value)

    def _clear_dashboard_cache(self, clear_slow=False):
        """
        Clears the calculated dashboard cache, and async recalculates all dashboards
        :param clear_slow: Also clear the slow cache
        """
        if clear_slow:
            generate_dashboard.update_cache()
        adapter_data.update_cache()
        get_fielded_plugins.update_cache()
        first_historical_date.clean_cache()
        all_historical_dates.clean_cache()
        entity_fields.clean_cache()
        self._lifecycle.clean_cache()
        self._adapters.clean_cache()
        self._adapters_v2.clean_cache()

    def _init_all_dashboards(self):
        """
        Warms up the cache for all dashboards for all users
        """
        dashboard_control = self._current_feature_flag_config.get(DashboardControlNames.root_key, {})
        generate_dashboard_uncached.init_semaphore(dashboard_control.get(
            DashboardControlNames.present_call_limit, DASHBOARD_CALL_LIMIT))
        dashboard_historical_uncached.init_semaphore(dashboard_control.get(
            DashboardControlNames.historical_call_limit, DASHBOARD_CALL_LIMIT))
        for dashboard in self._dashboard_collection.find(
                filter=filter_archived(),
                projection={
                    '_id': True,
                    'config.sort': True
                }):
            try:
                dashboard_sort_config = dashboard['config'].get('sort', {}) or {}
                generate_dashboard(dashboard['_id'],
                                   sort_by=dashboard_sort_config.get('sort_by', None),
                                   sort_order=dashboard_sort_config.get('sort_order', None))
            except NoCacheException:
                logger.debug(f'dashboard {dashboard["_id"]} is not ready')
            except Exception:
                logger.warning(f'Failed generating dashboard for {dashboard}', exc_info=True)

    def _get_dashboard(self, skip=0, limit=0, uncached: bool = False,
                       space_ids: list = None, exclude_personal=False, generate_data=True):
        """
        GET Fetch current dashboard chart definitions. For each definition, fetch each of it's views and
        fetch devices_db with their view. Amount of results is mapped to each views' name, under 'data' key,
        to be returned with the dashboard definition.

        POST Save a new dashboard chart definition, given it has a name and at least one query attached

        If 'uncached' is True, then this will return a non cached version
        If 'space_ids' is List[str] and has more then 0 space ids then fetch only these dashboard spaces

        :return:
        """
        logger.debug('Getting dashboard')
        all_personal_spaces = self._dashboard_spaces_collection.find({
            'type': DASHBOARD_SPACE_TYPE_PERSONAL}, {'_id': 1})
        if not list(all_personal_spaces):
            logger.critical('Missing personal space')
            return return_error('Missing personal space', 400)

        all_personal_spaces_ids = [space['_id'] for space in all_personal_spaces]
        filter_spaces = {
            'space': {
                '$in': [ObjectId(space_id) for space_id in space_ids]
            } if space_ids else {'$nin': all_personal_spaces_ids},
            'name': {
                '$ne': None
            },
            'config': {
                '$ne': None
            }
        }
        if not exclude_personal:
            personal_space = self._dashboard_spaces_collection.find_one({
                'type': DASHBOARD_SPACE_TYPE_PERSONAL, 'user_id': get_connected_user_id()}, {'_id': 1})
            if personal_space:
                personal_id = personal_space['_id']
                filter_spaces = {
                    '$or': [{
                        'space': personal_id,
                        'user_id': {
                            '$in': ['*', get_connected_user_id()]
                        }
                    }, filter_spaces]
                }
        for dashboard in self._dashboard_collection.find(
                filter=filter_archived(filter_spaces),
                skip=skip,
                limit=limit,
                projection={
                    '_id': True,
                    'space': True,
                    'name': True,
                    'config.sort': True,
                    'hide_empty': True,
                    'linked_dashboard': True,
                    'is_linked_dashboard': True
                }):
            dashboard_sort_config = dashboard['config'].get('sort', {}) or {}
            # Let's fetch and execute them query filters
            try:
                generated_dashboard = {}
                if generate_data:
                    if uncached:
                        generated_dashboard = generate_dashboard_uncached(dashboard['_id'])
                    else:
                        try:
                            generated_dashboard = generate_dashboard(
                                dashboard['_id'],
                                sort_by=dashboard_sort_config.get('sort_by', None),
                                sort_order=dashboard_sort_config.get('sort_order', None))
                        except NoCacheException:
                            logger.debug(f'dashboard {dashboard["_id"]} is not ready')
                    if generated_dashboard:
                        yield {
                            **generated_dashboard,
                            **self._process_initial_dashboard_data(generated_dashboard.get('data', [])),
                        }
                if not generate_data or not generated_dashboard:
                    yield {
                        'uuid': str(dashboard['_id']),
                        'name': dashboard['name'],
                        'is_linked_dashboard': dashboard.get('is_linked_dashboard', False),
                        'linked_dashboard': str(dashboard.get('linked_dashboard', None)),
                        'data': [],
                        'loading': True,
                        'hide_empty': dashboard.get('hide_empty', False)
                    }
            except Exception:
                # Since there is no data, not adding this chart to the list
                logger.exception(f'Error fetching data for chart ({dashboard["_id"]})')

    @gui_route_logged_in('adapter_data/<entity_name>', methods=['GET'], enforce_trial=False)
    def get_adapter_data(self, entity_name):
        try:
            return jsonify(adapter_data(EntityType(entity_name)))
        except KeyError:
            error = f'No such entity {entity_name}'
        except Exception:
            error = f'Could not get adapter data for entity {entity_name}'
            logger.exception(error)
        return return_error(error, 400)

    def _get_lifecycle_phase_info(self, doc_id: ObjectId) -> dict:
        """
        :param  doc_id: the id of the triggerable_history job to get the result from
        :return: the result field in the triggerable_history collection
        """
        if not doc_id:
            return {}
        result = self.aggregator_db_connection['triggerable_history'].find_one(
            {
                '_id': doc_id
            },
            sort=[('started_at', pymongo.DESCENDING)]
        )
        if not result or not result['result']:
            return {}
        return result['result']

    @rev_cached(ttl=3, key_func=lambda self: 1)
    def _lifecycle(self):
        # pylint: disable=no-member
        res = self.request_remote_plugin('trigger_state/execute', SYSTEM_SCHEDULER_PLUGIN_NAME)
        if not res or res.status_code != 200:
            raise RuntimeError('Scheduler not responding')
        execution_state = res.json()
        if 'state' not in execution_state:
            message = f'Scheduler failed with message: {execution_state.get("message", "")}'
            logger.error(message)
            raise RuntimeError(message)
        is_running = execution_state['state'] == TriggerStates.Triggered.name
        del res, execution_state

        state_response = self.request_remote_plugin('state', SYSTEM_SCHEDULER_PLUGIN_NAME)
        if state_response.status_code != 200:
            raise RuntimeError(f'Error fetching status of system scheduler. Reason: {state_response.text}')

        state_response = state_response.json()
        state = SchedulerState(**state_response['state'])
        is_research = state.Phase == Phases.Research.name

        if state_response['stopping']:
            nice_state = ResearchStatus.stopping
        elif is_research:
            nice_state = ResearchStatus.running
        elif is_running:
            nice_state = ResearchStatus.starting
        else:
            nice_state = ResearchStatus.done

        # Map each sub-phase to a dict containing its name and status, which is determined by:
        # - Sub-phase prior to current sub-phase - 1
        # - Current sub-phase - complementary of retrieved status (indicating complete portion)
        # - Sub-phase subsequent to current sub-phase - 0
        sub_phases = []
        found_current = False
        for sub_phase in ResearchPhases:
            additional_data = {}
            if is_research and sub_phase.name == state.SubPhase:
                # Reached current status - set complementary of SubPhaseStatus value
                found_current = True
                if sub_phase.name in (ResearchPhases.Fetch_Devices.name, ResearchPhases.Fetch_Scanners.name):
                    doc_id = state_response.get('state').get('AssociatePluginId')
                    additional_data = self._get_lifecycle_phase_info(doc_id=ObjectId(doc_id))

                sub_phases.append({
                    'name': sub_phase.name,
                    'status': 0,
                    'additional_data': additional_data
                })
            else:
                # Set 0 or 1, depending if reached current status yet
                sub_phases.append({
                    'name': sub_phase.name,
                    'status': 0 if found_current else 1,
                    'additional_data': additional_data
                })

        # check tunnel status
        tunnel_gui_status = self.get_tunnel_status()
        # pylint: enable=no-member

        return {
            'sub_phases': sub_phases,
            'next_run_time': state_response['next_run_time'],
            'last_start_time': state_response['last_start_time'],
            'last_finished_time': state_response['last_finished_time'],
            'status': nice_state.name,
            'tunnel_status': tunnel_gui_status
        }
    # pylint: enable=too-many-branches

    def get_tunnel_status(self) -> TunnelStatuses:
        """
        get the status of the current machine,
        this method relay on non-existing variables to know if this is not a saas machine
        or if the first time connection happened
        :return: tunnel status from the enum TunnelStatuses
        """
        if hasattr(self, 'tunnel_status'):
            if hasattr(self, 'tunnel_first_up') and self.tunnel_first_up:
                status = TunnelStatuses.connected if self.tunnel_status else TunnelStatuses.disconnected
            else:
                status = TunnelStatuses.never_connected
        else:
            status = TunnelStatuses.not_available
        return status

    @gui_route_logged_in(DASHBOARD_LIFECYCLE_ENDPOINT, methods=['GET'], enforce_trial=False,
                         required_permission_values={PermissionValue.get(PermissionAction.RunManualDiscovery,
                                                                         PermissionCategory.Settings)})
    def get_system_lifecycle(self):
        """
        Fetches and build data needed for presenting current status of the system's lifecycle in a graph

        :return: Data containing:
         - All research phases names, for showing the whole picture
         - Current research sub-phase, which is empty if system is not stable
         - Portion of work remaining for the current sub-phase
         - The time next cycle is scheduled to run
        """
        return jsonify(self._lifecycle())

    ################################################
    #           REORDER
    ################################################

    @gui_route_logged_in('reorder/<space_id>', methods=['POST'], enforce_trial=False,
                         required_permission=PermissionValue.get(PermissionAction.Update,
                                                                 PermissionCategory.Dashboard,
                                                                 PermissionCategory.Charts),
                         activity_params=[SPACE_NAME], proceed_and_set_access=True)
    def reorder_dashboard_space_panels(self, space_id, no_access):

        if no_access and not self._is_personal_space(ObjectId(space_id)):
            return return_error(NO_ACCESS_ERROR_MESSAGE, 401)

        panels_order = self.get_request_data_as_object().get('panels_order')
        space = self._dashboard_spaces_collection.find_one_and_update({
            '_id': ObjectId(space_id)
        }, {
            '$set': {
                'panels_order': panels_order
            },
        }, {
            'name': 1
        })
        return jsonify({
            SPACE_ID: space_id,
            SPACE_NAME: space.get('name', '')
        })
