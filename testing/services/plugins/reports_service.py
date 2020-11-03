import traceback
from datetime import datetime

import dateutil
from bson import ObjectId
from pymongo import UpdateOne
from pymongo.database import Database

from axonius.clients.wmi_query.consts import (COMMAND_NAME, EXTRA_FILES_NAME,
                                              PASSWORD, USERNAME)
from axonius.consts import plugin_consts
from axonius.consts.gui_consts import LAST_UPDATED_FIELD
from axonius.consts.plugin_consts import (CORE_UNIQUE_NAME, GUI_PLUGIN_NAME,
                                          NODE_ID, NODE_NAME, PLUGIN_NAME,
                                          PLUGIN_UNIQUE_NAME,
                                          REPORTS_PLUGIN_NAME)
from axonius.consts.report_consts import (
    ACTIONS_FAILURE_FIELD, ACTIONS_FIELD, ACTIONS_MAIN_FIELD,
    ACTIONS_POST_FIELD, ACTIONS_SUCCESS_FIELD, LAST_TRIGGERED_FIELD,
    LAST_UPDATE_FIELD, TIMES_TRIGGERED_FIELD, TRIGGERS_FIELD)
from axonius.db_migrations import db_migration
from reports.action_types.action_type_base import DEFAULT_INSTANCE
from services.plugin_service import PluginService
from services.system_service import SystemService
from services.updatable_service import UpdatablePluginMixin

COMMAND_NAME_LENGTH = 30


