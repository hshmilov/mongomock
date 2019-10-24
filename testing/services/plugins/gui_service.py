import json
import os
from collections import defaultdict
import secrets
import logging
import requests
from axonius.consts.gui_consts import (CONFIG_CONFIG, ROLES_COLLECTION, USERS_COLLECTION,
                                       DASHBOARD_COLLECTION, DASHBOARD_SPACES_COLLECTION,
                                       DASHBOARD_SPACE_DEFAULT, DASHBOARD_SPACE_PERSONAL,
                                       DASHBOARD_SPACE_TYPE_DEFAULT, DASHBOARD_SPACE_TYPE_PERSONAL,
                                       PREDEFINED_ROLE_ADMIN, PREDEFINED_ROLE_RESTRICTED, PREDEFINED_ROLE_READONLY,
                                       FEATURE_FLAGS_CONFIG, Signup, EXEC_REPORT_TITLE)
from axonius.consts.plugin_consts import (AGGREGATOR_PLUGIN_NAME,
                                          AXONIUS_SETTINGS_DIR_NAME,
                                          CONFIGURABLE_CONFIGS_COLLECTION,
                                          GUI_PLUGIN_NAME,
                                          PLUGIN_NAME,
                                          PLUGIN_UNIQUE_NAME,
                                          MAINTENANCE_TYPE,
                                          GUI_SYSTEM_CONFIG_COLLECTION,
                                          LIBS_PATH)
from axonius.entities import EntityType
from axonius.utils.gui_helpers import PermissionLevel, PermissionType
from gui.gui_logic.filter_utils import filter_archived
from services.plugin_service import PluginService
from services.updatable_service import UpdatablePluginMixin
logger = logging.getLogger(f'axonius.{__name__}')
MAINTENANCE_FILTER = {'type': MAINTENANCE_TYPE}


