from flask import (jsonify)

from gui.logic.routing_helper import gui_category_add_rules, gui_route_logged_in
#pylint: disable=no-self-use


@gui_category_add_rules('labels')
class Labels:
    @gui_route_logged_in(enforce_permissions=False)
    def get_labels(self):
        return jsonify(self._get_labels())

    @staticmethod
    def _get_labels():
        return {
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
            'permissions.settings.audit.get': 'View Activity Logs',

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

            'audit.session': 'User Session',
            'audit.session.login': 'Login',
            'audit.session.login.template': 'Login {status}',
            'audit.session.logout': 'Logout',
            'audit.session.logout.template': 'Logged out',
            'audit.session.failure': 'Login Failed',
            'audit.session.failure.template': 'Login failure attempt by {user_name}',

            'audit.session.changed_password': 'Set Password',
            'audit.session.changed_password.template': 'Password set for user {user_name}',

            'audit.settings.users': 'User Management',
            'audit.settings.users.put': 'Add User',
            'audit.settings.users.put.template': 'Added user \'{user_name}\'',
            'audit.settings.users.post': 'Edit User',
            'audit.settings.users.post.template': 'Edited user \'{user_name}\'',
            'audit.settings.users.delete': 'Delete User',
            'audit.settings.users.delete.template': 'Deleted {count} users',
            'audit.settings.users.assign_role': 'Assign Role',
            'audit.settings.users.assign_role.template': 'Assigned role \'{name}\' to {count} users',

            'audit.settings.roles': 'Role Management',
            'audit.settings.roles.put': 'Add Role',
            'audit.settings.roles.put.template': 'Added role \'{name}\'',
            'audit.settings.roles.post': 'Edit Role',
            'audit.settings.roles.post.template': 'Edited role \'{name}\'',
            'audit.settings.roles.delete': 'Delete Role',
            'audit.settings.roles.delete.template': 'Deleted role \'{name}\'',

            'audit.settings': 'Settings Management',
            'audit.settings.reset_api_key': 'Reset API Key',
            'audit.settings.reset_api_key.template': 'Reset API key',
            'audit.settings.run_manual_discovery': 'Run Manual Discovery',
            'audit.settings.run_manual_discovery.template': 'Ran manual discovery',
            'audit.settings.stop_research_phase': 'Stop Discovery',
            'audit.settings.stop_research_phase.template': 'Stopped discovery',

            'audit.settings.plugins': 'Settings Management',
            'audit.settings.plugins.post': 'Edit Settings',
            'audit.settings.plugins.post.template': 'Edited {config_name}',

            'audit.settings.configuration': 'Administration',
            'audit.settings.configuration.execute': 'Execute Config Script',
            'audit.settings.configuration.execute.template': 'Executed configuration script',
            'audit.settings.configuration.upload_file': 'Upload Config Script',
            'audit.settings.configuration.upload_file.template': 'Uploaded configuration script',

            'audit.settings.users.tokens': 'User Management',
            'audit.settings.users.tokens.generate': 'Password Reset Link',
            'audit.settings.users.tokens.generate.template': 'Password reset link generated '
                                                             'for user \'{user_name}\' ',
            'audit.settings.users.tokens.notify': 'Send Password Reset Link',
            'audit.settings.users.tokens.notify.template': 'Password reset link sent for user \'{user_name}\' ',

            'audit.self': 'Account Management',
            'audit.self.password': 'Change Password',
            'audit.self.password.template': 'Changed password',
            'audit.self.preferences': 'Edit Default Columns',
            'audit.self.preferences.template': 'Edited default columns',

            'audit.discovery': 'Discovery',
            'audit.discovery.start': 'Discovery Started',
            'audit.discovery.start.template': 'Discovery cycle started',
            'audit.discovery.start_phase': 'Discovery Phase Started',
            'audit.discovery.start_phase.template': 'Discovery phase \'{phase}\' started',
            'audit.discovery.complete_phase': 'Discovery Phase Ended',
            'audit.discovery.complete_phase.template': 'Discovery phase \'{phase}\' ended',
            'audit.discovery.complete': 'Discovery Ended',
            'audit.discovery.complete.template': 'Discovery cycle ended',

            'audit.getting_started': 'Getting Started',
            'audit.getting_started.complete_phase': 'Getting Started Phase Completed',
            'audit.getting_started.complete_phase.template': 'Getting Started phase \'{phase}\' completed',
            'audit.getting_started.complete': 'Getting Started Completed',
            'audit.getting_started.complete.template': 'Getting Started completed',

            'audit.instances': 'Instances',
            'audit.instances.post': 'Edit Instance',
            'audit.instances.post.template': 'Edited instance \'{node_name}\'',

            'audit.reports': 'Reports',
            'audit.reports.put': 'Add Report',
            'audit.reports.put.template': 'Added report \'{name}\'',
            'audit.reports.post': 'Edit Report',
            'audit.reports.post.template': 'Edited report \'{name}\'',
            'audit.reports.delete': 'Delete Report',
            'audit.reports.delete.template': 'Deleted {count} reports',
            'audit.reports.download': 'Download Report',
            'audit.reports.download.template': 'Downloaded report \'{name}\'',
            'audit.reports.send_email': 'Manual Sent Report',
            'audit.reports.send_email.template': 'Manually sent report \'{name}\'',

            'audit.adapters': 'Adapters',
            'audit.adapters.fetch': 'Fetch',
            'audit.adapters.fetch.template':
                'Fetched {count} {asset} for adapter \'{adapter}\' with connection ID {client_id}',
            'audit.adapters.clean': 'Cleanup',
            'audit.adapters.clean.template': 'Removed {count} {asset} from adapter \'{adapter}\'',
            'audit.adapters.post': 'Edit Advanced Settings',
            'audit.adapters.post.template': 'Edited {config_name} for adapter {adapter_name}',

            'audit.adapters.connections': 'Adapters',
            'audit.adapters.connections.put': 'Add Connection',
            'audit.adapters.connections.put.template':
                'Added new connection for adapter \'{adapter}\' with connection ID {client_id}',
            'audit.adapters.connections.post': 'Edit Connection',
            'audit.adapters.connections.post.template': 'Edited adapter \'{adapter}\' with connection ID {client_id}',
            'audit.adapters.connections.delete': 'Delete Connection',
            'audit.adapters.connections.delete.template': 'Deleted adapter \'{adapter}\' '
                                                          'with connection ID {client_id}',

            'audit.adapters.failure': 'Connection Failure',
            'audit.adapters.failure.template':
                'Connection failure for adapter \'{adapter}\' with connection ID {client_id}. Error: {error}',

            'audit.enforcements': 'Enforcements',
            'audit.enforcements.put': 'Add Enforcement',
            'audit.enforcements.put.template': 'Added enforcement \'{name}\'',
            'audit.enforcements.post': 'Edit Enforcement',
            'audit.enforcements.post.template': 'Edited enforcement \'{name}\'',
            'audit.enforcements.delete': 'Delete Enforcement',
            'audit.enforcements.delete.template': 'Deleted {deleted} enforcements',
            'audit.enforcements.start': 'Enforcement Started',
            'audit.enforcements.start.template': 'Enforcement \'{enforcement}\' with task ID {task} started',
            'audit.enforcements.complete': 'Enforcement Ended',
            'audit.enforcements.complete.template': 'Enforcement \'{enforcement}\' with task ID {task} completed',
            'audit.enforcements.trigger': 'Run Enforcement',
            'audit.enforcements.trigger.template': 'Executed enforcement \'{name}\'',

            'audit.devices.views': 'Device Saved Queries',
            'audit.devices.views.put': 'Create Saved Query',
            'audit.devices.views.put.template': 'Created saved query {name}',
            'audit.devices.views.post': 'Edit Saved Query',
            'audit.devices.views.post.template': 'Edited saved query {name}',
            'audit.devices.views.delete': 'Delete Saved Query',
            'audit.devices.views.delete.template': 'Deleted {count} saved queries',

            'audit.users.views': 'User Saved Query',
            'audit.users.views.put': 'Create Saved Query',
            'audit.users.views.put.template': 'Created saved query \'{name}\'',
            'audit.users.views.post': 'Edit Saved Query',
            'audit.users.views.post.template': 'Edited saved query \'{name}\'',
            'audit.users.views.delete': 'Delete Saved Query',
            'audit.users.views.delete.template': 'Deleted {count} saved queries',

            'audit.dashboard': 'Dashboard',
            'audit.dashboard.delete': 'Delete Space',
            'audit.dashboard.delete.template': 'Deleted dashboard space \'{space_name}\'',
            'audit.dashboard.post': 'Add Space',
            'audit.dashboard.post.template': 'Added dashboard space \'{name}\'',
            'audit.dashboard.put': 'Edit Space',
            'audit.dashboard.put.template': 'Edited dashboard space \'{before_space_name}\' to \'{space_name}\'',
            'audit.dashboard.reorder': 'Reorder Space',
            'audit.dashboard.reorder.template': 'Reordered charts on space {\'{space_name}\'',
            'audit.dashboard.charts': 'Dashboard',
            'audit.dashboard.charts.put': 'Add Chart',
            'audit.dashboard.charts.put.template':
                'Added chart \'{chart_name}\' of type {chart_type} on space \'{space_name}\'',
            'audit.dashboard.charts.post': 'Edit Chart',
            'audit.dashboard.charts.post.template': 'Edited chart \'{chart_name}\' on space \'{space_name}\'',
            'audit.dashboard.charts.delete': 'Delete Chart',
            'audit.dashboard.charts.delete.template': 'Deleted chart \'{chart_name}\' from space \'{space_name}\'',

            'audit.dashboard.charts.move': 'Move Chart',
            'audit.dashboard.charts.move.template':
                'Moved chart \'{chart_name}\' from space \'{source_space_name}\' to space \'{target_space_name}\'',

            'audit.devices': 'Devices',
            'audit.devices.enforce': 'Run Enforcement',
            'audit.devices.enforce.template': 'Executed enforcement \'{name}\'',
            'audit.devices.csv': 'Export CSV',
            'audit.devices.csv.template': 'Exported to CSV',
            'audit.devices.manual_link': 'Link',
            'audit.devices.manual_link.template': 'Linked {count} devices',
            'audit.devices.manual_unlink': 'Link',
            'audit.devices.manual_unlink.template': 'Unlinked {count} devices',
            'audit.devices.delete': 'Delete Device',
            'audit.devices.delete.template': 'Deleted {count} devices',
            'audit.devices.custom': 'Add Custom Data',
            'audit.devices.custom.template': 'Added custom data',
            'audit.devices.notes': 'Edit Note',
            'audit.devices.notes.template': 'Edited notes',
            'audit.devices.labels': 'Edit Tags',
            'audit.devices.labels.template': 'Edited tags',

            'audit.users': 'Users',
            'audit.users.enforce': 'Run Enforcement',
            'audit.users.enforce.template': 'Executed enforcement \'{name}\'',
            'audit.users.csv': 'Export CSV',
            'audit.users.csv.template': 'Exported to CSV',
            'audit.users.manual_link': 'Link',
            'audit.users.manual_link.template': 'Linked {count} users',
            'audit.users.manual_unlink': 'Link',
            'audit.users.manual_unlink.template': 'Unlinked {count} users',
            'audit.users.delete': 'Delete User',
            'audit.users.delete.template': 'Deleted {count} users',
            'audit.users.custom': 'Add Custom Data',
            'audit.users.custom.template': 'Added custom data',
            'audit.users.notes': 'Edit Note',
            'audit.users.notes.template': 'Edited notes',
            'audit.users.labels': 'Edit Tags',
            'audit.users.labels.template': 'Edited tags',

            'audit.compliance': 'Cloud Asset Compliance',
            'audit.compliance.csv': 'Export CSV',
            'audit.compliance.csv.template': 'Exported to CSV compliance {name}'

        }
