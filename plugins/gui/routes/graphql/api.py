from flask import request

from axonius.utils import gui_helpers
from axonius.utils.gui_helpers import Permission, PermissionType, ReadOnlyJustForGet
from gui.logic.routing_helper import gui_add_rule_logged_in
from gui.routes.graphql import graphql
# pylint: disable=no-member,no-self-use


class GraphQLAPI:
    @gui_helpers.paginated()
    @gui_add_rule_logged_in('graphql/search/devices', methods=['GET'],
                            required_permissions={Permission(PermissionType.Devices,
                                                             ReadOnlyJustForGet)})
    def search_devices(self, limit, skip):
        response = graphql.search_devices(request.args.get('term'), limit, skip, request.args.get('count', False))
        if not response:
            return None
        if response.status_code != 200:
            return {}
        return response.text

    @gui_helpers.paginated()
    @gui_add_rule_logged_in('graphql/search/users', methods=['GET'],
                            required_permissions={Permission(PermissionType.Users,
                                                             ReadOnlyJustForGet)})
    def search_users(self, limit, skip):
        response = graphql.search_users(request.args.get('term'), limit, skip, request.args.get('count', False))
        if not response:
            return None
        if response.status_code != 200:
            return {}
        return response.text
