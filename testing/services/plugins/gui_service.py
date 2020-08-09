import json
import logging
import os
import re
import secrets
from collections import defaultdict
from datetime import datetime
from typing import List
from funcy import chunks
from bson import ObjectId
import requests
from pymongo import UpdateOne

from axonius.consts.gui_consts import (CONFIG_CONFIG, ROLES_COLLECTION, USERS_COLLECTION, USERS_CONFIG_COLLECTION,
                                       DASHBOARD_COLLECTION, DASHBOARD_SPACES_COLLECTION,
                                       DASHBOARD_SPACE_DEFAULT, DASHBOARD_SPACE_PERSONAL,
                                       DASHBOARD_SPACE_TYPE_DEFAULT, DASHBOARD_SPACE_TYPE_PERSONAL,
                                       PREDEFINED_ROLE_ADMIN, PREDEFINED_ROLE_RESTRICTED, PREDEFINED_ROLE_READONLY,
                                       PREDEFINED_ROLE_VIEWER, PREDEFINED_ROLE_OWNER, FEATURE_FLAGS_CONFIG, Signup,
                                       EXEC_REPORT_TITLE, LAST_UPDATED_FIELD, UPDATED_BY_FIELD,
                                       PREDEFINED_FIELD, IS_AXONIUS_ROLE, PREDEFINED_ROLE_RESTRICTED_USER,
                                       PRIVATE_FIELD, IDENTITY_PROVIDERS_CONFIG, DEFAULT_ROLE_ID, ROLE_ASSIGNMENT_RULES,
                                       EVALUATE_ROLE_ASSIGNMENT_ON, NEW_USERS_ONLY, ASSIGNMENT_RULE_ARRAY)
from axonius.consts.plugin_consts import (AGGREGATOR_PLUGIN_NAME,
                                          AXONIUS_SETTINGS_DIR_NAME,
                                          DEVICE_VIEWS,
                                          USER_VIEWS,
                                          GUI_PLUGIN_NAME,
                                          PLUGIN_NAME,
                                          PLUGIN_UNIQUE_NAME,
                                          MAINTENANCE_TYPE,
                                          GUI_SYSTEM_CONFIG_COLLECTION,
                                          LIBS_PATH,
                                          AXONIUS_USER_NAME,
                                          ADMIN_USER_NAME,
                                          CONFIGURABLE_CONFIGS_LEGACY_COLLECTION)
from axonius.db_migrations import db_migration
from axonius.entities import EntityType
from axonius.utils.gui_helpers import (PermissionLevel, PermissionType,
                                       deserialize_db_permissions as old_deserialize_db_permissions)
from axonius.utils.mongo_retries import mongo_retry
from axonius.utils.permissions_helper import (PermissionCategory, PermissionAction,
                                              get_admin_permissions, get_permissions_structure,
                                              get_viewer_permissions, get_restricted_permissions,
                                              serialize_db_permissions)
from gui.logic.filter_utils import filter_archived
from services.plugin_service import PluginService
from services.system_service import SystemService
from services.updatable_service import UpdatablePluginMixin

logger = logging.getLogger(f'axonius.{__name__}')
MAINTENANCE_FILTER = {'type': MAINTENANCE_TYPE}


