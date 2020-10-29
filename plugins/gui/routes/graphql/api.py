from flask import request

from axonius.utils import gui_helpers
from axonius.utils.permissions_helper import (PermissionCategory, PermissionAction,
                                              PermissionValue)
from gui.logic.routing_helper import gui_category_add_rules, gui_route_logged_in
from gui.logic.graphql import graphql


# pylint: disable=no-member,no-self-use
@gui_category_add_rules('graphql')
class GraphQLAPI:

    @gui_helpers.paginated()
    @gui_route_logged_in('search/devices', methods=['GET'], required_permission=PermissionValue.get(
        PermissionAction.View, PermissionCategory.DevicesAssets))
    def search_devices(self, limit, skip):
        """
        path: /api/graphql/search/devices
        """
        response = graphql.search_devices(request.args.get('term'), limit, skip, request.args.get('count', False))
        if not response:
            return None
        if response.status_code != 200:
            return {}
        return response.text

    @gui_helpers.paginated()
    @gui_route_logged_in('search/users', methods=['GET'], required_permission=PermissionValue.get(
        PermissionAction.View, PermissionCategory.UsersAssets))
    def search_users(self, limit, skip):
        """
        path: /api/graphql/search/users
        """
        response = graphql.search_users(request.args.get('term'), limit, skip, request.args.get('count', False))
        if not response:
            return None
        if response.status_code != 200:
            return {}
        return response.text