class GuiService(PluginService, UpdatablePluginMixin):
    def __init__(self):
        super().__init__('gui')
        self._session = requests.Session()
        self.override_exposed_port = True
        local_npm = os.path.join(self.service_dir, 'frontend', 'node_modules')
        local_dist = os.path.join(self.service_dir, 'frontend', 'dist')
        self.is_dev = os.path.isdir(local_npm) and os.path.isdir(local_dist)

    # pylint: disable=too-many-branches
    def _migrate_db(self):
        super()._migrate_db()
        if self.db_schema_version < 1:
            self._update_schema_version_1()
        if self.db_schema_version < 2:
            self._update_schema_version_2()
        if self.db_schema_version < 3:
            self._update_schema_version_3()
        if self.db_schema_version < 4:
            self._update_schema_version_4()
        if self.db_schema_version < 5:
            self._update_schema_version_5()
        if self.db_schema_version < 6:
            self._update_schema_version_6()
        if self.db_schema_version < 7:
            self._update_schema_version_7()
        if self.db_schema_version < 8:
            self._update_schema_version_8()
        if self.db_schema_version < 9:
            self._update_schema_version_9()
        if self.db_schema_version < 10:
            self._update_schema_version_10()
        if self.db_schema_version < 11:
            self._update_schema_version_11()
        if self.db_schema_version < 12:
            self._update_schema_version_12()
        if self.db_schema_version < 13:
            self._update_schema_version_13()
        if self.db_schema_version < 14:
            self._update_schema_version_14()
        if self.db_schema_version < 15:
            self._update_schema_version_15()
        if self.db_schema_version < 16:
            self._update_schema_version_16()
        if self.db_schema_version < 17:
            self._update_schema_version_17()
        if self.db_schema_version < 18:
            self._update_schema_version_18()
        if self.db_schema_version < 19:
            self._update_schema_version_19()
        if self.db_schema_version < 20:
            self._update_schema_version_20()
        if self.db_schema_version != 20:
            print(f'Upgrade failed, db_schema_version is {self.db_schema_version}')

    def _update_schema_version_1(self):
        print('upgrade to schema 1')
        try:
            preceding_charts = []
            for chart in self._get_all_dashboard():
                # Discard chart if does not comply with new or old structure
                if not chart.get('name') or (
                        (not chart.get('type') or not chart.get('views')) and not chart.get('metric')):
                    continue
                try:
                    if chart.get('metric'):
                        preceding_charts.append(chart)
                    else:
                        preceding_charts.append({
                            'name': chart['name'],
                            'metric': chart['type'],
                            'view': 'pie' if chart['type'] == 'intersect' else 'histogram',
                            'config': {
                                'entity': chart['views'][0]['module'],
                                'base': chart['views'][0]['name'],
                                'intersecting': [x['name'] for x in chart['views'][1:]]
                            } if chart['type'] == 'intersect' else {
                                'views': chart['views']
                            }
                        })
                except Exception as e:
                    print(f'Could not upgrade chart {chart["name"]}. Details: {e}')
            self._replace_all_dashboard(preceding_charts)
            self.db_schema_version = 1
        except Exception as e:
            print(f'Could not upgrade gui db to version 1. Details: {e}')

    def _get_all_dashboard(self):
        return self.db.get_collection(self.plugin_name, DASHBOARD_COLLECTION).find({})

    def _replace_all_dashboard(self, dashboard_list):
        dashboard = self.db.get_collection(self.plugin_name, DASHBOARD_COLLECTION)
        dashboard.delete_many({})
        if len(dashboard_list) > 0:
            dashboard.insert(dashboard_list)

    def __perform_schema_2(self):
        """
        (1) Delete all fake users that aren't admin
        (2) User permissions were added
        (3) 'source' was added - where did the user come from?
        (4) API Key is now on a per user basis
        """
        users_collection = self.db.get_collection(self.plugin_name, 'users')

        # (1) delete all nonadmin users
        users_collection.delete_many(
            {
                'user_name': {
                    '$ne': 'admin'
                }
            })

        # (4) fetch the API key/secret from DB
        api_keys_collection = self.db.get_collection(self.plugin_name, 'api_keys')
        api_data = api_keys_collection.find_one({})
        if not api_data:
            print('No API Key, GUI is new or really old')
            api_data = {
                'api_key': secrets.token_urlsafe(),
                'api_secret': secrets.token_urlsafe()
            }

        # We assume we only have one "regular" user because the system didn't allow multiple users so far
        # (2) - Add max permissions to the user
        # (3) - Mark it as 'internal' - i.e. not from LDAP, etc
        # (4) - Add the API key and secret
        users_collection.update_one(
            {
                'user_name': 'admin'
            },
            {
                '$set': {
                    'permissions': {},
                    'admin': True,
                    'source': 'internal',
                    'api_key': api_data['api_key'],
                    'api_secret': api_data['api_secret']
                }
            }
        )

    def _update_schema_version_2(self):
        """
        See __perform_schema_2 for implementation
        :return:
        """
        print('upgrade to schema 2')
        try:
            self.__perform_schema_2()
        except Exception as e:
            print(f'Exception while upgrading gui db to version 2. Details: {e}')

        self.db_schema_version = 2

    def _update_schema_version_3(self):
        """
        This upgrade adapts the configuration of the 'timeline' chart to have a range that could be absolute dates,
        or a period relative to the view time, instead of the current datefrom and dateto

        :return:
        """
        print('upgrade to schema 3')
        try:
            preceding_charts = []
            for chart in self._get_all_dashboard():
                try:
                    # Chart defined with a metric other than timeline or already in new structure, can be added as is
                    if chart.get('metric', '') != 'timeline' or not chart.get('config') or chart['config'].get('range'):
                        preceding_charts.append(chart)
                    else:
                        preceding_charts.append({
                            'metric': chart['metric'],
                            'view': chart['view'],
                            'name': chart['name'],
                            'config': {
                                'views': chart['config']['views'],
                                'timeframe': {
                                    'type': 'absolute',
                                    'from': chart['config']['datefrom'],
                                    'to': chart['config']['dateto']
                                }
                            }
                        })
                except Exception as e:
                    print(f'Could not upgrade chart {chart["name"]}. Details: {e}')
            self._replace_all_dashboard(preceding_charts)
            self.db_schema_version = 3
        except Exception as e:
            print(f'Exception while upgrading gui db to version 3. Details: {e}')

    def _update_schema_version_4(self):
        print('upgrade to schema 4')
        try:
            # Fix Restricted User Role - Change permissions to Restricted
            permissions = {
                p.name: PermissionLevel.Restricted.name for p in PermissionType
            }
            permissions[PermissionType.Dashboard.name] = PermissionLevel.ReadOnly.name
            self.db.get_collection(GUI_PLUGIN_NAME, ROLES_COLLECTION).update_one({
                'name': PREDEFINED_ROLE_RESTRICTED
            }, {
                '$set': {
                    'permissions': permissions
                }
            })

            # Fix the Google Login Settings - Rename 'client_id' field to 'client'
            config_match = {
                'config_name': CONFIG_CONFIG
            }
            current_config = self.db.get_collection(
                GUI_PLUGIN_NAME, CONFIGURABLE_CONFIGS_COLLECTION).find_one(config_match)
            if current_config:
                current_config_google = current_config['config']['google_login_settings']
                if current_config_google.get('client_id'):
                    current_config_google['client'] = current_config_google['client_id']
                    del current_config_google['client_id']
                    self.db.get_collection(GUI_PLUGIN_NAME, CONFIGURABLE_CONFIGS_COLLECTION).replace_one(
                        config_match, current_config)

            self.db_schema_version = 4
        except Exception as e:
            print(f'Exception while upgrading gui db to version 4. Details: {e}')

    def _update_schema_version_5(self):
        print('upgrade to schema 5')
        try:
            # Change all labels not by GUI to be by GUI
            def change_for_collection(col):
                col.update_many(
                    filter={
                        'tags': {
                            '$elemMatch': {
                                '$and': [
                                    {
                                        'type': 'label'
                                    },
                                    {
                                        PLUGIN_NAME: {
                                            '$ne': GUI_PLUGIN_NAME
                                        }
                                    }
                                ]
                            }
                        }
                    },
                    update={
                        '$set': {
                            f'tags.$[i].{PLUGIN_NAME}': GUI_PLUGIN_NAME,
                            f'tags.$[i].{PLUGIN_UNIQUE_NAME}': GUI_PLUGIN_NAME
                        }
                    },
                    array_filters=[
                        {
                            '$and': [
                                {
                                    f'i.{PLUGIN_NAME}': {
                                        '$ne': GUI_PLUGIN_NAME
                                    }
                                },
                                {
                                    'i.type': 'label'
                                }
                            ]
                        }
                    ]
                )

            change_for_collection(self.db.get_collection(AGGREGATOR_PLUGIN_NAME, 'devices_db'))
            change_for_collection(self.db.get_collection(AGGREGATOR_PLUGIN_NAME, 'users_db'))

            self.db_schema_version = 5
        except Exception as e:
            print(f'Exception while upgrading gui db to version 5. Details: {e}')

    def _update_schema_version_6(self):
        print('upgrade to schema 6')
        try:
            # Fix the Okta Login Settings - Rename 'gui_url' field to 'gui2_url'
            config_match = {
                'config_name': CONFIG_CONFIG
            }
            current_config = self.db.get_collection(
                GUI_PLUGIN_NAME, CONFIGURABLE_CONFIGS_COLLECTION).find_one(config_match)
            if current_config:
                current_config_okta = current_config['config']['okta_login_settings']
                if current_config_okta.get('gui_url'):
                    current_config_okta['gui2_url'] = current_config_okta['gui_url']
                    del current_config_okta['gui_url']
                    self.db.get_collection(GUI_PLUGIN_NAME, CONFIGURABLE_CONFIGS_COLLECTION).replace_one(
                        config_match, current_config)
            self.db_schema_version = 6
        except Exception as e:
            print(f'Exception while upgrading gui db to version 6. Details: {e}')

    def _update_schema_version_7(self):
        print('upgrade to schema 7')
        try:
            # If Instances screen default doesn't exist add it with Resticted default.
            self.db.get_collection(GUI_PLUGIN_NAME, ROLES_COLLECTION).update_many(
                {f'permissions.{PermissionType.Instances.name}': {'$exists': False}},
                {'$set': {f'permissions.{PermissionType.Instances.name}': PermissionLevel.Restricted.name}})

            # Update Admin role with ReadWrite
            self.db.get_collection(GUI_PLUGIN_NAME, ROLES_COLLECTION).find_one_and_update(
                {'name': PREDEFINED_ROLE_ADMIN},
                {'$set': {f'permissions.{PermissionType.Instances.name}': PermissionLevel.ReadWrite.name}})
            self.db_schema_version = 7
        except Exception as e:
            print(f'Exception while upgrading gui db to version 7. Details: {e}')

    def _update_schema_version_8(self):
        print('upgrade to schema 8')
        try:
            # If Instances screen default doesn't exist add it with Resticted default.
            self.db.get_collection(GUI_PLUGIN_NAME, USERS_COLLECTION).update_many(
                {f'permissions.{PermissionType.Instances.name}': {'$exists': False},
                 '$or': [{'admin': False}, {'admin': {'$exists': False}}],
                 'role_name': {'$ne': PREDEFINED_ROLE_ADMIN}},
                {'$set': {f'permissions.{PermissionType.Instances.name}': PermissionLevel.Restricted.name}})

            # Update Admin role with ReadWrite
            self.db.get_collection(GUI_PLUGIN_NAME, USERS_COLLECTION).update_many(
                {f'permissions.{PermissionType.Instances.name}': {'$exists': False},
                 '$or': [{'admin': False}, {'admin': {'$exists': False}}],
                 'role_name': PREDEFINED_ROLE_ADMIN},
                {'$set': {f'permissions.{PermissionType.Instances.name}': PermissionLevel.ReadWrite.name}})
            self.db_schema_version = 8
        except Exception as e:
            print(f'Exception while upgrading gui db to version 8. Details: {e}')

    def _update_schema_version_9(self):
        print('Upgrade to schema 9')
        try:

            # All non-admin Users - change any Alerts screen permissions to be under Enforcements screen
            users_col = self.db.get_collection(GUI_PLUGIN_NAME, USERS_COLLECTION)
            regular_users = users_col.find({
                '$or': [{
                    'admin': False
                }, {
                    'admin': {'$exists': False}
                }]
            })
            for user in regular_users:
                permissions = user['permissions']
                if user.get('role_name') == PREDEFINED_ROLE_ADMIN:
                    default_perm = PermissionLevel.ReadWrite.name
                else:
                    default_perm = PermissionLevel.Restricted.name
                permissions[PermissionType.Enforcements.name] = permissions.get('Alerts', default_perm)
                if 'Alerts' in permissions:
                    del permissions['Alerts']
                users_col.update_one({
                    '_id': user['_id']
                }, {
                    '$set': {
                        'permissions': permissions
                    }
                })

            # Roles - change any Alerts screen permissions to be under Enforcements screen
            roles_col = self.db.get_collection(GUI_PLUGIN_NAME, ROLES_COLLECTION)
            for role in roles_col.find({}):
                permissions = role['permissions']
                if role['name'] == PREDEFINED_ROLE_ADMIN:
                    default_perm = PermissionLevel.ReadWrite.name
                elif role['name'] == PREDEFINED_ROLE_READONLY:
                    default_perm = PermissionLevel.ReadOnly.name
                else:
                    default_perm = PermissionLevel.Restricted.name
                permissions[PermissionType.Enforcements.name] = permissions.get('Alerts', default_perm)
                if 'Alerts' in permissions:
                    del permissions['Alerts']
                roles_col.update_one({
                    '_id': role['_id']
                }, {
                    '$set': {
                        'permissions': permissions
                    }
                })
            self.db_schema_version = 9
        except Exception as e:
            print(f'Exception while upgrading gui db to version 9. Details: {e}')

    def _update_schema_version_10(self):
        print('Upgrade to schema 10')
        self._update_default_locked_actions(['tenable_io_add_ips_to_target_group'])
        self.db_schema_version = 10

    def _update_schema_version_11(self):
        print('Upgrade to schema 11')
        try:
            self._migrate_default_report()
            self.db_schema_version = 11
        except Exception as e:
            print(f'Exception while upgrading gui db to version 11. Details: {e}')

    def _update_schema_version_12(self):
        print('Upgrade to schema 12')
        try:
            self._update_default_locked_actions(['sentinelone_initiate_scan_action'])
            dashboard_spaces_collection = self.db.get_collection(self.plugin_name, DASHBOARD_SPACES_COLLECTION)
            dashboard_spaces_collection.insert_many([{
                'name': DASHBOARD_SPACE_DEFAULT,
                'type': DASHBOARD_SPACE_TYPE_DEFAULT
            }, {
                'name': DASHBOARD_SPACE_PERSONAL,
                'type': DASHBOARD_SPACE_TYPE_PERSONAL
            }])
            default_id = dashboard_spaces_collection.find_one({
                'name': DASHBOARD_SPACE_DEFAULT
            })['_id']
            self.db.get_collection(self.plugin_name, DASHBOARD_COLLECTION).update_many({}, {
                '$set': {
                    'space': default_id
                }
            })
            self.db_schema_version = 12
        except Exception as e:
            print(f'Exception while upgrading gui db to version 12. Details: {e}')

    def _update_schema_version_13(self):
        print('Upgrade to schema 13')
        try:
            self._update_default_locked_actions(['sentinelone_initiate_scan_action'])
            dashboard_spaces_collection = self.db.get_collection(self.plugin_name, DASHBOARD_SPACES_COLLECTION)
            replace_result = dashboard_spaces_collection.replace_one({
                'type': DASHBOARD_SPACE_TYPE_DEFAULT
            }, {
                'name': DASHBOARD_SPACE_DEFAULT,
                'type': DASHBOARD_SPACE_TYPE_DEFAULT
            }, upsert=True)
            dashboard_spaces_collection.replace_one({
                'type': DASHBOARD_SPACE_TYPE_PERSONAL
            }, {
                'name': DASHBOARD_SPACE_PERSONAL,
                'type': DASHBOARD_SPACE_TYPE_PERSONAL
            }, upsert=True)

            if replace_result.upserted_id:
                self.db.get_collection(self.plugin_name, DASHBOARD_COLLECTION).update_many({
                    'space': {
                        '$exists': False
                    }
                }, {
                    '$set': {
                        'space': replace_result.upserted_id
                    }
                })
            self.db_schema_version = 13
        except Exception as e:
            print(f'Exception while upgrading gui db to version 13. Details: {e}')

    def _update_schema_version_14(self):
        """
        For version 2.7, update all history views' pageSize to 20
        """
        print('Upgrade to schema 14')
        try:
            self._entity_views_map[EntityType.Users].update_many({
                'query_type': 'history'
            }, {
                '$set': {
                    'view.pageSize': 20
                }
            })
            self._entity_views_map[EntityType.Devices].update_many({
                'query_type': 'history'
            }, {
                '$set': {
                    'view.pageSize': 20
                }
            })
            self.db_schema_version = 14
        except Exception as e:
            print(f'Exception while upgrading gui db to version 14. Details: {e}')

    def _update_schema_version_15(self):
        print('Upgrade to schema 15')
        self._update_default_locked_actions(['tenable_io_create_asset'])
        self.db_schema_version = 15

    def _update_schema_version_16(self):
        """
        For version 2.8, remove pageSize and page from all saved views
        """
        print('Upgrade to schema 16')
        try:
            for entity_type in EntityType:
                self._entity_views_map[entity_type].update_many({
                    'query_type': 'saved'
                }, {
                    '$set': {
                        'view.pageSize': 20,
                        'view.page': 0
                    }
                })
            self.db_schema_version = 16
        except Exception as e:
            print(f'Exception while upgrading gui db to version 15. Details: {e}')

    def _update_schema_version_17(self):
        """
        For version 2.10, remove duplicated spaces
        """
        print('Upgrade to schema 17')
        try:
            self._remove_unused_spaces(DASHBOARD_SPACE_TYPE_DEFAULT)
            self._remove_unused_spaces(DASHBOARD_SPACE_TYPE_PERSONAL)

            self.db_schema_version = 17
        except Exception as e:
            print(f'Exception while upgrading gui db to version 17. Details: {e}')

    def _remove_unused_spaces(self, spaces_type):
        dashboard_spaces_collection = self.db.get_collection(self.plugin_name, DASHBOARD_SPACES_COLLECTION)
        dashboards = dashboard_spaces_collection.find({
            'type': spaces_type
        })
        if dashboards.count() > 1:
            indexes_to_delete = [space.get('_id') for space in dashboards[1:]]
            dashboard_spaces_collection.delete_many({'_id': {'$in': indexes_to_delete}})

    def _update_schema_version_18(self):
        """
        For version 2.10, fix order of fields for all saved queries
        """
        print('Upgrade to schema 18')
        try:
            fields_order = {
                EntityType.Devices: [
                    'adapters', 'specific_data.data.name', 'specific_data.data.hostname',
                    'specific_data.data.last_seen', 'specific_data.data.network_interfaces.mac',
                    'specific_data.data.network_interfaces.ips', 'specific_data.data.os.type'
                ],
                EntityType.Users: [
                    'adapters', 'specific_data.data.image', 'specific_data.data.username', 'specific_data.data.domain',
                    'specific_data.data.is_admin', 'specific_data.data.last_seen'
                ]
            }
            for entity_type in EntityType:
                views_collection = self._entity_views_map[entity_type]
                saved_views = views_collection.find({
                    'query_type': 'saved'
                })
                for view_doc in saved_views:
                    original_fields = view_doc.get('view', {}).get('fields', [])
                    reordered_fields = []
                    for field in fields_order[entity_type]:
                        try:
                            original_fields.remove(field)
                        except ValueError:
                            # Field from definition is not in saved fields - nothing to do
                            continue
                        reordered_fields.append(field)

                    reordered_fields.extend([field for field in original_fields if 'specific_data.data' in field])
                    if 'labels' in original_fields:
                        reordered_fields.append('labels')
                    reordered_fields.extend([field for field in original_fields if 'adapters_data.' in field])
                    views_collection.update_one({
                        '_id': view_doc['_id']
                    }, {
                        '$set': {
                            'view.fields': reordered_fields
                        }
                    })

            self.db_schema_version = 18
        except Exception as e:
            print(f'Exception while upgrading gui db to version 18. Details: {e}')

    def _update_schema_version_19(self):
        """
        For version 2.11, add Getting Started With Axonius collection to db.
        """
        print('Upgrade to schema 19')
        try:
            self.db.get_collection(GUI_PLUGIN_NAME, 'getting_started').insert_one(
                {
                    'settings': {
                        'autoOpen': True,
                        'interactive': False
                    },
                    'milestones': [
                        {
                            'name': 'connect_adapters',
                            'title': 'Connect adapters',
                            'completed': False,
                            'completionDate': None,
                            'path': '/adapters',
                            'link': 'https://docs.axonius.com/docs/connect-adapters',
                            'description': 'You can collect and correlate information '
                                           'about your assets by using Axonius\' '
                                           'adapters, which integrate with a wide array of security and IT '
                                           'management solutions.\n\nGo to the Adapters screen to connect at '
                                           'least three adapters to fetch data for your devices '
                                           'and users from at least three different sources.'
                        },
                        {
                            'name': 'examine_device',
                            'title': 'Examine a device profile',
                            'completed': False,
                            'completionDate': None,
                            'path': '/devices',
                            'link': 'https://docs.axonius.com/docs/examine-a-device-profile',
                            'description': 'You can examine the details about your devices by looking '
                                           'at their profiles, which displays the data that Axonius collected '
                                           'and correlated from multiple sources.\n\nUse the Devices screen or the '
                                           'search bar on Axonius Dashboard to search for a device '
                                           'and examine its profile.'
                        },
                        {
                            'name': 'query_saved',
                            'title': 'Save a query',
                            'completed': False,
                            'path': '/devices',
                            'link': 'https://docs.axonius.com/docs/save-a-query',
                            'description': 'You can identify security gaps by running and '
                                           'saving a query about your assets.\n\nUse the Query '
                                           'Wizard on the Devices screen to create a query, '
                                           'then save it so you can easily access it in the future.'
                        },
                        {
                            'name': 'device_tag',
                            'title': 'Tag a device',
                            'completed': False,
                            'completionDate': None,
                            'path': '/devices',
                            'link': 'https://docs.axonius.com/docs/tag-a-device',
                            'description': 'You can tag a single asset or a group of '
                                           'assets that share common characteristics. Use tags to assign '
                                           'context to your assets for granular filters and queries.\n\n '
                                           'Go to the Devices screen, tag a few devices with shared '
                                           'characteristics, then issue a query that includes the new tag.'
                        },
                        {
                            'name': 'enforcement_executed',
                            'title': 'Create and execute an enforcement set',
                            'completed': False,
                            'completionDate': None,
                            'path': '/enforcements',
                            'link': 'https://docs.axonius.com/docs/create-and-execute-an-enforcement-set',
                            'description': 'You can take action on the identified security gaps '
                                           'by defining Enforcement Sets in the Axonius Security Policy '
                                           'Enforcement Center.\n\nGo to the Enforcement Center screen '
                                           'to create and execute an Enforcement Set.'
                        },
                        {
                            'name': 'dashboard_created',
                            'title': 'Create a dashboard chart',
                            'completed': False,
                            'completionDate': None,
                            'path': '/',
                            'link': 'https://docs.axonius.com/docs/create-a-dashboard-chart',
                            'description': 'You can customize the Axonius Dashboard with charts that '
                                           'track the relevant metrics and show immediate insights based '
                                           'on your saved queries.\n\nGo to the Axonius Dashboard, and add '
                                           'a chart to a new custom space.'
                        },
                        {
                            'name': 'report_generated',
                            'title': 'Generate a report',
                            'completed': False,
                            'completionDate': None,
                            'path': '/reports',
                            'link': 'https://docs.axonius.com/docs/generate-a-report',
                            'description': 'You can customize the Axonius Dashboard with charts '
                                           'that track the relevant '
                                           'metrics and show immediate insights based on your saved queries.\n\n '
                                           'Go to the Axonius Dashboard, and add a chart to any '
                                           'of the default spaces or to a '
                                           'new custom space.'
                        }
                    ]
                }
            )

            self.db_schema_version = 19
        except Exception as e:
            print(f'Exception while upgrading gui db to version 19. Details: {e}')

    def _update_schema_version_20(self):
        """
        For version 2.11, add in every space a new attribute "panels_order" of type array.
        for each space this array should respectively holds the order of all the existing panels.
        This is requested as part of the Drag & Drop features in order to allow upgragded systems
        to benefits from the new feature
        """
        panels_order_by_space = defaultdict(list)
        try:
            dashboard_spaces_collection = self.db.get_collection(self.plugin_name, DASHBOARD_SPACES_COLLECTION)
            print('Upgrade to schema 20')

            for dashboard in self.db.get_collection(self.plugin_name, DASHBOARD_COLLECTION).find(
                    filter=filter_archived(),
                    projection={
                        '_id': True,
                        'space': True
                    }):
                try:
                    panels_order_by_space[dashboard['space']].append(str(dashboard['_id']))
                except Exception as e:
                    pass

            for space_id, dashboard_ids in panels_order_by_space.items():
                try:
                    dashboard_spaces_collection.update_one({
                        '_id': space_id
                    }, {
                        '$push': {
                            'panels_order': {'$each': dashboard_ids}
                        }
                    })

                except Exception as e:
                    logger.exception(f'Failed adding panels_order {dashboard_ids} to space {str(space_id)}')

            self.db_schema_version = 20
        except Exception as e:
            print(f'Exception while upgrading gui db to version 20. Details: {e}')

    def _update_default_locked_actions(self, new_actions):
        """
        Update the config record that holds the FeatureFlags setting, adding received new_actions to it's list of
        locked_actions
        """
        self.db.get_collection(GUI_PLUGIN_NAME, CONFIGURABLE_CONFIGS_COLLECTION).update_one({
            'config_name': FEATURE_FLAGS_CONFIG
        }, {
            '$addToSet': {
                'config.locked_actions': {
                    '$each': new_actions
                }
            }
        })

    @property
    def exposed_ports(self):
        """
        :return: list of pairs (exposed_port, inner_port)
        """
        # The only container that listens to 80 and redirects to 80 is the gui, to allow http to https redirection.
        ports = super().exposed_ports
        if not self._system_config.get('https-only'):
            ports += [(80, 80)]
        return ports

    @property
    def volumes_override(self):
        # Creating a settings dir outside of cortex (on production machines
        # this will be /home/ubuntu/.axonius_settings) for login marker and weave encryption key.
        settings_path = os.path.abspath(os.path.join(self.cortex_root_dir, AXONIUS_SETTINGS_DIR_NAME))
        os.makedirs(settings_path, exist_ok=True)
        container_settings_dir_path = os.path.join('/home/axonius/', AXONIUS_SETTINGS_DIR_NAME)
        volumes = [f'{settings_path}:{container_settings_dir_path}']

        # GUI supports development, but to use, you have to build your *local* node modules
        if self.is_dev:
            volumes.extend(super().volumes_override)
            return volumes
        libs = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'axonius-libs', 'src', 'libs'))
        volumes.extend([f'{libs}:{LIBS_PATH.as_posix()}:ro'])

        # extend volumes by mapping specifically each python file, to be able to debug much better.
        volumes.extend([f'{self.service_dir}/{fn}:/home/axonius/app/{self.package_name}/{fn}:ro'
                        for fn in os.listdir(self.service_dir) if fn.endswith('.py')])
        volumes.extend([f'{self.service_dir}/gui_logic/{fn}:/home/axonius/app/{self.package_name}/gui_logic/{fn}:ro'
                        for fn in os.listdir(f'{self.service_dir}/gui_logic') if fn.endswith('.py')])

        volumes.extend([f'{self.service_dir}/frontend/src/constants/plugin_meta.js:'
                        f'/home/axonius/app/{self.package_name}/frontend/src/constants/plugin_meta.js:ro'])

        return volumes

    # I don't want to change all dockerfiles
    # pylint: disable=W0221
    def get_dockerfile(self, *args, docker_internal_env_vars=None, **kwargs):

        build_command = '' if self.is_dev else f'''
# Compile npm, assuming we have it from axonius-libs
RUN cd ./gui/frontend/ && npm run build
'''
        install_command = '' if self.is_dev else '''
# Prepare build packages
COPY ./frontend/package.json ./gui/frontend/package.json
COPY ./frontend/package-lock.json ./gui/frontend/package-lock.json
RUN cd ./gui/frontend && npm set progress=false && npm install
# This must be the first thing so subsequent rebuilds will use this cache image layer
# Docker builds the image from the dockerfile in stages [called layers], each layer is cached and reused if not changed
# [since the line created it + the layer before it has not changed]
# So as long as package.json file is not changed, installation will not be run again
'''

        return ('''
FROM axonius/axonius-libs

# Set the working directory to /app
WORKDIR /home/axonius/app
''' + install_command + '''
# Copy the current directory contents into the container at /app
COPY ./ ./gui/
COPY /config/nginx_conf.d/ /home/axonius/config/nginx_conf.d/
RUN cd /home/axonius && mkdir axonius-libs && mkdir axonius-libs/src && cd axonius-libs/src/ && ln -s ../../libs/ .
''' + build_command)[1:]

    def __del__(self):
        self._session.close()

    def get_devices(self, *vargs, **kwargs):
        return self.get('devices', session=self._session, *vargs, **kwargs)

    def delete_devices(self, internal_axon_ids, *vargs, **kwargs):
        return self.delete('devices', session=self._session, data={
            'ids': internal_axon_ids, 'include': True
        }, *vargs, **kwargs)

    def get_devices_count(self, *vargs, **kwargs):
        return self.get('devices/count', session=self._session, *vargs, **kwargs)

    def get_users(self, *vargs, **kwargs):
        return self.get('users', session=self._session, *vargs, **kwargs)

    def get_users_count(self, *vargs, **kwargs):
        return self.get('users/count', session=self._session, *vargs, **kwargs)

    def delete_users(self, internal_axon_ids, *vargs, **kwargs):
        return self.delete('users', session=self._session, data={
            'ids': internal_axon_ids, 'include': True
        }, *vargs, **kwargs)

    def get_device_by_id(self, id_, *vargs, **kwargs):
        return self.get('devices/{0}'.format(id_), session=self._session, *vargs, **kwargs)

    def delete_client(self, adapter_unique_name, client_id, *vargs, **kwargs):
        return self.delete(f'adapters/{adapter_unique_name}/clients/{client_id}', session=self._session,
                           *vargs, **kwargs)

    def get_all_tags(self, *vargs, **kwargs):
        return self.get('tags', session=self._session, *vargs, **kwargs)

    def remove_labels_from_device(self, payload, *vargs, **kwargs):
        return self.delete('devices/labels', data=json.dumps(payload), session=self._session, *vargs,
                           **kwargs)

    def add_labels_to_device(self, payload, *vargs, **kwargs):
        return self.post('devices/labels', data=json.dumps(payload), session=self._session, *vargs, **kwargs)

    def activate_plugin_job(self, plugin_id, *vargs, **kwargs):
        return self.post(f'plugins/{plugin_id}/start', *vargs, **kwargs)

    def deactivate_plugin_job(self, plugin_id, *vargs, **kwargs):
        return self.post(f'plugins/{plugin_id}/stop', *vargs, **kwargs)

    def get_api_key(self):
        return self.get('api_key', session=self._session).json()

    def renew_api_key(self):
        return self.post('api_key', session=self._session).json()

    def get_queries(self):
        self.get('trigger_watches', api_key=self.api_key, session=self._session)

    def login_user(self, credentials):
        return self.post('login', data=json.dumps(credentials), session=self._session)

    def logout_user(self):
        return self.get('logout', session=self._session)

    def analytics(self):
        return self.get('analytics').content

    def troubleshooting(self):
        return self.get('troubleshooting').content

    def provision(self):
        return self.get('provision').content

    def get_api_version(self, *vargs, **kwargs):
        return self.get(f'api', *vargs, **kwargs).json()

    def get_api_devices(self, *vargs, **kwargs):
        return self.get(f'V{self.get_api_version()}/devices', *vargs, **kwargs)

    def get_api_device_by_id(self, device_id, *vargs, **kwargs):
        return self.get(f'V{self.get_api_version()}/devices/{device_id}', *vargs, **kwargs)

    def get_api_users(self, *vargs, **kwargs):
        return self.get(f'V{self.get_api_version()}/users', *vargs, **kwargs)

    def get_api_user_by_id(self, user_id, *vargs, **kwargs):
        return self.get(f'V{self.get_api_version()}/users/{user_id}', *vargs, **kwargs)

    def get_api_reports(self, *vargs, **kwargs):
        return self.get(f'V{self.get_api_version()}/reports', *vargs, **kwargs)

    def get_api_report_by_id(self, report_id, *vargs, **kwargs):
        return self.get(f'V{self.get_api_version()}/reports/{report_id}', *vargs, **kwargs)

    def delete_api_report_by_id(self, report_id, *vargs, **kwargs):
        return self.delete(f'V{self.get_api_version()}/reports/{report_id}', *vargs, **kwargs)

    def put_api_report(self, report_data, *vargs, **kwargs):
        return self.put(f'V{self.get_api_version()}/reports', report_data, *vargs, **kwargs)

    def get_saml_settings(self):
        return self.get_configurable_config(CONFIG_CONFIG)

    def get_feature_flags(self):
        return self.get_configurable_config(FEATURE_FLAGS_CONFIG)

    def get_maintenance_flags(self):
        flags = self.db.get_collection(self.plugin_name, GUI_SYSTEM_CONFIG_COLLECTION).find_one(MAINTENANCE_FILTER)
        del flags['_id']
        return flags

    def set_maintenance_flags(self, flags):
        self.db.get_collection(self.plugin_name, GUI_SYSTEM_CONFIG_COLLECTION).update_one(MAINTENANCE_FILTER, {
            '$set': flags
        })

    def get_signup_status(self):
        return self.get(Signup.SignupEndpoint).json()[Signup.SignupField]

    def get_signup_collection(self):
        return self.db.client[self.plugin_name][Signup.SignupCollection]

    def get_report_pdf(self, report_id, *vargs, **kwargs):
        return self.get(f'export_report/{report_id}', session=self._session, *vargs, **kwargs)

    def get_saved_views(self):

        user_view = self.db.get_collection('gui', 'user_views')
        device_view = self.db.get_collection('gui', 'device_views')

        entity_query_views_db_map = {
            EntityType.Users: user_view,
            EntityType.Devices: device_view,
        }

        saved_views_filter = filter_archived({
            'query_type': 'saved',
            '$or': [
                {
                    'predefined': False
                },
                {
                    'predefined': {
                        '$exists': False
                    }
                }
            ]
        })
        views_data = []
        for entity in EntityType:
            saved_views = entity_query_views_db_map[entity].find(saved_views_filter)
            for view_doc in saved_views:
                view = view_doc.get('view')
                if view:
                    views_data.append({
                        'entity': entity.value,
                        'name': view_doc.get('name')
                    })

        return views_data

    def _upsert_report_config(self, name, report):
        reports_collection = self.db.get_collection('gui', 'reports_config')

        new_report = {**report}

        result = reports_collection.replace_one({'name': name},
                                                new_report, upsert=True)
        return result

    def _migrate_default_report(self):
        exec_reports_settings_collection = self.db.get_collection('gui', 'exec_reports_settings')
        reports_collection = self.db.get_collection('gui', 'reports_config')

        default_report = exec_reports_settings_collection.find_one()
        default_report_config = reports_collection.find_one()
        views = self.get_saved_views()
        if default_report:
            mail_properties = dict(mailSubject='', emailList=[], emailListCC=[])
            mail_properties['emailList'] = default_report.get('recipients')
            mail_properties['mailSubject'] = EXEC_REPORT_TITLE
            include_saved_views = 'IncludeSavedViews' if len(views) > 0 else None
            new_report = {
                'name': EXEC_REPORT_TITLE,
                'include_saved_views': include_saved_views,
                'include_dashboard': 'IncludeDashboard',
                'add_scheduling': 'AddScheduling',
                'period': default_report.get('period'),
                'mail_properties': mail_properties,
                'views': views
            }
            self._upsert_report_config(EXEC_REPORT_TITLE, new_report)
            exec_reports_settings_collection.delete_one({'_id': default_report.get('_id')})
            reports_collection.delete_one({'_id': default_report_config.get('_id')})
