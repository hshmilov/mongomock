import copy
import csv
import io
import logging
import threading
from datetime import datetime
from enum import Enum

from bson import ObjectId
from flask import jsonify, make_response, request
from pymongo import ReturnDocument

from axonius.consts.gui_consts import (FILE_NAME_TIMESTAMP_FORMAT,
                                       LAST_UPDATED_FIELD, ChartViews,
                                       DASHBOARD_SPACE_TYPE_PERSONAL)
from axonius.entities import EntityType
from axonius.logging.audit_helper import AuditCategory, AuditAction
from axonius.plugin_base import return_error
from axonius.utils.gui_helpers import (get_connected_user_id, historical_range,
                                       paginated, search_filter, sorted_by_method_endpoint)
from axonius.utils.permissions_helper import (PermissionAction,
                                              PermissionCategory,
                                              PermissionValue)
from axonius.utils.revving_cache import WILDCARD_ARG, NoCacheException
from gui.logic.dashboard_data import (fetch_chart_segment,
                                      fetch_chart_segment_historical,
                                      fetch_chart_adapter_segment,
                                      fetch_chart_adapter_segment_historical,
                                      generate_dashboard_historical)
from gui.logic.routing_helper import gui_route_logged_in, gui_section_add_rules
from gui.routes.dashboard.dashboard import generate_dashboard

logger = logging.getLogger(f'axonius.{__name__}')

REQUEST_MAX_WAIT_TIME = 10 * 60

# AUDIT CONST
CHART_TYPE_REQUEST = 'metric'
CHART_NAME_REQUEST = 'name'
CHART_TYPE = 'chart_type'
CHART_NAME = 'chart_name'
CHART_ID = 'chart_id'
SPACE_NAME = 'space_name'
SPACE_ID = 'ID'

SOURCE_SPACE_ID = 'source_space_id'
SOURCE_SPACE_NAME = 'source_space_name'
TARGET_SPACE_ID = 'target_space_id'
TARGET_SPACE_NAME = 'target_space_name'

NO_ACCESS_ERROR_MESSAGE = 'You are lacking some permissions for this request'


class ChartTitle(Enum):
    intersect = 'Query Intersection'
    compare = 'Query Comparison'
    segment = 'Field Segmentation'
    adapter_segment = 'Adapter Segmentation'
    abstract = 'Field Summary'
    timeline = 'Query Timeline'
    matrix = 'Matrix Data'

    @classmethod
    def from_name(cls, name):
        try:
            return cls[name].value
        except KeyError:
            return ''


