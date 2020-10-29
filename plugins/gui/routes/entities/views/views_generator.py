import re
from flask import (jsonify,
                   request)

from axonius.plugin_base import EntityType, return_error
from axonius.utils.gui_helpers import (paginated, filtered, sorted_endpoint, metadata)
from axonius.utils.permissions_helper import PermissionCategory, PermissionAction, PermissionValue
from axonius.consts.gui_consts import ACTIVITY_PARAMS_COUNT, ACTIVITY_PARAMS_NAME
from gui.logic.api_helpers import get_page_metadata
from gui.logic.routing_helper import gui_section_add_rules, gui_route_logged_in
from gui.logic.views_data import get_views_count
# pylint: disable=no-member


def views_generator(base_permission_category: PermissionCategory):

    @gui_section_add_rules('views', permission_section=PermissionCategory.SavedQueries)
    class Views:

        @paginated()
        @filtered()
        @sorted_endpoint()
        @metadata()
        @gui_route_logged_in('<query_type>', methods=['GET'], required_permission=PermissionValue.get(
            PermissionAction.View, base_permission_category))
        def get_views(self, limit, skip, mongo_filter, mongo_sort, query_type,
                      get_metadata: bool = True,
                      include_details: bool = False):
            """
            Get saved view for the entity

            path: /api/devices/views/<query_type>
            path: /api/users/views/<query_type>

            :return:
            """
            views = self._get_entity_views(self.entity_type, limit, skip, mongo_filter, mongo_sort, query_type)
            if get_metadata:
                assets = list(views)
                page_meta = get_page_metadata(
                    skip=skip,
                    limit=limit,
                    number_of_assets=self._get_views_count(mongo_filter))
                page_meta['size'] = len(assets)
                return jsonify({'page': page_meta, 'assets': assets})

            if query_type == 'saved':
                for view in views:
                    if self.gui_dbs.entity_saved_queries_indirect[self.entity_type].count_documents({
                            'target': view.get('uuid', '')
                    }):
                        view['is_referenced'] = True
                    else:
                        view['is_referenced'] = False

            return jsonify(
                views)

        @gui_route_logged_in(methods=['PUT'], proceed_and_set_access=True)
        def add_entity_views(self, no_access):
            """
            Add views over the devices db

            path: /api/devices/views
            path: /api/devices/views

            :return:
            """
            # If there are no permissions, also check that the request doesn't relate to the private query
            # Only then we report error and exit
            if no_access and not request.get_json().get('private'):
                return return_error('You are lacking some permissions for this request', 401)

            return jsonify(self._add_entity_view(self.entity_type))

        @filtered()
        @gui_route_logged_in('<query_type>', methods=['DELETE'], activity_params=[ACTIVITY_PARAMS_COUNT],
                             proceed_and_set_access=True)
        def delete_views(self, query_type, mongo_filter, no_access):
            """
            Delete views over the devices db

            path: /api/devices/views/<query_type>
            path: /api/devices/views/<query_type>
            """
            # If there are no permissions, also check that the request doesn't relate to the private query
            # Only then we report error and exit
            if no_access and not request.get_json().get('private'):
                return return_error('You are lacking some permissions for this request', 401)

            return jsonify({ACTIVITY_PARAMS_COUNT: str(self._delete_entity_views(self.entity_type, mongo_filter))})

        @gui_route_logged_in('view/<view_id>', methods=['DELETE'], proceed_and_set_access=True,
                             activity_params=[ACTIVITY_PARAMS_NAME])
        def delete_sq_from_panel(self, view_id, no_access):
            """
            Delete Entity View by ID

            path: /api/devices/views/view/<view_id>
            path: /api/users/views/view/<view_id>
            """
            if no_access and not request.get_json().get('private'):
                return return_error('You are lacking some permissions for this request', 401)

            deleted_entity = self._delete_entity_view(self.entity_type, view_id)
            if deleted_entity:
                return jsonify({
                    ACTIVITY_PARAMS_NAME: deleted_entity.get(ACTIVITY_PARAMS_NAME, '')
                })
            return return_error(f'Entity ID {view_id} type {self.entity_type.value} not found !', 400)

        @gui_route_logged_in('<query_id>', methods=['POST'], proceed_and_set_access=True)
        def views_update(self, query_id, no_access):
            """
            Update name of an existing view

            path: /api/devices/views/<query_id>
            path: /api/users/views/<query_id>

            :return:
            """
            # If there are no permissions, also check that the request doesn't relate to the private query
            # Only then we report error and exit
            if no_access and not request.get_json().get('private'):
                return return_error('You are lacking some permissions for this request', 401)

            error = self._update_entity_views(self.entity_type, query_id)
            return return_error(error, 400) if error else ''

        @gui_route_logged_in('<query_id>/publish', methods=['POST'], required_permission=PermissionValue.get(
            PermissionAction.Add, base_permission_category, PermissionCategory.SavedQueries))
        def views_publish(self, query_id):
            """
            Sets private view to public

            path: /api/devices/views/<query_id>/publish
            path: /api/users/views/<query_id>/publish

            :return:
            """
            error = self._update_entity_views(self.entity_type, query_id)
            return return_error(error, 400) if error else ''

        @gui_route_logged_in('tags', methods=['GET'], required_permission=PermissionValue.get(
            PermissionAction.View, base_permission_category))
        def get_entity_saved_queries_tags(self):
            """"
            path: /api/devices/views/tags
            path: /api/users/views/tags
            """
            return jsonify(self._get_queries_tags_by_entity(self.entity_type))

        @gui_route_logged_in('names_list', methods=['GET'], required_permission=PermissionValue.get(
            PermissionAction.View, base_permission_category))
        def get_entity_saved_queries_names_list(self):
            """"
            path: /api/devices/views/names_list
            path: /api/users/views/names_list
            """
            return jsonify(self._get_queries_names_by_entity(self.entity_type))

        @filtered()
        @gui_route_logged_in('<query_type>/count', methods=['GET'], required_permission=PermissionValue.get(
            PermissionAction.View, base_permission_category))
        def get_entities_views_count(self, mongo_filter, query_type):
            """"
            path: /api/devices/views/<query_type>/count
            path: /api/users/views/<query_type>/count
            """
            content = self.get_request_data_as_object()
            quick = content.get('quick') or request.args.get('quick')
            quick = quick == 'True'
            return str(self._get_views_count(mongo_filter, query_type, quick))

        def _get_views_count(self, mongo_filter, query_type='saved', quick=False):
            mongo_filter['query_type'] = query_type
            return get_views_count(self.entity_type, mongo_filter, quick=quick)

        @property
        def entity_type(self):
            m = re.search('/api/(.+?)([\\?/].*)?$', request.url)
            if m:
                return EntityType(m.group(1))
            return None

        @gui_route_logged_in('references/<query_id>', methods=['GET'], required_permission=PermissionValue.get(
            PermissionAction.View, base_permission_category))
        def get_query_references(self, query_id):
            """
            return the invalid references that the <query_id> cannot reference (use as a saved_query in the wizard)
            due to circular dependency.

            path: /api/devices/views/references/<query_id>
            path: /api/users/views/references/<query_id>

            :return:
            """
            return jsonify(self._get_saved_query_invalid_references(self.entity_type, query_id))

    return Views
