import csv
import io
import logging
from datetime import datetime
from enum import Enum

from bson import ObjectId
from flask import jsonify, make_response, request

from axonius.consts.gui_consts import (FILE_NAME_TIMESTAMP_FORMAT,
                                       LAST_UPDATED_FIELD, ChartViews,
                                       DASHBOARD_SPACE_TYPE_PERSONAL)
from axonius.entities import EntityType
from axonius.plugin_base import return_error
from axonius.utils.gui_helpers import (get_connected_user_id, historical_range,
                                       paginated, search_filter, sorted_by_method_endpoint)
from axonius.utils.permissions_helper import (PermissionAction,
                                              PermissionCategory,
                                              PermissionValue)
from axonius.utils.revving_cache import WILDCARD_ARG, NoCacheException
from gui.logic.dashboard_data import (fetch_chart_segment,
                                      fetch_chart_segment_historical,
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


class ChartTitle(Enum):

    intersect = 'Query Intersection'
    compare = 'Query Comparison'
    segment = 'Field Segmentation'
    abstract = 'Field Summary'
    timeline = 'Query Timeline'

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

    @gui_route_logged_in('<space_id>', methods=['PUT'], enforce_trial=False,
                         activity_params=[CHART_TYPE, SPACE_NAME, CHART_NAME])
    def add_dashboard_space_panel(self, space_id):
        """
        POST a new Dashboard Panel configuration, attached to requested space

        :param space_id: The ObjectId of the space for adding the panel to
        :return:         An error with 400 status code if failed, or empty response with 200 status code, otherwise
        """
        dashboard_data = dict(self.get_request_data_as_object())
        if not dashboard_data.get('name'):
            return return_error('Name required in order to save Dashboard Chart', 400)
        if not dashboard_data.get('config'):
            return return_error('At least one query required in order to save Dashboard Chart', 400)
        dashboard_data['space'] = ObjectId(space_id)
        dashboard_data['user_id'] = get_connected_user_id()
        dashboard_data[LAST_UPDATED_FIELD] = datetime.now()
        insert_result = self._dashboard_collection.insert_one(dashboard_data)
        if not insert_result or not insert_result.inserted_id:
            return return_error('Error saving dashboard chart', 400)
        # Adding to the 'panels_order' attribute the newly panelId created through the wizard
        dashboard_space = self._dashboard_spaces_collection.find_one_and_update({
            '_id': ObjectId(space_id)
        }, {
            '$push': {
                'panels_order': str(insert_result.inserted_id)
            }
        })
        return jsonify({
            SPACE_NAME: dashboard_space.get('name', ''),
            CHART_NAME: dashboard_data.get('name', ''),
            CHART_TYPE: ChartTitle.from_name(dashboard_data.get('metric'))
        })

    @paginated()
    @historical_range()
    @search_filter()
    @gui_route_logged_in('<panel_id>', methods=['GET'], required_permission=PermissionValue.get(
        PermissionAction.View, PermissionCategory.Dashboard))
    @sorted_by_method_endpoint()
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
        panel_id = ObjectId(panel_id)
        if request.args.get('refresh', False):
            generate_dashboard.clean_cache([panel_id, sort_by, sort_order])
            generate_dashboard_historical.clean_cache([panel_id, sort_by, sort_order, WILDCARD_ARG, WILDCARD_ARG])

        if from_date and to_date:
            generated_dashboard = generate_dashboard_historical(panel_id, from_date, to_date,
                                                                sort_by=sort_by, sort_order=sort_order)
        else:
            try:
                if request.args.get('refresh', False):
                    # we want to wait for a fresh data
                    generated_dashboard = generate_dashboard.wait_for_cache(panel_id, sort_by=sort_by,
                                                                            sort_order=sort_order,
                                                                            wait_time=REQUEST_MAX_WAIT_TIME)
                else:
                    generated_dashboard = generate_dashboard(panel_id, sort_by=sort_by, sort_order=sort_order)
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
            return jsonify(self._process_initial_dashboard_data(dashboard_data))

        return jsonify({
            'data': dashboard_data[skip: skip + limit],
            'count': len(dashboard_data)
        })

    @gui_route_logged_in('<panel_id>', methods=['POST'], activity_params=[SPACE_NAME, CHART_NAME])
    def update_dashboard_panel(self, panel_id):
        """
        POST an update of the configuration for an existing Dashboard Panel
        :param panel_id: The mongo id of the panel to handle
        :return: chart name / dashboard name
        """
        panel_id = ObjectId(panel_id)

        update_data = {
            **self.get_request_data_as_object(),
            'user_id': get_connected_user_id(),
            'last_updated': datetime.now()
        }
        chart = self._dashboard_collection.find_one_and_update(
            {'_id': panel_id}, {'$set': update_data}, {'name': 1, 'space': 1})

        if not chart:
            return return_error(f'No dashboard by the id {str(panel_id)} found or updated', 400)

        generate_dashboard.clean_cache([panel_id])
        generate_dashboard_historical.clean_cache([panel_id, WILDCARD_ARG, WILDCARD_ARG])

        space = self._dashboard_spaces_collection.find_one({'_id': chart.get('space')}, {'name': 1})

        return jsonify({
            SPACE_NAME: space.get('name', ''),
            CHART_NAME: chart.get('name', '')
        })

    @gui_route_logged_in('<panel_id>', methods=['DELETE'],
                         required_permission=PermissionValue.get(None,
                                                                 PermissionCategory.Dashboard,
                                                                 PermissionCategory.Charts),
                         activity_params=[SPACE_NAME, CHART_NAME])
    def delete_dashboard_panel(self, panel_id):
        """
        DELETE an existing Dashboard Panel and DELETE its panelId from the
        "panels_order" in the "dashboard_space" collection

        :param panel_id: The mongo id of the panel to handle
        :return: ObjectId of the Panel to delete
        """
        panel_id = ObjectId(panel_id)

        update_data = {
            'archived': True
        }

        chart = self._dashboard_collection.find_one_and_update(
            {'_id': panel_id}, {'$set': update_data}, {'name': 1, 'space': 1})

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
        personal_space = self._dashboard_spaces_collection.find_one({'type': DASHBOARD_SPACE_TYPE_PERSONAL},
                                                                    {'_id': 1})
        if personal_space.get('_id') == destination_space_id:
            return return_error(f'Can not move panels to {personal_space.get("name")}',
                                400)

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
    def chart_segment_csv(self, panel_id, from_date: datetime, to_date: datetime):
        card = self._dashboard_collection.find_one({
            '_id': ObjectId(panel_id)
        })
        if (not card.get('view') or not card.get('config') or not card['config'].get('entity')
                or not card['config'].get('field')):
            return return_error('Error: no such data available ', 400)
        card['config']['entity'] = EntityType(card['config']['entity'])
        if from_date and to_date:
            data = fetch_chart_segment_historical(card, from_date, to_date)
        else:
            data = fetch_chart_segment(ChartViews[card['view']], **card['config'])
        name = card['config']['field']['title']
        string_output = io.StringIO()
        dw = csv.DictWriter(string_output, [name, 'count'])
        dw.writeheader()
        dw.writerows([{name: x['name'], 'count': x['value']} for x in data])
        outputFile = make_response(string_output.getvalue().encode('utf-8'))
        timestamp = datetime.now().strftime(FILE_NAME_TIMESTAMP_FORMAT)
        outputFile.headers['Content-Disposition'] = f'attachment; filename=axonius-chart-{card["name"]}_{timestamp}.csv'
        outputFile.headers['Content-type'] = 'text/csv'
        return outputFile
