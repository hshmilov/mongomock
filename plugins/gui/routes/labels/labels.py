from flask import (jsonify)

from gui.logic.routing_helper import gui_category_add_rules, gui_route_logged_in
#pylint: disable=no-self-use


@gui_category_add_rules('labels')
class Labels:
    @gui_route_logged_in(enforce_permissions=False)
    def get_labels(self):
        return self._get_labels()

    def _get_labels(self):
        return jsonify({
            'permissions.settings': 'System and User Management',
            'permissions.settings.get': 'View system settings',
            'permissions.settings.get_users_and_roles': 'View user accounts and roles',
            'permissions.settings.users.put': 'Add user',
            'permissions.settings.users.post': 'Edit users',
            'permissions.settings.roles.put': 'Add role',
            'permissions.settings.users.delete': 'Delete user',
            'permissions.settings.roles.post': 'Edit roles',
            'permissions.settings.roles.delete': 'Delete roles',
            'permissions.settings.reset_api_key': 'Reset API Key',
            'permissions.settings.post': 'Update system settings',
            'permissions.settings.run_manual_discovery': 'Run manual discovery cycle',
            'permissions.settings.audit.get': 'View Audit Log',

            'permissions.dashboard': 'Dashboard',
            'permissions.dashboard.get': 'View dashboard',
            'permissions.dashboard.charts.delete': 'Delete chart',
            'permissions.dashboard.charts.put': 'Add chart',
            'permissions.dashboard.charts.post': 'Edit charts',
            'permissions.dashboard.spaces.put': 'Add space',
            'permissions.dashboard.spaces.delete': 'Delete space',

            'permissions.devices_assets': 'Device Assets',
            'permissions.devices_assets.get': 'View devices',
            'permissions.devices_assets.post': 'Edit devices',
            'permissions.devices_assets.saved_queries.run': 'Run saved queries',
            'permissions.devices_assets.saved_queries.post': 'Edit saved queries',
            'permissions.devices_assets.saved_queries.delete': 'Delete saved query',
            'permissions.devices_assets.saved_queries.put': 'Create saved query',

            'permissions.users_assets': 'User Assets',
            'permissions.users_assets.get': 'View users',
            'permissions.users_assets.post': 'Edit users',
            'permissions.users_assets.saved_queries.run': 'Run saved queries',
            'permissions.users_assets.saved_queries.post': 'Edit saved queries',
            'permissions.users_assets.saved_queries.delete': 'Delete saved query',
            'permissions.users_assets.saved_queries.put': 'Create saved query',

            'permissions.reports': 'Reports',
            'permissions.reports.get': 'View reports',
            'permissions.reports.put': 'Add report',
            'permissions.reports.post': 'Edit reports',
            'permissions.reports.delete': 'Delete report',

            'permissions.instances': 'Instances',
            'permissions.instances.get': 'View instances',
            'permissions.instances.post': 'Edit instance',

            'permissions.adapters': 'Adapters',
            'permissions.adapters.get': 'View adapters',
            'permissions.adapters.connections.put': 'Add connection',
            'permissions.adapters.connections.post': 'Edit connections',
            'permissions.adapters.post': 'Edit adapter advanced settings',
            'permissions.adapters.connections.delete': 'Delete connection',

            'permissions.enforcements': 'Enforcement Center',
            'permissions.enforcements.get': 'View Enforcement Center',
            'permissions.enforcements.post': 'Edit Enforcement',
            'permissions.enforcements.put': 'Add Enforcement',
            'permissions.enforcements.tasks.get': 'View Enforcement Tasks',
            'permissions.enforcements.delete': 'Delete Enforcement',
            'permissions.enforcements.run': 'Run Enforcement',

            'permissions.compliance': 'Cloud Asset Compliance',
            'permissions.compliance.get': 'View Cloud Asset Compliance',
        })
