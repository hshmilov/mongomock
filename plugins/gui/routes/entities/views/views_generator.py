import re
from flask import (jsonify,
                   request)

from axonius.plugin_base import EntityType
from axonius.utils.gui_helpers import (paginated, filtered, sorted_endpoint)
from axonius.utils.permissions_helper import PermissionCategory, PermissionAction, PermissionValue
from gui.logic.routing_helper import gui_section_add_rules, gui_route_logged_in
from gui.logic.views_data import get_views_count
# pylint: disable=no-member


def views_generator(base_permission_category: PermissionCategory):

    @gui_section_add_rules('views', permission_section=PermissionCategory.SavedQueries)
    class Views:

        @paginated()
        @filtered()
        @sorted_endpoint()
        @gui_route_logged_in('<query_type>', methods=['GET'],
                             required_permission_values={PermissionValue.get(PermissionAction.View,
                                                                             base_permission_category)})
        def get_views(self, limit, skip, mongo_filter, mongo_sort, query_type):
            """
            Get saved view for the entity
            :return:
            """
            return jsonify(
                self._get_entity_views(self.entity_type, limit, skip, mongo_filter, mongo_sort, query_type))

        @gui_route_logged_in('<query_type>', methods=['PUT', 'POST'])
        def update_entity_views(self, query_type):
            """
            Add/ Update views over the devices db
            :return:
            """
            return jsonify(
                self._update_entity_views(self.entity_type, query_type))

        @filtered()
        @gui_route_logged_in('<query_type>', methods=['DELETE'])
        def delete_views(self, query_type, mongo_filter):
            """
            Delete views over the devices db
            :return:
            """
            return jsonify(
                self._delete_entity_views(self.entity_type, mongo_filter))

        @gui_route_logged_in('saved/<query_id>', methods=['POST'])
        def views_update(self, query_id):
            """
            Update name of an existing view
            :return:
            """
            self._entity_views_update(self.entity_type, query_id)
            return ''

        @gui_route_logged_in('tags', methods=['GET'],
                             required_permission_values={PermissionValue.get(PermissionAction.View,
                                                                             base_permission_category)})
        def get_entity_saved_queries_tags(self):
            return jsonify(self._get_queries_tags_by_entity(self.entity_type))

        @gui_route_logged_in('names_list', methods=['GET'],
                             required_permission_values={PermissionValue.get(PermissionAction.View,
                                                                             base_permission_category)})
        def get_entity_saved_queries_names_list(self):
            return jsonify(self._get_queries_names_by_entity(self.entity_type))

        @filtered()
        @gui_route_logged_in('<query_type>/count', methods=['GET'],
                             required_permission_values={PermissionValue.get(PermissionAction.View,
                                                                             base_permission_category)})
        def get_devices_views_count(self, mongo_filter, query_type):
            content = self.get_request_data_as_object()
            quick = content.get('quick') or request.args.get('quick')
            quick = quick == 'True'
            mongo_filter['query_type'] = query_type
            return str(get_views_count(self.entity_type, mongo_filter, quick=quick))

        @property
        def entity_type(self):
            m = re.search('/api/(.+?)([\\?/].*)?$', request.url)
            if m:
                return EntityType(m.group(1))
            return None

    return Views