class GuiService(PluginService, SystemService, UpdatablePluginMixin):
    def __init__(self):
        super().__init__('gui')
        self._session = requests.Session()
        self.override_exposed_port = True
        local_npm = os.path.join(self.service_dir, 'frontend', 'node_modules')
        local_dist = os.path.join(self.service_dir, 'frontend', 'dist')
        self.is_dev = os.path.isdir(local_npm) and os.path.isdir(local_dist)

    # pylint: disable=too-many-branches,too-many-lines,too-many-locals
    def _migrate_db(self):
        super()._migrate_db()
        self._run_all_migrations()

    @db_migration(raise_on_failure=False)
    def _update_schema_version_1(self):
        print('upgrade to schema 1')
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

    @db_migration(raise_on_failure=False)
    def _update_schema_version_2(self):
        """
        See __perform_schema_2 for implementation
        :return:
        """
        print('upgrade to schema 2')
        self.__perform_schema_2()

    @db_migration(raise_on_failure=False)
    def _update_schema_version_3(self):
        """
        This upgrade adapts the configuration of the 'timeline' chart to have a range that could be absolute dates,
        or a period relative to the view time, instead of the current datefrom and dateto

        :return:
        """
        print('upgrade to schema 3')
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

    @db_migration(raise_on_failure=False)
    def _update_schema_version_4(self):
        print('upgrade to schema 4')
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
            GUI_PLUGIN_NAME, CONFIGURABLE_CONFIGS_LEGACY_COLLECTION).find_one(config_match)
        if current_config:
            current_config_google = current_config['config']['google_login_settings']
            if current_config_google.get('client_id'):
                current_config_google['client'] = current_config_google['client_id']
                del current_config_google['client_id']
                self.db.get_collection(GUI_PLUGIN_NAME, CONFIGURABLE_CONFIGS_LEGACY_COLLECTION).replace_one(
                    config_match, current_config)

    @db_migration(raise_on_failure=False)
    def _update_schema_version_5(self):
        print('upgrade to schema 5')

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

    @db_migration(raise_on_failure=False)
    def _update_schema_version_6(self):
        print('upgrade to schema 6')
        # Fix the Okta Login Settings - Rename 'gui_url' field to 'gui2_url'
        config_match = {
            'config_name': CONFIG_CONFIG
        }
        current_config = self.db.get_collection(
            GUI_PLUGIN_NAME, CONFIGURABLE_CONFIGS_LEGACY_COLLECTION).find_one(config_match)
        if current_config:
            current_config_okta = current_config['config']['okta_login_settings']
            if current_config_okta.get('gui_url'):
                current_config_okta['gui2_url'] = current_config_okta['gui_url']
                del current_config_okta['gui_url']
                self.db.get_collection(GUI_PLUGIN_NAME, CONFIGURABLE_CONFIGS_LEGACY_COLLECTION).replace_one(
                    config_match, current_config)

    @db_migration(raise_on_failure=False)
    def _update_schema_version_7(self):
        print('upgrade to schema 7')
        # If Instances screen default doesn't exist add it with Resticted default.
        self.db.get_collection(GUI_PLUGIN_NAME, ROLES_COLLECTION).update_many(
            {f'permissions.{PermissionType.Instances.name}': {'$exists': False}},
            {'$set': {f'permissions.{PermissionType.Instances.name}': PermissionLevel.Restricted.name}})

        # Update Admin role with ReadWrite
        self.db.get_collection(GUI_PLUGIN_NAME, ROLES_COLLECTION).find_one_and_update(
            {'name': PREDEFINED_ROLE_ADMIN},
            {'$set': {f'permissions.{PermissionType.Instances.name}': PermissionLevel.ReadWrite.name}})

    @db_migration(raise_on_failure=False)
    def _update_schema_version_8(self):
        print('upgrade to schema 8')
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

    @db_migration(raise_on_failure=False)
    def _update_schema_version_9(self):
        print('Upgrade to schema 9')
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

    @db_migration(raise_on_failure=False)
    def _update_schema_version_10(self):
        print('Upgrade to schema 10')
        self._update_default_locked_actions_legacy(['tenable_io_add_ips_to_target_group'])

    @db_migration(raise_on_failure=False)
    def _update_schema_version_11(self):
        print('Upgrade to schema 11')
        self._migrate_default_report()

    @db_migration(raise_on_failure=False)
    def _update_schema_version_12(self):
        print('Upgrade to schema 12')
        self._update_default_locked_actions_legacy(['sentinelone_initiate_scan_action'])
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

    @db_migration(raise_on_failure=False)
    def _update_schema_version_13(self):
        print('Upgrade to schema 13')
        self._update_default_locked_actions_legacy(['sentinelone_initiate_scan_action'])
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

    @db_migration(raise_on_failure=False)
    def _update_schema_version_14(self):
        """
        For version 2.7, update all history views' pageSize to 20
        """
        print('Upgrade to schema 14')

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

    @db_migration(raise_on_failure=False)
    def _update_schema_version_15(self):
        print('Upgrade to schema 15')
        self._update_default_locked_actions_legacy(['tenable_io_create_asset'])

    @db_migration(raise_on_failure=False)
    def _update_schema_version_16(self):
        """
        For version 2.8, remove pageSize and page from all saved views
        """
        print('Upgrade to schema 16')
        for entity_type in EntityType:
            self._entity_views_map[entity_type].update_many({
                'query_type': 'saved'
            }, {
                '$set': {
                    'view.pageSize': 20,
                    'view.page': 0
                }
            })

    @db_migration(raise_on_failure=False)
    def _update_schema_version_17(self):
        """
        For version 2.10, remove duplicated spaces
        """
        print('Upgrade to schema 17')
        self._remove_unused_spaces(DASHBOARD_SPACE_TYPE_DEFAULT)
        self._remove_unused_spaces(DASHBOARD_SPACE_TYPE_PERSONAL)

    def _remove_unused_spaces(self, spaces_type):
        dashboard_spaces_collection = self.db.get_collection(self.plugin_name, DASHBOARD_SPACES_COLLECTION)
        dashboards = dashboard_spaces_collection.find({
            'type': spaces_type
        })
        if dashboards.count() > 1:
            indexes_to_delete = [space.get('_id') for space in dashboards[1:]]
            dashboard_spaces_collection.delete_many({'_id': {'$in': indexes_to_delete}})

    @db_migration(raise_on_failure=False)
    def _update_schema_version_18(self):
        """
        For version 2.10, fix order of fields for all saved queries
        """
        print('Upgrade to schema 18')
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

    @db_migration(raise_on_failure=False)
    def _update_schema_version_19(self):
        """
        For version 2.11, add Getting Started With Axonius collection to db.
        """
        print('Upgrade to schema 19')
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

    # pylint:disable=invalid-triple-quote
    @db_migration(raise_on_failure=False)
    def _update_schema_version_20(self):
        """
        For version 2.11, add in every space a new attribute "panels_order" of type array.
        for each space this array should respectively holds the order of all the existing panels.
        This is requested as part of the Drag & Drop features in order to allow upgragded systems
        to benefits from the new feature
        :return:
        """
        panels_order_by_space = defaultdict(list)
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

    @db_migration(raise_on_failure=False)
    def _update_schema_version_21(self):
        """
        For version 2.12, remove in every default saved_query of 'device_views' and 'user_views'
        the pageSize attribute under the view
        """
        print('Upgrade to schema 21')
        self.db.get_collection(GUI_PLUGIN_NAME, DEVICE_VIEWS).update_many({'view.pageSize': {'$exists': True}},
                                                                          {'$unset': {'view.pageSize': 20}})
        self.db.get_collection(GUI_PLUGIN_NAME, USER_VIEWS).update_many({'view.pageSize': {'$exists': True}},
                                                                        {'$unset': {'view.pageSize': 20}})

    @db_migration(raise_on_failure=False)
    def _update_schema_version_22(self):
        """
        For version 2.12, run the report periodic config migration
        """
        print('Upgrade to schema 22')
        self._migrate_report_periodic_config()

    # pylint: disable=R0201
    @db_migration(raise_on_failure=False)
    def _update_schema_version_23(self):
        return

    @db_migration(raise_on_failure=False)
    def _update_schema_version_24(self):
        """
        For version 2.13, sync updated_by and last_updated fields in Enforcements, Reports and Saved Views
        """
        print('Upgrade to schema 24')
        find_query = {
            'user_id': {
                '$type': 'objectId'
            }
        }
        hidden_user_id = self._get_hidden_user_id()
        if hidden_user_id:
            find_query['user_id']['$ne'] = hidden_user_id

        update_query = [{
            '$set': {
                UPDATED_BY_FIELD: '$user_id'
            }
        }]

        # Update reports_config:
        #     'updated_by' from 'user_id'
        self.db.gui_reports_config_collection().update_many(find_query, update_query)

        # Update reports:
        #     'updated_by' from 'user_id'
        self.db.enforcements_collection().update_many(find_query, update_query)

        update_query[0]['$set'][LAST_UPDATED_FIELD] = '$timestamp'
        # Update saved views, per entity:
        #     'last_updated' from 'timestamp'
        #     'updated_by' from 'user_id'
        for entity_type in EntityType:
            views_collection = self._entity_views_map[entity_type]
            views_collection.update_many(find_query, update_query)

    @db_migration(raise_on_failure=False)
    def _update_schema_version_25(self):
        """
        For 2.14 - to fix Predefined queries that do not have the 'last_updated' and 'updated_by'
        :return:
        """
        print('Upgrade to schema 25')
        for entity_type in EntityType:
            self._entity_views_map[entity_type].update_many({
                UPDATED_BY_FIELD: {
                    '$exists': False
                },
                'user_id': '*'
            }, [{
                '$set': {
                    UPDATED_BY_FIELD: '$user_id',
                    LAST_UPDATED_FIELD: '$timestamp'
                }
            }])

    @mongo_retry()
    def delete_dup_users(self):
        """
        Delete duplicated users from users collection, identify duplicates by user_name and source.
        :return: None
        """
        with self.db.gui_users_collection().start_session() as transaction:
            results = transaction.aggregate([
                {
                    '$group': {
                        '_id': {
                            'user_name': '$user_name',
                            'source': '$source'
                        },
                        'dups': {
                            '$push': '$_id'
                        },
                        'count': {
                            '$sum': 1
                        }
                    },
                },
                {
                    '$match': {
                        'count': {
                            '$gt': 1
                        }
                    }
                }
            ])
            for dup_entry in results:
                _id = dup_entry.get('_id')
                username = _id.get('user_name')
                source = _id.get('source')
                dup_ids = dup_entry.get('dups', [])
                if not dup_ids:
                    # should not happen
                    continue

                print(f'Found duplicated user: {username}:{source}')
                # delete all dup ids except from the first one
                for chunk in chunks(5000, dup_ids[1:]):
                    transaction.delete_many({
                        '_id': {
                            '$in': chunk
                        }
                    })

    @db_migration(raise_on_failure=False)
    def _update_schema_version_26(self):
        """
        Check for duplicated users in users collections: AX-5836
        :return:
        """
        print('Upgrade to schema 26')
        self.delete_dup_users()

    @db_migration(raise_on_failure=False)
    def _update_schema_version_27(self):
        """
        Change in structure of an 'expression' object:
        - 'obj' bool becomes 'context' str, containing one of ['', 'OBJ', 'ENT']
        - 'nested' array becomes 'children' array
        """
        print('Upgrade to schema 27')
        for entity_type in EntityType:
            self._entity_views_map[entity_type].update_many({
                'view.query.expressions': {
                    '$exists': True
                }
            }, {
                '$set': {
                    'view.query.expressions.$[obj].context': 'OBJ',
                    'view.query.expressions.$[all].context': '',
                }
            }, array_filters=[{
                'obj.obj': True
            }, {
                'all.obj': False
            }])
            self._entity_views_map[entity_type].update_many({
                'view.query.expressions': {
                    '$exists': True
                }
            }, [{
                '$set': {
                    'view.query.expressions': {
                        '$map': {
                            'input': '$view.query.expressions',
                            'as': 'expression',
                            'in': {
                                '$mergeObjects': [{
                                    'children': '$$expression.nested'
                                }, {
                                    '$arrayToObject': {
                                        '$filter': {
                                            'input': {'$objectToArray': '$$expression'},
                                            'as': 'expression',
                                            'cond': {'$ne': ['$$expression.k', 'nested']}
                                        }
                                    }
                                }]
                            }
                        }
                    }
                }
            }])

    @db_migration(raise_on_failure=False)
    def _update_schema_version_28(self):
        print('upgrade to schema 28')
        config_match = {
            'config_name': CONFIG_CONFIG
        }
        current_config = self.db.get_collection(
            GUI_PLUGIN_NAME, CONFIGURABLE_CONFIGS_LEGACY_COLLECTION).find_one(config_match)
        if not current_config:
            return
        current_config['config']['system_settings']['exactSearch'] = True
        self.db.get_collection(GUI_PLUGIN_NAME, CONFIGURABLE_CONFIGS_LEGACY_COLLECTION).replace_one(
            config_match, current_config)

    @db_migration(raise_on_failure=False)
    def _update_schema_version_29(self):
        """
        For 3.0 - remove last_updated field from Predefined Saved Queries
        :return:
        """
        print('Upgrade to schema 29')
        for entity_type in EntityType:
            self._entity_views_map[entity_type].update_many({
                PREDEFINED_FIELD: True
            }, [{
                '$set': {
                    LAST_UPDATED_FIELD: None
                }
            }])

    @db_migration(raise_on_failure=False)
    def _update_schema_version_30(self):
        """
        For 3.1 - Change reports (pdf) namings containing */:?\
        :return:
        """
        print('Upgrade to schema 30')
        report_config_collection = self.db.gui_reports_config_collection()
        reports_to_fix = report_config_collection.find(
            {'name': {'$regex': r'[^\w@.\s-]'}})
        fixed = {}

        # Creating a fix map
        for report in reports_to_fix:
            fixed[report['uuid']] = {'new_name': re.sub(r'[^\w@.\s-]', '-', report['name']),
                                     'old_name': report['name']}

        # Creating duplicates list
        all_new_names = [current_report['new_name'] for current_report in fixed.values()]

        # list of dup names and number of appearances (Notice the set comprehension).
        all_duplicate_new_names = {current_report_name for current_report_name in all_new_names if
                                   all_new_names.count(current_report_name) > 1}

        # If there are duplicates
        if len(all_duplicate_new_names) != 0:
            # New dict key usages will default to 0.
            usage_counter = defaultdict(int)
            for current_report in fixed.values():
                current_report_new_name = current_report['new_name']
                # If current name is a duplicate.
                if current_report_new_name not in all_duplicate_new_names:
                    continue

                # pylint: disable=pointless-statement
                usage_counter[current_report_new_name] += 1
                current_report[
                    'new_name'] = f'{current_report_new_name} ({usage_counter[current_report_new_name]})'

        for uuid, names in fixed.items():
            # Fixing name in reports_config collection
            update_result = report_config_collection.update_one({'uuid': uuid},
                                                                {'$set': {'name': names['new_name']}})

            if update_result.modified_count != 1:
                logger.error('Had a problem updating the report name to remove special characters.')
                continue

            # Fixing name in reports collection.
            file_name_filter = {'filename': f'most_recent_{names["old_name"]}'}
            file_name_update = {'$set': {'filename': f'most_recent_{names["new_name"]}'}}
            update_result = self.db.get_collection(GUI_PLUGIN_NAME, 'reports').update_one(file_name_filter,
                                                                                          file_name_update)

            if update_result.modified_count != 1:
                logger.error('Had a problem updating the report name to remove special characters.')
                continue

            # Fixing gridfs file.
            self.db.get_collection(GUI_PLUGIN_NAME, 'fs.files').update_one(file_name_filter, file_name_update)

    @db_migration(raise_on_failure=False)
    def _update_schema_version_31(self):
        """
        For 3.3 - Migrate users and roles to the new permissions structure
        :return:
        """
        print('Upgrade to schema 31')
        self._migrate_old_users_and_roles_legacy()

    @db_migration(raise_on_failure=False)
    def _update_schema_version_32(self):
        """
        For 3.4 - Add a default value for a new feature flag in Axonius system:
        Query time-line range
        Set default to False for existing customers
        :return:
        """
        print('Upgrade to schema 32')
        self._set_query_timeline_feature_flag_legacy()
        self._fix_space_id_in_panels()

    def _fix_space_id_in_panels(self):
        dashboard_spaces_collection = self.db.get_collection(self.plugin_name, DASHBOARD_SPACES_COLLECTION)
        dashboard_collection = self.db.get_collection(self.plugin_name, DASHBOARD_COLLECTION)
        panels = dashboard_collection.find({})
        panels_map = {str(panel.get('_id')): panel for panel in panels}
        for space in dashboard_spaces_collection.find(filter=filter_archived()):
            panels_order = space.get('panels_order', [])
            space_id = space.get('_id')
            for panel_id in panels_order:
                if str(panels_map[panel_id].get('space')) != space_id:
                    dashboard_collection.update_one({
                        '_id': ObjectId(panel_id)
                    }, {
                        '$set': {
                            'space': space_id
                        }
                    })

    def _set_query_timeline_feature_flag_legacy(self):
        """
        Set a default value for the Query Time-Line range FeatureFlag to be False for existing customers
        """
        self.db.get_collection(GUI_PLUGIN_NAME, CONFIGURABLE_CONFIGS_LEGACY_COLLECTION).update_one({
            'config_name': FEATURE_FLAGS_CONFIG
        }, {
            '$set': {'config.query_timeline_range': True}
        })

    @db_migration(raise_on_failure=False)
    def _update_schema_version_33(self):
        """
        For 3.4 - Add a default value for a new feature flag in Axonius system:
        Enable Enforcement Center
        Set default to True for existing customers
        :return:
        """
        print('Upgrade to schema 33')
        self.db.get_collection(GUI_PLUGIN_NAME, CONFIGURABLE_CONFIGS_LEGACY_COLLECTION).update_one({
            'config_name': FEATURE_FLAGS_CONFIG
        }, {
            '$set': {
                'config.enforcement_center': True
            }
        })

    def _update_reports_views(self, entity_to_views):
        report_configs_update = self.db.gui_reports_config_collection().find({
            'views': {
                '$exists': True
            }
        }, {'views': 1})
        for report_config in report_configs_update:
            views_update = [{
                'entity': view['entity'],
                'id': entity_to_views[view['entity']].get(view['name'])
            } for view in report_config['views'] if view.get('entity') and view.get('name')]
            self.db.gui_reports_config_collection().update_one({
                '_id': report_config['_id']
            }, {
                '$set': {
                    'views': views_update
                }
            })

    def _update_dashboards_views(self, entity_to_views):
        dashboards_update = self.db.gui_dashboard_collection().find({
            'config': {
                '$ne': None
            }
        }, {'config': 1})
        for dashboard in dashboards_update:
            config = dashboard['config']
            if config.get('views'):
                config['views'] = [{
                    'entity': view['entity'],
                    'id': entity_to_views[view['entity']].get(view['name'])
                } for view in config['views'] if view.get('entity') and view.get('name')]
            elif config.get('entity'):
                entity = config['entity']
                if 'base' in config:
                    config['base'] = entity_to_views[entity].get(config['base'])
                    config['intersecting'] = [entity_to_views[entity].get(name) for name in config['intersecting']]
                elif config.get('view'):
                    config['view'] = entity_to_views[entity].get(config['view'])
            self.db.gui_dashboard_collection().update_one({
                '_id': dashboard['_id']
            }, {
                '$set': {
                    'config': config
                }
            })

    def _update_enforcements_views(self, entity_to_views):
        enforcements_update = self.db.enforcements_collection().find({
            'triggers': {
                '$ne': []
            }
        }, {'triggers': 1})
        for enforcement in enforcements_update:
            triggers = [trigger for trigger in enforcement['triggers'] if trigger.get('view', {}).get('entity')]
            for trigger in triggers:
                view = trigger['view']
                if view.get('name'):
                    entity = view['entity']
                    trigger['view'] = {
                        'entity': entity,
                        'id': entity_to_views[entity].get(trigger['view']['name'])
                    }
            self.db.enforcements_collection().update_one({
                '_id': enforcement['_id']
            }, {
                '$set': {
                    'triggers': triggers
                }
            })

    def _get_views_by_entity(self):
        entity_to_views = {}
        for entity_type in EntityType:
            entity_to_views[entity_type.value] = {
                view['name']: str(view['_id'])
                for view in self._entity_views_map[entity_type].find({
                    'query_type': 'saved'
                }, {
                    'name': 1
                })
            }
        return entity_to_views

    @db_migration(raise_on_failure=False)
    def _update_schema_version_34(self):
        """
        AX-6287 Update all Reports, Enforcements and Charts holding a view name, to hold its uuid instead
        """
        print('Upgrade to schema 34')
        entity_to_views = self._get_views_by_entity()
        self._update_reports_views(entity_to_views)
        self._update_dashboards_views(entity_to_views)
        self._update_enforcements_views(entity_to_views)

    @db_migration(raise_on_failure=False)
    def _update_schema_version_35(self):
        """
        For 3.4 - Default dashboard chart sort
        :return:
        """
        print('Upgrade to schema 35')
        self.db.get_collection(self.plugin_name, DASHBOARD_COLLECTION).update_many(
            {
                'config': {
                    '$ne': None
                },
                '$or': [{
                    'metric': 'compare'
                }, {
                    'metric': 'segment'
                }]
            }, {
                '$set': {
                    'config.sort': {
                        'sort_by': 'value',
                        'sort_order': 'desc'
                    }
                }
            })

    def _update_enforcement_tasks_views(self, entity_to_views):
        trigger_path = 'result.metadata.trigger.view'
        tasks_update = self.db.tasks_collection().find({
            'job_name': 'run',
            trigger_path: {
                '$exists': True
            }
        }, {
            trigger_path: 1
        })
        for task in tasks_update:
            view = task['result']['metadata']['trigger']['view']
            if not view.get('entity') or not view.get('name'):
                continue

            self.db.tasks_collection().update_one({
                '_id': task['_id']
            }, {
                '$set': {
                    trigger_path: {
                        'entity': view['entity'],
                        'id': entity_to_views[view['entity']].get(view['name'])
                    }
                }
            })

    @db_migration(raise_on_failure=False)
    def _update_schema_version_36(self):
        print('Upgrade to schema 36')
        self._update_enforcement_tasks_views(self._get_views_by_entity())

    @db_migration(raise_on_failure=False)
    def _update_schema_version_37(self):
        """
        For 3.5 - Add a default value "not private" for all the existing devices and users views in the system
        and move the identity providers into a separate config record
        :return:
        """
        print('Upgrade to schema 37')
        for entity_type in EntityType:
            self._entity_views_map[entity_type].update_many({
                PRIVATE_FIELD: {'$exists': False}
            }, {
                '$set': {
                    PRIVATE_FIELD: False
                }
            })

    @db_migration(raise_on_failure=False)
    def _update_schema_version_38(self):
        """
        For 3.5 - Add compliance rules update role.
        :return:
        """
        print('Upgrade to schema 38')
        roles_collection = self.db.get_collection(GUI_PLUGIN_NAME, ROLES_COLLECTION)
        bulk_updates = []
        roles = roles_collection.find({})

        for role in roles:
            rule_name = role['name']
            if rule_name in ['Owner', 'OwnerReadOnly', 'Admin']:
                bulk_updates.append(UpdateOne(
                    {
                        '_id': role['_id'],
                    },
                    {
                        '$set': {
                            'permissions.compliance.post': True
                        }
                    }
                ))
            else:
                bulk_updates.append(UpdateOne(
                    {
                        '_id': role['_id'],
                    },
                    {
                        '$set': {
                            'permissions.compliance.post': False
                        }
                    }
                ))

        if len(bulk_updates) > 0:
            roles_collection.bulk_write(bulk_updates)

    @db_migration(raise_on_failure=False)
    def _update_schema_version_39(self):
        """
        For 3.6 - Migrate the external service to a new configuration record
        :return:
        """
        print('Upgrade to schema 39')
        self.migrate_external_services_settings()

    # pylint: disable=R1702
    @db_migration(raise_on_failure=False)
    def _update_schema_version_40(self):
        """
        Change 'general_info' service to 'wmi_adapter' in saved queries.
        """
        print('Upgrade to schema 40')
        for entity_type in EntityType:
            views_collection = self._entity_views_map[entity_type]
            general_info_views = views_collection.find({
                'view.query.filter': {
                    '$regex': '.*general_info.*'
                }
            })
            for view_doc in general_info_views:
                original_fields = view_doc.get('view', {}).get('fields', [])
                # update fields names
                original_fields = [field.replace('general_info', 'wmi_adapter') for field in original_fields]
                # update query filter
                query = view_doc.get('view', {}).get('query', {})
                query['filter'] = query.get('filter', '').replace('general_info', 'wmi_adapter')
                query['onlyExpressionsFilter'] = query.get('onlyExpressionsFilter', '').replace('general_info',
                                                                                                'wmi_adapter')
                # update expressions
                expressions = query.get('expressions', [])
                for expression in expressions:
                    if not expression:
                        continue
                    for k, v in expression.items():
                        if not isinstance(expression[k], str):
                            continue
                        expression[k] = expression[k].replace('general_info', 'wmi_adapter')
                views_collection.update_one({
                    '_id': view_doc['_id']
                }, {
                    '$set': {
                        'view.fields': original_fields,
                        'view.query': query
                    }
                })

    @db_migration(raise_on_failure=False)
    def _update_schema_version_41(self):
        """
        add last password change field to all users, for password expiration
        :return:
        """
        print('Upgrade to schema 41')
        self.db.get_collection(GUI_PLUGIN_NAME, USERS_COLLECTION).update_many(
            {},  # all users
            {'$set': {'password_last_updated': datetime.utcnow()}}
        )

    def _update_default_locked_actions_legacy(self, new_actions):
        """
        Update the config record that holds the FeatureFlags setting, adding received new_actions to it's list of
        locked_actions
        """
        self.db.get_collection(GUI_PLUGIN_NAME, CONFIGURABLE_CONFIGS_LEGACY_COLLECTION).update_one({
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

    def _get_exposed_ports(self, mode, expose_port):
        # This is kind of confusing.
        # - The internal port 443 is an https server that has no protections (like optional mutual tls) and needs
        # to be used only internally by the system. We want this to be mounted to 127.0.0.1:4433
        # - The internal port 1443 is an https server that is meant to be used operationally by the customer.
        # we mount this to 443 always.
        # - the internal port 80 is mounted to the host 80 only in case the customer do not specifically asked
        # for it to not be mounted.

        published_ports = [
            '--publish', f'443:1443'  # external customer-facing web server. host:443 -> gui:1443
        ]
        if not self._system_config.get('https-only'):
            published_ports.extend(['--publish', '80:80'])
        # host:4433 -> gui:443
        if mode != 'prod':
            internal_web_server = ['--publish', '4433:443']
        else:
            internal_web_server = ['--publish', '127.0.0.1:4433:443']
        published_ports.extend(internal_web_server)  # do not expose to 0.0.0.0 in prod!

        return published_ports

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
        libs = os.path.abspath(
            os.path.join(os.path.dirname(__file__), '..', '..', '..', 'axonius-libs', 'src', 'libs'))
        volumes.extend([f'{libs}:{LIBS_PATH.as_posix()}:ro'])

        # extend volumes by mapping specifically each python file, to be able to debug much better.
        volumes.extend([f'{self.service_dir}/{fn}:/home/axonius/app/{self.package_name}/{fn}:ro'
                        for fn in os.listdir(self.service_dir) if fn.endswith('.py')])

        volumes.extend([f'{self.service_dir}/logic:/home/axonius/app/{self.package_name}/logic:ro'])

        # extend and share the routes folder
        volumes.extend([f'{self.service_dir}/routes/:/home/axonius/app/{self.package_name}/routes/:ro'])

        # append constants dir in order to update new adapters.
        # We use constants dir instead of plugin_meta beacuse mounting a specific file won't support inode replacement
        volumes.append(f'{self.service_dir}/frontend/src/constants/:'
                       f'/home/axonius/app/{self.package_name}/frontend/src/constants/:ro')

        return volumes

    @property
    def is_unique_image(self):
        return True

    @property
    def run_timeout(self):
        return 60 * 6

    # I don't want to change all dockerfiles
    # pylint: disable=W0221
    def get_dockerfile(self, *args, docker_internal_env_vars=None, **kwargs):
        client_filter = list(filter(re.compile(r'CLIENT=(\w)').match, docker_internal_env_vars or []))
        npm_params = f'-- --env.{client_filter[0].lower()}' if client_filter else ''

        build_command = '' if self.is_dev else f'''
# Compile npm, assuming we have it from axonius-libs
RUN cd ./gui/frontend/ && npm run build {npm_params}
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
COPY /config/ /home/axonius/config/
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

    def unlink_users(self, internal_axon_ids: List = None):
        return self.post('users/manual_unlink', session=self._session, data={
            'ids': internal_axon_ids, 'include': True
        })

    def unlink_devices(self, internal_axon_ids: List = None):
        return self.post('devices/manual_unlink', session=self._session, data={
            'ids': internal_axon_ids, 'include': True
        })

    def delete_users(self, internal_axon_ids, *vargs, **kwargs):
        return self.delete('users', session=self._session, data={
            'ids': internal_axon_ids, 'include': True
        }, *vargs, **kwargs)

    def get_device_by_id(self, id_, *vargs, **kwargs):
        return self.get('devices/{0}'.format(id_), session=self._session, *vargs, **kwargs)

    def delete_client(self, adapter_unique_name, client_id, *vargs, **kwargs):
        data = json.dumps({
            'adapter': adapter_unique_name
        })
        return self.delete(f'adapters/connections/{client_id}', data=data, session=self._session, *vargs, **kwargs)

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
        return self.get('settings/api_key', session=self._session).json()

    def renew_api_key(self):
        return self.post('settings/reset_api_key', session=self._session).json()

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

    def add_panel(self, space_id, data):
        return self.put(f'dashboard/charts/{space_id}', data=json.dumps(data), session=self._session)

    def edit_panel(self, panel_id, data):
        return self.post(f'dashboard/charts/{panel_id}', data=json.dumps(data), session=self._session)

    def remove_panel(self, panel_id, space_id):
        return self.delete(f'dashboard/charts/{panel_id}',
                           data=json.dumps({'panelId': panel_id, 'spaceId': space_id}),
                           session=self._session)

    def move_panel(self, panel_id, space_id):
        return self.put(f'dashboard/charts/move/{panel_id}',
                        data=json.dumps({'destinationSpace': space_id}),
                        session=self._session)

    def get_space_id_from_panel(self, panel_id: str):
        return self.db.get_collection(self.plugin_name, DASHBOARD_COLLECTION)\
            .find_one(filter={'_id': ObjectId(panel_id)}, projection={'space': 1})

    def get_gui_settings(self):
        return self.db.plugins.get_plugin_settings(GUI_PLUGIN_NAME).configurable_configs[CONFIG_CONFIG]

    def set_gui_settings(self, value):
        self.db.plugins.get_plugin_settings(GUI_PLUGIN_NAME).configurable_configs[CONFIG_CONFIG] = value

    def get_feature_flags(self):
        return self.db.plugins.get_plugin_settings(GUI_PLUGIN_NAME).configurable_configs[FEATURE_FLAGS_CONFIG]

    def get_identity_providers_settings(self):
        return self.db.plugins.get_plugin_settings(GUI_PLUGIN_NAME).configurable_configs[IDENTITY_PROVIDERS_CONFIG]

    def set_identity_providers_settings(self, value):
        self.db.plugins.get_plugin_settings(GUI_PLUGIN_NAME).configurable_configs[IDENTITY_PROVIDERS_CONFIG] = value

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
        return self.get(f'reports/{report_id}/pdf', session=self._session, *vargs, **kwargs)

    def get_chart_csv(self, chart_id, *vargs, **kwargs):
        return self.get(f'dashboard/charts/{chart_id}/csv', session=self._session, *vargs, **kwargs)

    def get_saved_views(self):

        user_view = self.db.get_collection('gui', USER_VIEWS)
        device_view = self.db.get_collection('gui', DEVICE_VIEWS)

        entity_query_views_db_map = {
            EntityType.Users: user_view,
            EntityType.Devices: device_view,
        }

        saved_views_filter = filter_archived({
            'query_type': 'saved',
            '$or': [
                {
                    PREDEFINED_FIELD: False
                },
                {
                    PREDEFINED_FIELD: {
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
        new_report = {**report}

        result = self.db.gui_reports_config_collection().replace_one({
            'name': name
        }, new_report, upsert=True)
        return result

    def _migrate_default_report(self):
        exec_reports_settings_collection = self.db.get_collection('gui', 'exec_reports_settings')

        default_report = exec_reports_settings_collection.find_one()
        default_report_config = self.db.gui_reports_config_collection().find_one()
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
            self.db.gui_reports_config_collection().delete_one({'_id': default_report_config.get('_id')})

    def _migrate_report_periodic_config(self):
        self.db.gui_reports_config_collection().update_many({}, {
            '$set': {
                'period_config': {
                    'week_day': 0,
                    'monthly_day': 1,
                    'send_time': '13:00',
                }
            }
        })

    def _get_hidden_user_id(self):
        hidden_user = self.db.gui_users_collection().find_one({
            'user_name': AXONIUS_USER_NAME
        }, {
            '_id': 1
        })
        if not hidden_user:
            return None
        return hidden_user['_id']

    def _migrate_old_users_and_roles_legacy(self):
        users_collection = self.db.get_collection(GUI_PLUGIN_NAME, USERS_COLLECTION)
        roles_collection = self.db.get_collection(GUI_PLUGIN_NAME, ROLES_COLLECTION)
        users_config_collection = self.db.get_collection(GUI_PLUGIN_NAME, USERS_CONFIG_COLLECTION)
        external_role_id = None
        config_doc = users_config_collection.find_one({})
        # Get the old default external role
        if config_doc:
            external_role_default_name = config_doc['external_default_role']
            external_role = roles_collection.find_one({'name': external_role_default_name})
            if external_role:
                external_role_id = external_role.get('_id')
        # Just in case the default role was not defined and the old restricted role name exists
        if not external_role_id:
            external_role = roles_collection.find_one({'name': PREDEFINED_ROLE_RESTRICTED_USER})
            if external_role:
                external_role_id = external_role.get('_id')

        with users_collection.start_session() as users_session:
            with users_session.start_transaction():
                with roles_collection.start_session() as roles_session:
                    with roles_session.start_transaction():
                        users = list(users_session.find({}))
                        old_roles = list(roles_session.find({}))
                        number_of_custom_roles = 1
                        for user in users:
                            self._migrate_user(number_of_custom_roles, old_roles, user, users_session)
                        for role in old_roles:
                            self._migrate_role(role, roles_session, old_roles)
            # Update the default external role, if a default role exists
            if external_role_id:
                config_match = {
                    'config_name': CONFIG_CONFIG
                }
                config_collection = self.db.get_collection(
                    GUI_PLUGIN_NAME, CONFIGURABLE_CONFIGS_LEGACY_COLLECTION)
                gui_config = config_collection.find_one(config_match)
                if gui_config and gui_config.get('config'):
                    current_config = gui_config['config']
                    for external_service_settings in ['okta_login_settings',
                                                      'saml_login_settings',
                                                      'ldap_login_settings']:
                        external_service = current_config[external_service_settings]
                        external_service[DEFAULT_ROLE_ID] = str(external_role_id)

                    self.db.get_collection(
                        GUI_PLUGIN_NAME, CONFIGURABLE_CONFIGS_LEGACY_COLLECTION) \
                        .replace_one(filter=config_match,
                                     replacement={'config_name': CONFIG_CONFIG, 'config': current_config})
                users_config_collection.drop()

    @staticmethod
    def _is_role_name_exists(old_roles, name):
        for role in old_roles:
            if role['name'] == name:
                return True
        return False

    def _migrate_role(self, role, roles_session, old_roles):
        if role.get('name') in [PREDEFINED_ROLE_ADMIN, PREDEFINED_ROLE_OWNER] and role.get(PREDEFINED_FIELD):
            role['permissions'] = get_admin_permissions()
        elif role.get('name') == PREDEFINED_ROLE_READONLY:
            permissions = old_deserialize_db_permissions(role.get('permissions'))
            if all([permission == PermissionLevel.ReadOnly for permission in permissions.values()]):
                if not self._is_role_name_exists(old_roles, PREDEFINED_ROLE_VIEWER):
                    role['name'] = PREDEFINED_ROLE_VIEWER
                role['permissions'] = get_viewer_permissions()
            else:
                role['permissions'] = self._map_old_permissions_to_new_permissions(permissions)
        elif role.get('name') == PREDEFINED_ROLE_RESTRICTED_USER:
            permissions = old_deserialize_db_permissions(role.get('permissions'))
            if all([level == PermissionLevel.Restricted or (
                    level == PermissionLevel.ReadOnly and t == PermissionType.Dashboard) for t, level in
                    permissions.items()]):
                role['name'] = PREDEFINED_ROLE_RESTRICTED
                role['permissions'] = get_restricted_permissions()
            else:
                role['permissions'] = self._map_old_permissions_to_new_permissions(permissions)
        else:
            permissions = old_deserialize_db_permissions(role.get('permissions'))
            role['permissions'] = self._map_old_permissions_to_new_permissions(permissions)
        role_to_set = {
            'name': role['name'],
            'permissions': role['permissions']
        }
        if role.get(PREDEFINED_FIELD):
            role_to_set[PREDEFINED_FIELD] = role[PREDEFINED_FIELD]
        if role.get(IS_AXONIUS_ROLE):
            role_to_set[IS_AXONIUS_ROLE] = role[IS_AXONIUS_ROLE]
        roles_session.update_one(
            {'_id': role['_id']}, {'$set': role_to_set}, upsert=True)

    def _migrate_user(self, number_of_custom_roles, old_roles, user, users_session):
        if user.get('user_name') == AXONIUS_USER_NAME:
            user_role = {
                '_id': ObjectId(),
                'name': PREDEFINED_ROLE_OWNER,
                'permissions': user.get('permissions'),
                PREDEFINED_FIELD: True,
                IS_AXONIUS_ROLE: True
            }
            old_roles.append(user_role)
        elif (user.get('admin') or user.get('user_name') == ADMIN_USER_NAME
              or user.get('role_name') == PREDEFINED_ROLE_ADMIN):
            user_role = next((x for x in old_roles if x.get('name') == PREDEFINED_ROLE_ADMIN), None)
        else:
            user_role = self._get_matched_role(user, old_roles)
        if not user_role:
            new_role_name = f'custom role {number_of_custom_roles}'
            while self._is_role_name_exists(old_roles, new_role_name):
                number_of_custom_roles += 1
                new_role_name = f'custom role {number_of_custom_roles}'
            user_role = {
                '_id': ObjectId(),
                'name': new_role_name,
                'permissions': user.get('permissions'),
            }
            number_of_custom_roles += 1
            old_roles.append(user_role)
        user['role_id'] = user_role.get('_id')
        users_session.update_one({'_id': user['_id']},
                                 {'$unset': {'permissions': 1, 'admin': 1, 'role_name': 1}})
        users_session.update_one({'_id': user['_id']},
                                 {'$set': {'role_id': user_role.get('_id')}})

    @staticmethod
    def _get_matched_role(user, roles) -> dict:
        if not user.get('permissions'):
            return None
        user_permissions = old_deserialize_db_permissions(user.get('permissions'))
        for role in roles:
            if role.get('name') != PREDEFINED_ROLE_ADMIN:
                role_permissions = old_deserialize_db_permissions(role.get('permissions'))
                if user_permissions == role_permissions:
                    return role
        return None

    # pylint: disable=too-many-statements
    def _map_old_permissions_to_new_permissions(self, old_permissions: dict):
        new_permissions = get_permissions_structure(False)
        for old_type, old_value in old_permissions.items():
            if old_type == PermissionType.Dashboard:
                if PermissionLevel.ReadOnly == old_value:
                    new_permissions[PermissionCategory.Dashboard][
                        PermissionAction.View] = True
                if PermissionLevel.ReadWrite == old_value:
                    new_permissions[PermissionCategory.Settings][
                        PermissionAction.RunManualDiscovery] = True
                    self._update_all_category_permissions(new_permissions, PermissionCategory.Dashboard)
            if old_type == PermissionType.Devices:
                if PermissionLevel.ReadOnly == old_value:
                    new_permissions[PermissionCategory.DevicesAssets][
                        PermissionAction.View] = True
                    new_permissions[PermissionCategory.DevicesAssets][PermissionCategory.SavedQueries][
                        PermissionAction.Run] = True
                if PermissionLevel.ReadWrite == old_value:
                    self._update_all_category_permissions(new_permissions, PermissionCategory.DevicesAssets)
            if old_type == PermissionType.Users:
                if PermissionLevel.ReadOnly == old_value:
                    new_permissions[PermissionCategory.UsersAssets][
                        PermissionAction.View] = True
                    new_permissions[PermissionCategory.UsersAssets][PermissionCategory.SavedQueries][
                        PermissionAction.Run] = True
                if PermissionLevel.ReadWrite == old_value:
                    self._update_all_category_permissions(new_permissions, PermissionCategory.UsersAssets)
            if old_type == PermissionType.Adapters:
                if PermissionLevel.ReadOnly == old_value:
                    new_permissions[PermissionCategory.Adapters][
                        PermissionAction.View] = True
                if PermissionLevel.ReadWrite == old_value:
                    self._update_all_category_permissions(new_permissions, PermissionCategory.Adapters)
            if old_type == PermissionType.Enforcements:
                if PermissionLevel.ReadOnly == old_value:
                    new_permissions[PermissionCategory.Enforcements][
                        PermissionAction.View] = True
                    new_permissions[PermissionCategory.Enforcements][PermissionCategory.Tasks][
                        PermissionAction.View] = True
                if PermissionLevel.ReadWrite == old_value:
                    self._update_all_category_permissions(new_permissions, PermissionCategory.Enforcements)
            if old_type == PermissionType.Reports:
                if PermissionLevel.ReadOnly == old_value:
                    new_permissions[PermissionCategory.Reports][
                        PermissionAction.View] = True
                if PermissionLevel.ReadWrite == old_value:
                    self._update_all_category_permissions(new_permissions, PermissionCategory.Reports)
            if old_type == PermissionType.Settings:
                if PermissionLevel.ReadOnly == old_value:
                    new_permissions[PermissionCategory.Settings][
                        PermissionAction.View] = True
                if PermissionLevel.ReadWrite == old_value:
                    self._update_all_category_permissions(new_permissions, PermissionCategory.Settings)
                    new_permissions_settings = new_permissions[PermissionCategory.Settings]
                    new_permissions_settings[PermissionAction.GetUsersAndRoles] = False
                    self._update_all_category_permissions(new_permissions_settings, PermissionCategory.Users, False)
                    self._update_all_category_permissions(new_permissions_settings, PermissionCategory.Roles, False)
            if old_type == PermissionType.Instances:
                if PermissionLevel.ReadOnly == old_value:
                    new_permissions[PermissionCategory.Instances][PermissionAction.View] = True
                if PermissionLevel.ReadWrite == old_value:
                    self._update_all_category_permissions(new_permissions, PermissionCategory.Instances)
        if (old_permissions[PermissionType.Devices] != PermissionLevel.Restricted
                and old_permissions[PermissionType.Users] != PermissionLevel.Restricted):
            new_permissions[PermissionCategory.Compliance][PermissionAction.View] = True
        admin_like = all(value == PermissionLevel.ReadWrite for value in old_permissions.values())
        new_permissions[PermissionCategory.Settings][PermissionAction.ResetApiKey] = admin_like
        new_permissions[PermissionCategory.Settings][PermissionCategory.Audit][PermissionAction.View] = admin_like
        return serialize_db_permissions(new_permissions)

    def _update_all_category_permissions(self, permissions, category, permission_value=True):
        for permission_name in permissions[category].keys():
            if permission_name in PermissionCategory:
                self._update_all_category_permissions(permissions[category], permission_name, permission_value)
            else:
                permissions[category][permission_name] = permission_value

    def migrate_external_services_settings(self):
        gui_config = self.get_gui_settings()
        identity_providers_config = self.get_identity_providers_settings()
        if not identity_providers_config:
            identity_providers_config = {}
        if gui_config:
            if gui_config.get('okta_login_settings'):
                del gui_config['okta_login_settings']
            for external_service in ['saml_login_settings',
                                     'ldap_login_settings']:
                if gui_config.get(external_service):
                    external_service_settings = gui_config[external_service]
                    default_role_id = external_service_settings.get(DEFAULT_ROLE_ID)
                    external_service_settings[ROLE_ASSIGNMENT_RULES] = {
                        DEFAULT_ROLE_ID: default_role_id,
                        EVALUATE_ROLE_ASSIGNMENT_ON: NEW_USERS_ONLY,
                        ASSIGNMENT_RULE_ARRAY: []
                    }
                    identity_providers_config[external_service] = external_service_settings
                    del gui_config[external_service]

            self.set_identity_providers_settings(identity_providers_config)

            self.set_gui_settings(gui_config)