class ReportsService(PluginService, SystemService, UpdatablePluginMixin):
    def __init__(self):
        super().__init__('reports')

    def _migrate_db(self):
        super()._migrate_db()
        self._run_all_migrations(nonsingleton=True)

    @staticmethod
    @db_migration(raise_on_failure=False)
    def _update_schema_version_1(db):
        collection = db['reports']
        for report_data in collection.find():
            triggers = report_data['triggers']
            new_triggers = {}
            new_triggers['every_discovery'] = bool(triggers.get('no_change'))
            new_triggers['new_entities'] = bool(triggers.get('increase') and not triggers.get('above'))
            new_triggers['previous_entities'] = bool(triggers.get('decrease') and not triggers.get('below'))
            new_triggers['above'] = triggers.get('above', 0)
            new_triggers['below'] = triggers.get('below', 0)

            report_data['triggers'] = new_triggers
            collection.replace_one({'_id': report_data['_id']}, report_data)

    @db_migration(raise_on_failure=False)
    def _update_schema_version_2(self, db):
        reports_collection = db['reports']
        saved_actions_collection = db['saved_actions']

        def _update_action_data(action_type: str, data, severity):
            """
            The inner data for some action has changed its form
            """
            if action_type == 'send_emails':
                return {
                    'mailSubject': data.get('mailSubject'),
                    'emailList': data.get('emailList', []),
                    'emailListCC': data.get('emailListCC', []),
                    'sendDeviceCSV': data.get('sendDeviceCSV', False),
                    'sendDevicesChangesCSV': data.get('sendDevicesChangesCSV', False)
                }
            if action_type in ['tag_entities', 'tag_all_entities']:
                return {
                    'tag_name': data
                }
            if action_type == 'notify_syslog':
                return {
                    'send_device_data': data,
                    'severity': severity
                }
            if action_type == 'create_fresh_service_incident':
                return {
                    'email': data
                }
            if action_type == 'create_service_now_incident':
                return {
                    'severity': severity
                }
            return {}

        def _update_action_name(name):
            return 'tag' if name in ['tag_all_entities', 'tag_entities'] else name

        for report_data in reports_collection.find():
            actions = report_data[ACTIONS_FIELD]
            run_on = 'AddedEntities' if any('tag_entities' in action['type'] for action in actions) else 'AllEntities'

            actions = [
                {
                    'action_name': _update_action_name(action['type']),
                    'config': _update_action_data(action['type'], action.get('data', {}), report_data['severity'])
                }
                for action
                in actions
            ]

            def saved_action_from_action(action):
                action_name = action['action_name']
                count_of_this_type = saved_actions_collection.count_documents({
                    'action.action_name': action_name
                })
                generated_name = f'{action_name}_{count_of_this_type}'
                saved_actions_collection.insert_one({
                    'name': generated_name,
                    'action': action
                })
                return generated_name

            actions = [saved_action_from_action(x) for x in actions]
            new_actions = {
                ACTIONS_MAIN_FIELD: next(iter(actions), None),
                ACTIONS_SUCCESS_FIELD: [],
                ACTIONS_FAILURE_FIELD: [],
                ACTIONS_POST_FIELD: actions[1:]
            }
            conditions = report_data['triggers']
            del conditions['every_discovery']

            result = list(self.db.client['aggregator'][f'{report_data["view_entity"]}_db'].find({
                '_id': {
                    '$in': [x['_id'] for x in report_data['result']]
                }
            }, {
                'internal_axon_id': 1
            }))

            # This won't overflow because the list comes out of a report, which is a document, therefore the list
            # is shorter than document_max_size (16mb)
            chunk_group_id = ObjectId()
            insert_result = db['internal_axon_ids_lists'].insert_one({
                'chunk': [x['internal_axon_id'] for x in result],
                'chunk_group_id': chunk_group_id,
                'chunk_number': 0,
                'count': len(result),
                'next': None
            })

            triggers = [{
                'name': 'Trigger',
                'view': {
                    'name': report_data['view'],
                    'entity': report_data['view_entity']
                },
                'period': report_data['period'],
                'conditions': conditions,
                'run_on': run_on,
                TIMES_TRIGGERED_FIELD: report_data['triggered'],
                LAST_TRIGGERED_FIELD: report_data[LAST_TRIGGERED_FIELD],
                'result': chunk_group_id
            }]

            new_report = {
                '_id': report_data['_id'],
                LAST_UPDATE_FIELD: datetime.utcnow(),
                ACTIONS_FIELD: new_actions,
                'name': report_data['name'],
                TRIGGERS_FIELD: triggers
            }

            reports_collection.replace_one({'_id': report_data['_id']}, new_report)

    @staticmethod
    @db_migration(raise_on_failure=False)
    def _update_schema_version_3(db):
        # Search for duplicate names in the reports collection
        reports_collection = db['reports']
        dup_names = reports_collection.aggregate([{
            '$project': {
                'name': 1
            },
        }, {
            '$group': {
                '_id': '$name',
                'count': {
                    '$sum': 1
                }
            }
        }, {
            '$match': {
                'count': {
                    '$gt': 1
                }
            }
        }])
        # For each found, update name to the name + counter, making them unique
        for dup_name in dup_names:
            name = dup_name['_id']
            for i in range(dup_name['count']):
                reports_collection.update_one({
                    'name': name
                }, {
                    '$set': {
                        'name': f'{name} {i + 1}'
                    }
                })

    @staticmethod
    @db_migration(raise_on_failure=False)
    def _update_schema_version_4(db):
        # https://axonius.atlassian.net/browse/AX-3832
        # Fixes LAST_TRIGGERED_FIELD that are strings in the DB to be datettimes
        collection = db['reports']
        projection = {
            '_id': 1,
            f'triggers.{LAST_TRIGGERED_FIELD}': 1,
            'triggers.name': 1,
        }
        for report_data in collection.find(projection=projection):
            for trigger in report_data['triggers']:
                last = trigger[LAST_TRIGGERED_FIELD]
                if isinstance(last, str):
                    last = dateutil.parser.parse(last)
                    collection.update_one({
                        '_id': report_data['_id'],
                        'triggers.name': trigger['name']
                    }, {
                        '$set': {
                            f'triggers.$.{LAST_TRIGGERED_FIELD}': last
                        }
                    })

    @db_migration(raise_on_failure=False)
    def _update_schema_version_5(self, specific_reports_db: Database):
        # Change reports to be a single instance, so we rename all collections over
        admin_db = self.db.client['admin']
        for collection_name in specific_reports_db.list_collection_names():
            admin_db.command({
                'renameCollection': f'{specific_reports_db.name}.{collection_name}',
                'to': f'{plugin_consts.REPORTS_PLUGIN_NAME}.{collection_name}'
            })

    @db_migration(raise_on_failure=False)
    def _update_schema_version_6(self):
        # Encrypt client details
        try:
            client = self.db.client['reports']
            saved_actions = client['saved_actions'].find({})
            for saved_action in saved_actions:
                config = saved_action.get('action', {}).get('config')
                if not config:
                    continue
                for key, val in config.items():
                    if val:
                        # GUI_PLUGIN_NAME is encrypting the reports data
                        config[key] = self.db_encrypt(GUI_PLUGIN_NAME, val)
                client['saved_actions'].update(
                    {
                        '_id': saved_action['_id']
                    },
                    {
                        '$set':
                            {
                                'action.config': config
                            }
                    })
            self.db_schema_version = 6
        except OSError:
            print('Cannot upgrade db to version 6, libmongocrypt error')
        except Exception as e:
            print(e)

    def get_plugin_unique_name(self, plugin_name: str, node_id: str) -> str:
        """
        Get plugin unique name from core db by plugin name and node_id
        :param plugin_name: plugin name
        :param node_id: node id
        :return: plugin unique name
        """
        config = self.db.client[CORE_UNIQUE_NAME]['configs'].find_one({
            PLUGIN_NAME: plugin_name,
            NODE_ID: node_id
        })
        return config.get(PLUGIN_UNIQUE_NAME)

    @db_migration(raise_on_failure=False)
    def _update_schema_version_7(self):
        print('Upgrade to schema 7')
        try:
            # change deploy software action to run wmi
            actions_collection = self.db.client[REPORTS_PLUGIN_NAME]['saved_actions']
            old_actions = actions_collection.find(
                filter={
                    'action.action_name': {
                        '$in': [
                            'run_executable_windows', 'run_command_windows', 'run_wmi_scan'
                        ]
                    }
                }
            )
            for action in old_actions:
                try:
                    action = dict(action)
                    config = action['action']['config']
                    # decrypt config data
                    self.decrypt_dict(config)
                    # update instance id
                    default_instance = self.db.client[CORE_UNIQUE_NAME]['nodes_metadata'].find_one({
                        NODE_NAME: DEFAULT_INSTANCE
                    })
                    master_node_id = default_instance[NODE_ID]
                    config['instance'] = master_node_id
                    # update action creds
                    if not config.get('use_adapter'):
                        if config.get('wmi_username'):
                            config[USERNAME] = config['wmi_username']

                        if config.get('wmi_password'):
                            config[PASSWORD] = config['wmi_password']
                    # pop unnecessary keys
                    config.pop('wmi_username', None)
                    config.pop('wmi_password', None)
                    # update files
                    if config.get('executable'):
                        config[EXTRA_FILES_NAME] = [config.get('executable')]
                        config.pop('executable')
                    # update command name
                    if config.get('params'):
                        # normalize command param to command name
                        config[COMMAND_NAME] = config.get('params').strip().lower().replace(' ', '_').replace('-', '_')
                        config[COMMAND_NAME] = config[COMMAND_NAME][:COMMAND_NAME_LENGTH]
                    # update action name
                    old_action_name = action['action']['action_name']
                    action_name = 'run_command_windows' if old_action_name == 'run_executable_windows' \
                        else old_action_name
                    # encrypt config data
                    for key, val in config.items():
                        if val:
                            config[key] = self.db_encrypt(GUI_PLUGIN_NAME, val)
                    actions_collection.update_one(
                        filter={
                            '_id': action['_id']
                        },
                        update={
                            '$set': {
                                'action.action_name': action_name,
                                'action.config': config,
                            }
                        }
                    )
                except Exception as e:
                    print(f'Exception while upgrading reports action id: {action["_id"]} to version 7. Details: {e}')
                    raise
            self.db_schema_version = 7
        except Exception as e:
            print(f'Exception while upgrading reports db to version 7. Details: {e}')
            traceback.print_exc()
            raise

    @db_migration(raise_on_failure=False)
    def _update_schema_version_8(self):
        enforcement_tasks_collection = self.db.data.tasks_collection
        for result_type in ['main', 'failure', 'success', 'post']:
            enforcement_tasks_collection.update_many(
                filter={
                    f'result.{result_type}.action.action_name': 'run_executable_windows',
                },
                update={
                    '$set': {
                        f'result.{result_type}.action.action_name': 'run_command_windows'
                    }
                }
            )

    @db_migration(raise_on_failure=False)
    def _update_schema_version_9(self):
        print('Upgrade to schema 9')
        try:
            collection = self.db.client[REPORTS_PLUGIN_NAME][REPORTS_PLUGIN_NAME]
            reports = collection.find({
                f'{TRIGGERS_FIELD}.period': {'$in': ['daily', 'weekly', 'monthly']}
            }, projection={
                'name': 1,
                LAST_UPDATED_FIELD: 1,
                f'{TRIGGERS_FIELD}.name': 1,
                f'{TRIGGERS_FIELD}.period': 1,
                f'{TRIGGERS_FIELD}.{LAST_TRIGGERED_FIELD}': 1
            })

            bulk_updates = []
            for report in reports:
                triggers = report[TRIGGERS_FIELD]
                trigger = triggers[0]
                period = trigger['period']

                last_updated = report[LAST_UPDATED_FIELD]
                last_triggered = trigger.get(LAST_TRIGGERED_FIELD, None)

                if period == 'daily':
                    period_recurrence = 1
                elif period == 'weekly':
                    period_recurrence = last_triggered.weekday() if last_triggered else last_updated.weekday()
                    period_recurrence = [str(period_recurrence)]
                elif period == 'monthly':
                    period_recurrence = last_triggered.day if last_triggered else last_updated.day
                    if period_recurrence in [29, 30, 31]:
                        period_recurrence = 29
                    period_recurrence = [str(period_recurrence)]
                else:
                    continue

                period_time = last_triggered.strftime('%H:%M') if last_triggered else '13:00'
                bulk_updates.append(UpdateOne(
                    {
                        '_id': report['_id'],
                        f'{TRIGGERS_FIELD}.name': trigger['name']
                    },
                    {
                        '$set': {
                            f'{TRIGGERS_FIELD}.$.period_recurrence': period_recurrence,
                            f'{TRIGGERS_FIELD}.$.period_time': period_time
                        }
                    }
                ))

            if len(bulk_updates) > 0:
                collection.bulk_write(bulk_updates)
            self.db_schema_version = 9

        except Exception as e:
            print(f'Exception while upgrading reports db to version 9. Details: {e}')
            traceback.print_exc()
            raise

    def _request_watches(self, method, *vargs, **kwargs):
        return getattr(self, method)('reports', api_key=self.api_key, *vargs, **kwargs)

    def get_watches(self, *vargs, **kwargs):
        return self._request_watches('get', *vargs, **kwargs)

    def create_watch(self, data, *vargs, **kwargs):
        return self._request_watches('put', data=data, *vargs, **kwargs)

    def delete_watch(self, data, *vargs, **kwargs):
        return self._request_watches('delete', data=data, *vargs, **kwargs)

    def run_jobs(self):
        self.get('trigger_reports', api_key=self.api_key)