# pylint: disable=no-member
@gui_section_add_rules('charts')
class Charts:

    @paginated()
    @gui_route_logged_in(methods=['GET'], enforce_trial=False, required_permission=PermissionValue.get(
        PermissionAction.View, PermissionCategory.Dashboard))
    def get_dashboard_data(self, skip, limit):
        """
        Return charts data for the requested page.
        Charts attached to the Personal dashboard and a different user the connected one, are excluded

        """
        return jsonify(self._get_dashboard(skip, limit))

    def restrict_space_action_by_user_role(self, space_id: ObjectId):
        space = self._dashboard_spaces_collection.find_one({
            '$and': [
                {'_id': space_id},
                {
                    '$or': [
                        {'public': {'$in': [None, True]}},
                        {'roles': str(self.get_user_role_id())}
                    ]
                } if not self.is_admin_user() else {}
            ]
        })
        if space:
            return False
        return True

    @gui_route_logged_in('<space_id>', methods=['PUT'], enforce_trial=False,
                         activity_params=[CHART_TYPE, SPACE_NAME, CHART_NAME], proceed_and_set_access=True)
    def add_dashboard_space_panel(self, space_id, no_access):
        """
        POST a new Dashboard chart configuration, attached to requested space

        :param space_id: The ObjectId of the space for adding the panel to
        :param no_access: this endpoint called by user with no permissions if true
        :return:         An error with 400 status code if failed, or empty response with 200 status code, otherwise
        """
        source_space_id = ObjectId(space_id)

        if no_access and not self._is_personal_space(source_space_id):
            return return_error(NO_ACCESS_ERROR_MESSAGE, 401)

        chart_data = dict(self.get_request_data_as_object())
        if not chart_data.get('name'):
            return return_error('Name required in order to save Dashboard Chart', 400)
        if not chart_data.get('config'):
            return return_error('At least one query required in order to save Dashboard Chart', 400)

        if self.restrict_space_action_by_user_role(source_space_id):
            return return_error(NO_ACCESS_ERROR_MESSAGE, 401)
        chart_data['space'] = source_space_id
        chart_data['user_id'] = get_connected_user_id()
        chart_data[LAST_UPDATED_FIELD] = datetime.now()
        insert_result = self._dashboard_collection.insert_one(chart_data)
        if not insert_result or not insert_result.inserted_id:
            return return_error('Error saving dashboard chart', 400)
        chart_id = insert_result.inserted_id
        trend_chart_id = self._trend_chart_handler(chart_data, chart_id, source_space_id)
        # Adding to the 'panels_order' attribute the newly panelId created through the wizard
        space = self._dashboard_spaces_collection.find_one_and_update({
            '_id': ObjectId(space_id)
        }, {
            '$push': {
                'panels_order': str(chart_id)
            }
        })
        chart_name = chart_data.get('name', '')
        chart_metric = chart_data.get('metric')
        chart_config = chart_data.get('config', {})
        try:
            sort = chart_config.get('sort', {})
            generate_dashboard(chart_id, sort.get('sort_by'), sort.get('sort_order'))
        except NoCacheException:
            pass
        return jsonify({
            'uuid': str(chart_id),
            'config': chart_config,
            'metric': chart_metric,
            'name': chart_name,
            'space': str(space_id),
            'user_id': str(chart_data.get('user_id')),
            'view': chart_data.get('view'),
            'linked_dashboard': str(trend_chart_id),
            SPACE_NAME: space.get('name', ''),
            CHART_NAME: chart_name,
            CHART_TYPE: chart_metric
        })

    def _trend_chart_handler(self, chart_data, chart_id: ObjectId, space_id: ObjectId):
        if chart_data.get('config').get('show_timeline'):
            generated_id = self._link_trend_chart(chart_data, chart_id, space_id)
            return generated_id
        if chart_data.get('linked_dashboard', None):
            self._unlink_trend_chart(chart_data.get('linked_dashboard'), chart_id)
        return None

    def _unlink_trend_chart(self, trend_chart_id, chart_id: ObjectId):
        self._dashboard_collection.find_one_and_delete({
            '_id': ObjectId(trend_chart_id)
        })
        self._dashboard_collection.find_one_and_update({
            '_id': chart_id
        }, {
            '$unset': {'linked_dashboard': 1}
        })

    def _get_db_cached_data(self, chart_id):
        chart_data = self._dashboard_collection.find_one({'_id': ObjectId(chart_id)})
        if chart_data and chart_data.get('cached_result') and \
                chart_data.get('cached_config', {}) == chart_data.get('config', {}):
            logger.info(f'Got chart {chart_data.get("name")} from db cache')
            return chart_data.get('cached_result')
        return None

    def _set_db_cached_data(self, chart_id, data):
        current_config = self._dashboard_collection.find_one({'_id': ObjectId(chart_id)}).get('config')
        self._dashboard_collection.find_one_and_update(
            {
                '_id': ObjectId(chart_id)
            },
            {
                '$set': {
                    'cached_result': data,
                    'cached_config': current_config
                }
            }
        )

    def _async_generate_dashboard(self, panel_id, sort_by=None, sort_order=None):
        try:
            logger.debug(f'Started generating panel id {panel_id} async')
            generated_dashboard = generate_dashboard.wait_for_cache(panel_id, sort_by=sort_by,
                                                                    sort_order=sort_order,
                                                                    wait_time=REQUEST_MAX_WAIT_TIME)
        except (TimeoutError, NoCacheException):
            # the dashboard is still being calculated
            logger.debug(f'Async Dashboard {panel_id} is not ready')
            return
        dashboard_data = generated_dashboard.get('data', [])
        truncated_dashboard_data = self._process_initial_dashboard_data(dashboard_data)
        logger.info(f'Finished generating panel id: {panel_id} asynchronously')
        self._set_db_cached_data(panel_id, truncated_dashboard_data)

    def _link_trend_chart(self, chart_data, chart_id: ObjectId, space_id: ObjectId):
        config = chart_data.get('config')
        trend_chart_data = {
            'metric': 'segment_timeline',
            'name': chart_data.get('name'),
            'view': 'line',
            'space': space_id,
            'user_id': get_connected_user_id(),
            'is_linked_dashboard': True,
            'hide_empty': True,
            'config': {
                'entity': config['entity'], 'view': config['view'],
                'field': config['field'], 'value_filter': config['value_filter'],
                'include_empty': config.get('include_empty', False),
                'timeframe': config['timeframe']
            }, LAST_UPDATED_FIELD: datetime.now()
        }

        insert_result = self._dashboard_collection.find_one_and_update(
            {'_id': ObjectId(chart_data.get('linked_dashboard'))},
            {'$set': trend_chart_data},
            upsert=True,
            return_document=ReturnDocument.AFTER
        )
        if insert_result and insert_result.get('_id'):
            # link trend chart to the original chart
            trend_chart_id = str(insert_result.get('_id'))
            self._dashboard_collection.find_one_and_update({
                '_id': chart_id
            }, {
                '$set': {'linked_dashboard': ObjectId(trend_chart_id)}
            })

            if chart_data.get('linked_dashboard'):
                # clean cache if chart was updated
                generate_dashboard.clean_cache([trend_chart_id, None, None])
                generate_dashboard_historical.clean_cache([trend_chart_id, WILDCARD_ARG, WILDCARD_ARG])
            return trend_chart_id

        return None

    @paginated()
    @historical_range()
    @search_filter()
    @gui_route_logged_in('<panel_id>', methods=['GET'], required_permission=PermissionValue.get(
        PermissionAction.View, PermissionCategory.Dashboard), enforce_trial=False)
    @sorted_by_method_endpoint()
    # pylint: disable=too-many-branches, unexpected-keyword-arg
    def get_dashboard_panel(self, panel_id, skip, limit, from_date: datetime, to_date: datetime,
                            search: str, sort_by=None, sort_order=None):
        """
        GET partial data of the Dashboard Panel

        :param panel_id: The mongo id of the panel to handle
        :param skip: For GET, requested offset of panel's data
        :param limit: For GET, requested limit of panel's data
        :param to_date: the latest date to get the data
        :param from_date: the earlier date to start get the data
        :param search: a string to filter the data
        :param sort_by: sort for specific charts like segmentation. sort by value or segment.
        :param sort_order desc/asc
        """
        is_refresh = request.args.get('refresh', False) == 'true'
        is_blocking = request.args.get('blocking', False) == 'true'
        got_from_db_cache = False
        panel_id = ObjectId(panel_id)
        if is_refresh:
            generate_dashboard.clean_cache([panel_id, sort_by, sort_order])
            generate_dashboard_historical.clean_cache([panel_id, sort_by, sort_order, WILDCARD_ARG, WILDCARD_ARG])

        if from_date and to_date:
            generated_dashboard = generate_dashboard_historical(panel_id, from_date, to_date,
                                                                sort_by=sort_by, sort_order=sort_order,
                                                                use_semaphore=True)
        else:
            generated_dashboard = None
            try:
                if is_refresh:
                    # we want to wait for a fresh data
                    generated_dashboard = generate_dashboard.wait_for_cache(panel_id, sort_by=sort_by,
                                                                            sort_order=sort_order,
                                                                            wait_time=REQUEST_MAX_WAIT_TIME)
                elif is_blocking:
                    if not generate_dashboard.has_cache(panel_id, sort_by=sort_by, sort_order=sort_order):
                        try:
                            generated_dashboard = self._get_db_cached_data(panel_id)
                        except Exception:
                            logger.error(f'Couldn\'t get cached data from db for panel id: {panel_id}', exc_info=True)
                    if generated_dashboard is None:
                        generated_dashboard = generate_dashboard.wait_for_cache(panel_id, sort_by=sort_by,
                                                                                sort_order=sort_order,
                                                                                wait_time=REQUEST_MAX_WAIT_TIME,
                                                                                use_semaphore=True)
                    else:
                        got_from_db_cache = True
                        thread = threading.Thread(target=self._async_generate_dashboard,
                                                  args=(panel_id,),
                                                  kwargs={'sort_by': sort_by, 'sort_order': sort_order},
                                                  daemon=True)
                        thread.start()
                else:
                    generated_dashboard = generate_dashboard(panel_id, sort_by=sort_by, sort_order=sort_order,
                                                             use_semaphore=True)
            except (TimeoutError, NoCacheException):
                # the dashboard is still being calculated
                logger.debug(f'Dashboard {panel_id} is not ready')
                generated_dashboard = {}

        error = generated_dashboard.get('error', None)
        if error is not None:
            return return_error(error, 400)

        dashboard_data = generated_dashboard.get('data', [])
        if search:
            dashboard_data = [data for data in dashboard_data
                              if search.lower() in self.get_string_value(data['name']).lower()]
        if not skip:
            truncated_dashboard_data = self._process_initial_dashboard_data(dashboard_data)
            if not got_from_db_cache:
                try:
                    self._set_db_cached_data(panel_id, truncated_dashboard_data)
                except Exception:
                    logger.error(f'Couldn\'t save db cached data to panel id: {panel_id}', exc_info=True)
            return jsonify(truncated_dashboard_data)

        return jsonify({
            'data': dashboard_data[skip: skip + limit],
            'count': len(dashboard_data)
        })

    @gui_route_logged_in('<panel_id>', methods=['POST'], activity_params=[SPACE_NAME, CHART_NAME],
                         proceed_and_set_access=True)
    def update_dashboard_panel(self, panel_id, no_access):
        """
        POST an update of the configuration for an existing Dashboard Panel
        :param panel_id: The mongo id of the panel to handle
        :param no_access: this endpoint called by user with no permissions if true
        :return: chart name / dashboard name
        """
        panel_id = ObjectId(panel_id)
        old_chart = self._dashboard_collection.find_one({
            '_id': panel_id
        }, {
            'space': 1, 'config': 1
        })

        if no_access and not self._is_personal_space(old_chart.get('space')):
            return return_error(NO_ACCESS_ERROR_MESSAGE, 401)

        if self.restrict_space_action_by_user_role(old_chart.get('space')):
            return return_error(NO_ACCESS_ERROR_MESSAGE, 401)

        dashboard_data = dict(self.get_request_data_as_object())

        update_data = {
            **dashboard_data,
            'user_id': get_connected_user_id(),
            'last_updated': datetime.now()
        }
        new_chart = self._dashboard_collection.find_one_and_update(
            filter={'_id': panel_id},
            update={'$set': update_data},
            return_document=ReturnDocument.AFTER)

        if not new_chart:
            return return_error(f'No dashboard by the id {str(panel_id)} found or updated', 400)
        space = self._dashboard_spaces_collection.find_one({'_id': new_chart.get('space')}, {'name': 1})
        # if required by config, recreate and link a linked dashboard
        trend_chart_id = self._trend_chart_handler(update_data, panel_id, space['_id'])

        # we clean the cache of the updated config, in the next request the chart data will be refreshed
        if new_chart['config'] != old_chart['config']:
            generate_dashboard.clean_cache([panel_id, WILDCARD_ARG, WILDCARD_ARG])
            generate_dashboard_historical.clean_cache([panel_id, WILDCARD_ARG, WILDCARD_ARG])

        return jsonify({
            'uuid': str(panel_id),
            'config': new_chart.get('config', {}),
            'metric': new_chart.get('metric'),
            'name': new_chart.get('name'),
            'space': str(space['_id']),
            'user_id': str(new_chart.get('user_id')),
            'view': new_chart.get('view'),
            'linked_dashboard': str(trend_chart_id),
            SPACE_NAME: space.get('name', ''),
            CHART_NAME: new_chart.get('name', '')
        })

    @gui_route_logged_in('<panel_id>', methods=['DELETE'],
                         required_permission=PermissionValue.get(None,
                                                                 PermissionCategory.Dashboard,
                                                                 PermissionCategory.Charts),
                         activity_params=[SPACE_NAME, CHART_NAME], proceed_and_set_access=True)
    def delete_dashboard_panel(self, panel_id, no_access):
        """
        DELETE an existing Dashboard Panel and DELETE its panelId from the
        "panels_order" in the "dashboard_space" collection

        :param panel_id: The mongo id of the panel to handle
        :param no_access: this endpoint called by user with no permissions if true
        :return: ObjectId of the Panel to delete
        """
        panel_id = ObjectId(panel_id)
        old_chart = self._dashboard_collection.find_one(filter={'_id': panel_id}, projection={'space': 1})

        if no_access and not self._is_personal_space(old_chart.get('space')):
            return return_error(NO_ACCESS_ERROR_MESSAGE, 401)

        if self.restrict_space_action_by_user_role(old_chart.get('space')):
            return return_error(NO_ACCESS_ERROR_MESSAGE, 401)

        if no_access and not self._is_personal_space(old_chart.get('space')):
            return return_error(NO_ACCESS_ERROR_MESSAGE, 401)

        update_data = {
            'archived': True
        }

        chart = self._dashboard_collection.find_one_and_update(
            {'_id': panel_id}, {'$set': update_data}, {'name': 1, 'space': 1, 'linked_dashboard': 1})
        if not chart:
            return return_error(f'No dashboard by the id {str(panel_id)} found or updated', 400)

        space = self._dashboard_spaces_collection.find_one_and_update({
            '_id': chart.get('space')
        }, {
            '$pull': {
                'panels_order': str(panel_id)
            },
        }, {
            'name': 1
        })

        self._dashboard_spaces_collection.update_one({
            '_id': chart.get('space')
        }, {
            '$pull': {
                'panels_order': str(panel_id)
            }
        })

        generate_dashboard.remove_from_cache([panel_id])
        generate_dashboard_historical.remove_from_cache([panel_id, WILDCARD_ARG, WILDCARD_ARG])

        if chart.get('linked_dashboard'):
            self.delete_dashboard_panel(chart['linked_dashboard'], no_access=False)

        return jsonify({
            SPACE_NAME: space.get('name', ''),
            CHART_NAME: chart.get('name', '')
        })

    ################################################
    #           MOVE
    ################################################

    @gui_route_logged_in('move/<panel_id>', methods=['PUT'],
                         required_permission=PermissionValue.get(PermissionAction.Update,
                                                                 PermissionCategory.Dashboard,
                                                                 PermissionCategory.Charts),
                         activity_params=[SOURCE_SPACE_NAME, TARGET_SPACE_NAME, CHART_NAME])
    def move_dashboard_panel(self, panel_id):
        """
        :param panel_id: The mongo id of the panel to handle
        """
        destination_space_id = self.get_request_data_as_object().get('destinationSpace')

        chart = self._dashboard_collection.find_one({'_id': ObjectId(panel_id)}, {'name': 1, 'space': 1})

        if not chart:
            return return_error(f'No chart by the id {str(panel_id)}', 400)
        personal_space = self._dashboard_spaces_collection.find_one(
            {'type': DASHBOARD_SPACE_TYPE_PERSONAL,
             'user_id': get_connected_user_id()},
            {'_id': 1})
        if personal_space and personal_space.get('_id') == destination_space_id:
            return return_error(f'Can not move panels to {personal_space.get("name")}', 400)

        if self.restrict_space_action_by_user_role(ObjectId(destination_space_id)):
            return return_error(NO_ACCESS_ERROR_MESSAGE, 401)

        target_space = self._dashboard_spaces_collection.find_one_and_update({
            '_id': ObjectId(destination_space_id)
        }, {
            '$push': {
                'panels_order': str(panel_id)
            }
        })

        source_space = self._dashboard_spaces_collection.find_one_and_update({
            '_id': chart.get('space')
        }, {
            '$pull': {
                'panels_order': str(panel_id)
            }
        })

        self._dashboard_collection.find_one_and_update(
            {'_id': ObjectId(panel_id)}, {'$set': {'space': ObjectId(destination_space_id)}})

        return jsonify({
            SOURCE_SPACE_NAME: source_space.get('name', ''),
            TARGET_SPACE_NAME: target_space.get('name', ''),
            CHART_NAME: chart.get('name', '')
        })

    @gui_route_logged_in('reorder/<space_id>', methods=['GET'], enforce_trial=False,
                         required_permission=PermissionValue.get(PermissionAction.View, PermissionCategory.Dashboard))
    def get_dashboard_order_space_panels(self, space_id):
        return jsonify(self._dashboard_spaces_collection.find_one({
            '_id': ObjectId(space_id)
        }))

    ################################################
    #           EXPORT
    ################################################

    @historical_range()
    @gui_route_logged_in('<panel_id>/csv', methods=['GET'], required_permission=PermissionValue.get(
        PermissionAction.View, PermissionCategory.Dashboard))
    def generate_chart_csv(self, panel_id, from_date: datetime, to_date: datetime):
        card = self._dashboard_collection.find_one({
            '_id': ObjectId(panel_id)
        })

        handler_by_metric = {
            'segment': {
                'handler': self.generate_segment_csv,
                'required_config': ['entity'],
            },
            'adapter_segment': {
                'handler': self.generate_adapter_segment_csv,
                'required_config': ['entity'],
            },
            'timeline': {
                'handler': self.generate_timeline_csv,
                'required_config': [],
            },
            'segment_timeline': {
                'handler': self.generate_segment_timeline_csv,
                'required_config': [],
            }
        }

        if not card.get('view') or not card.get('config'):
            return return_error('Error: no such data available ', 400)

        for required_field in handler_by_metric[card['metric']]['required_config']:
            if not card['config'].get(required_field):
                return return_error(f'Error: no such required data available: {required_field}', 400)

        if card['config'].get('entity'):
            card['config']['entity'] = EntityType(card['config']['entity'])

        metric = card['metric']
        if metric in ('timeline', 'segment_timeline'):
            column_headers, rows = handler_by_metric[card['metric']]['handler'](card)
        else:
            column_headers, rows = handler_by_metric[metric]['handler'](card, from_date, to_date)

        string_output = io.StringIO()
        dw = csv.DictWriter(string_output, column_headers)
        dw.writeheader()
        dw.writerows(rows)
        output_file = make_response(string_output.getvalue().encode('utf-8'))
        timestamp = datetime.now().strftime(FILE_NAME_TIMESTAMP_FORMAT)
        output_file.headers['Content-Disposition'] = \
            f'attachment; filename=axonius-chart-{card["name"]}_{timestamp}.csv'
        output_file.headers['Content-type'] = 'text/csv'
        chart_name = card['name']
        self.log_activity_user(AuditCategory.Charts, AuditAction.ExportCsv, {
            'chart_name': chart_name
        })
        return output_file

    @staticmethod
    def generate_segment_csv(card, from_date, to_date):
        if not card['config'].get('field'):
            return return_error('Error: no such data available ', 400)

        if from_date and to_date:
            data = fetch_chart_segment_historical(card, from_date, to_date)
        else:
            data = fetch_chart_segment(ChartViews[card['view']], **card['config'])
        name = card['config']['field']['title']
        return [name, 'count'], [{name: x['name'], 'count': x['value']} for x in data]

    @staticmethod
    def generate_timeline_csv(card):
        generated_dashboard = generate_dashboard(card['_id'], sort_by=None, sort_order=None)
        data = copy.deepcopy(generated_dashboard.get('data', []))

        def get_row_data_as_dict(row_data, headers_names):
            """
            extract data from list of timeline points ( values )
            :param row_data: list of values from timeline data
            :param headers_names: list of columns names as strings
            :return: dict with column header names as keys and the corresponding values as value
            """
            row = {}
            for index, header in enumerate(headers_names):
                row[header] = row_data[index]
            return row

        def normalize_rows(data_to_normalize, data_headers):
            """
            fill empty holes in the data.
            go through all the rows of data from the earliest date
            and keep track on the last known value for each header, if a value is missing
            ( e.g. this day the lifecycle didnt complete ) the value is set from the last known value per header
            :param data_to_normalize: timeline data
            :param data_headers: list of headers as string
            """
            last_values = [None for _ in range(len(data_headers))]
            for row in data_to_normalize:
                # first row cell is the date, we skip it in this logic
                for i in range(1, len(data_headers)):
                    if row[i]:
                        last_values[i] = row[i]
                    elif last_values[i]:
                        row[i] = last_values[i]

        # pop the first item from the list, this is the headers data
        header_data = data.pop(0)
        # the first item is 'Day', no need to keep him
        header_data.pop(0)
        headers = ['Date'] + [x['label'] for x in header_data]
        normalize_rows(data, headers)
        # sort the data in desc order
        sorted_data = sorted([get_row_data_as_dict(x, headers) for x in data], key=lambda i: i['Date'], reverse=True)
        return headers, sorted_data

    @staticmethod
    def generate_adapter_segment_csv(card, from_date, to_date):
        if from_date and to_date:
            data = fetch_chart_adapter_segment_historical(card, from_date, to_date)
        else:
            data = fetch_chart_adapter_segment(ChartViews[card['view']], **card['config'])
        return ['Adapter Name', 'count'], [{'Adapter Name': x['fullName'], 'count': x['value']} for x in data]

    @staticmethod
    def generate_segment_timeline_csv(card):
        generated_dashboard = generate_dashboard(card['_id'], sort_by=None, sort_order=None)
        data = copy.deepcopy(generated_dashboard.get('data', []))
        if data is None:
            return None
        return ['Date', 'Total segment values', 'Segment count'], \
               [{'Date': data[index][0], 'Total segment values': data[index][2], 'Segment count': data[index][1]}
                for index in range(1, len(data))]
