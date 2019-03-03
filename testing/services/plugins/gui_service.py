import json
import os
import secrets

import requests

from axonius.consts.gui_consts import (CONFIG_COLLECTION, ROLES_COLLECTION, USERS_COLLECTION,
                                       PREDEFINED_ROLE_ADMIN, PREDEFINED_ROLE_RESTRICTED, PREDEFINED_ROLE_READONLY)
from axonius.consts.plugin_consts import (AGGREGATOR_PLUGIN_NAME,
                                          AXONIUS_SETTINGS_DIR_NAME,
                                          CONFIGURABLE_CONFIGS_COLLECTION,
                                          DASHBOARD_COLLECTION,
                                          GUI_NAME,
                                          PLUGIN_NAME,
                                          PLUGIN_UNIQUE_NAME,
                                          MAINTENANCE_TYPE,
                                          GUI_SYSTEM_CONFIG_COLLECTION)

from axonius.utils.gui_helpers import PermissionLevel, PermissionType
from services.plugin_service import PluginService

MAINTENANCE_FILTER = {'type': MAINTENANCE_TYPE}


class GuiService(PluginService):
    def __init__(self):
        super().__init__('gui')
        self._session = requests.Session()
        self.override_exposed_port = True
        local_npm = os.path.join(self.service_dir, 'frontend', 'node_modules')
        local_dist = os.path.join(self.service_dir, 'frontend', 'dist')
        self.is_dev = os.path.isdir(local_npm) and os.path.isdir(local_dist)

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

        if self.db_schema_version != 9:
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
            self.db.get_collection(GUI_NAME, ROLES_COLLECTION).update_one({
                'name': PREDEFINED_ROLE_RESTRICTED
            }, {
                '$set': {
                    'permissions': permissions
                }
            })

            # Fix the Google Login Settings - Rename 'client_id' field to 'client'
            config_match = {
                'config_name': CONFIG_COLLECTION
            }
            current_config = self.db.get_collection(GUI_NAME, CONFIGURABLE_CONFIGS_COLLECTION).find_one(config_match)
            if current_config:
                current_config_google = current_config['config']['google_login_settings']
                if current_config_google.get('client_id'):
                    current_config_google['client'] = current_config_google['client_id']
                    del current_config_google['client_id']
                    self.db.get_collection(GUI_NAME, CONFIGURABLE_CONFIGS_COLLECTION).replace_one(
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
                                            '$ne': GUI_NAME
                                        }
                                    }
                                ]
                            }
                        }
                    },
                    update={
                        '$set': {
                            f'tags.$[i].{PLUGIN_NAME}': GUI_NAME,
                            f'tags.$[i].{PLUGIN_UNIQUE_NAME}': GUI_NAME
                        }
                    },
                    array_filters=[
                        {
                            '$and': [
                                {
                                    f'i.{PLUGIN_NAME}': {
                                        '$ne': GUI_NAME
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
                'config_name': CONFIG_COLLECTION
            }
            current_config = self.db.get_collection(GUI_NAME, CONFIGURABLE_CONFIGS_COLLECTION).find_one(config_match)
            if current_config:
                current_config_okta = current_config['config']['okta_login_settings']
                if current_config_okta.get('gui_url'):
                    current_config_okta['gui2_url'] = current_config_okta['gui_url']
                    del current_config_okta['gui_url']
                    self.db.get_collection(GUI_NAME, CONFIGURABLE_CONFIGS_COLLECTION).replace_one(
                        config_match, current_config)
            self.db_schema_version = 6
        except Exception as e:
            print(f'Exception while upgrading gui db to version 6. Details: {e}')

    def _update_schema_version_7(self):
        print('upgrade to schema 7')
        try:
            # If Instances screen default doesn't exist add it with Resticted default.
            self.db.get_collection(GUI_NAME, ROLES_COLLECTION).update_many(
                {f'permissions.{PermissionType.Instances.name}': {'$exists': False}},
                {'$set': {f'permissions.{PermissionType.Instances.name}': PermissionLevel.Restricted.name}})

            # Update Admin role with ReadWrite
            self.db.get_collection(GUI_NAME, ROLES_COLLECTION).find_one_and_update(
                {'name': PREDEFINED_ROLE_ADMIN},
                {'$set': {f'permissions.{PermissionType.Instances.name}': PermissionLevel.ReadWrite.name}})
            self.db_schema_version = 7
        except Exception as e:
            print(f'Exception while upgrading gui db to version 7. Details: {e}')

    def _update_schema_version_8(self):
        print('upgrade to schema 8')
        try:
            # If Instances screen default doesn't exist add it with Resticted default.
            self.db.get_collection(GUI_NAME, USERS_COLLECTION).update_many(
                {f'permissions.{PermissionType.Instances.name}': {'$exists': False},
                 '$or': [{'admin': False}, {'admin': {'$exists': False}}],
                 'role_name': {'$ne': PREDEFINED_ROLE_ADMIN}},
                {'$set': {f'permissions.{PermissionType.Instances.name}': PermissionLevel.Restricted.name}})

            # Update Admin role with ReadWrite
            self.db.get_collection(GUI_NAME, USERS_COLLECTION).update_many(
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
            users_col = self.db.get_collection(GUI_NAME, USERS_COLLECTION)
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
            roles_col = self.db.get_collection(GUI_NAME, ROLES_COLLECTION)
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

    @property
    def exposed_ports(self):
        """
        :return: list of pairs (exposed_port, inner_port)
        """
        # The only container that listens to 80 and redirects to 80 is the gui, to allow http to https redirection.
        return [(80, 80)] + super().exposed_ports

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
        volumes.extend([f'{libs}:/home/axonius/libs:ro'])

        # extend volumes by mapping specifically each python file, to be able to debug much better.
        volumes.extend([f'{self.service_dir}/{fn}:/home/axonius/app/{self.package_name}/{fn}:ro'
                        for fn in os.listdir(self.service_dir) if fn.endswith('.py')])

        return volumes

    def get_dockerfile(self):
        build_command = '' if self.is_dev else '''
# Compile npm, assuming we have it from axonius-libs
RUN cd ./gui/frontend/ && npm run build
'''
        install_command = '' if self.is_dev else '''
# Prepare build packages
COPY ./frontend/package.json ./gui/frontend/package.json
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
        return self.get_configurable_config(CONFIG_COLLECTION)

    def get_maintenance_flags(self):
        flags = self.db.get_collection(self.plugin_name, GUI_SYSTEM_CONFIG_COLLECTION).find_one(MAINTENANCE_FILTER)
        del flags['_id']
        return flags

    def set_maintenance_flags(self, flags):
        self.db.get_collection(self.plugin_name, GUI_SYSTEM_CONFIG_COLLECTION).update_one(MAINTENANCE_FILTER, {
            '$set': flags
        })
