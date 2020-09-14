"""
System engineering common tasks.
"""
# pylint: disable=too-many-locals, too-many-return-statements, protected-access
import datetime
import importlib
import json
import sys
import os
import subprocess

import pymongo

from axonius.consts.adapter_consts import SHOULD_NOT_REFRESH_CLIENTS
from axonius.consts.plugin_subtype import PluginSubtype
from axonius.utils.debug import redprint, yellowprint, greenprint, blueprint
from axonius.entities import EntityType
from axonius.utils.host_utils import PYTHON_LOCKS_DIR, WATCHDOGS_ARE_DISABLED_FILE
from scripts.instances.network_utils import run_tunnel_for_adapters_register, stop_tunnel_for_adapters_register
from scripts.watchdog import watchdog_main
from services.plugins.compliance_service import ComplianceService
from services.plugins.reimage_tags_analysis_service import ReimageTagsAnalysisService
from services.plugins.reports_service import ReportsService
from services.plugins.system_scheduler_service import SystemSchedulerService
from testing.services.plugins.aggregator_service import AggregatorService
from testing.services.plugins.core_service import CoreService
from testing.services.plugins.static_correlator_service import StaticCorrelatorService
from testing.services.plugins.static_users_correlator_service import StaticUsersCorrelatorService
from testing.services.plugins.static_analysis_service import StaticAnalysisService
from testing.services.plugin_service import AdapterService

from static_analysis.consts import JOB_NAMES
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SERVICES_DIR = os.path.join(ROOT_DIR, 'testing', 'services')
ADAPTERS_DIR = os.path.join(SERVICES_DIR, 'adapters')
PLUGINS_DIR = os.path.join(SERVICES_DIR, 'plugins')
AXONIUS_SH = os.path.join(ROOT_DIR, 'axonius.sh')


def _get_docker_service(name, type_name=None) -> AdapterService:
    if not type_name:
        service_filename = f'{name}_service.py'
        if os.path.exists(os.path.join(ADAPTERS_DIR, service_filename)):
            type_name = 'adapters'
        elif os.path.exists(os.path.join(PLUGINS_DIR, service_filename)):
            type_name = 'plugins'
        else:
            raise ValueError(f'No such adapter or action!')
    module = importlib.import_module(f'services.{type_name}.{name.lower()}_service')
    return getattr(module, ' '.join(name.lower().split('_')).title().replace(' ', '') + 'Service')()


def usage():
    name = sys.argv[0]
    return f'''
    {name} al - list all running adapters & scanners
    {name} af <plugin_unique_name> [--nonblock] - fetches devices from a specific plugin unique name
    {name} afc <adapter_name> <client_id> [--nonblock] - Uses this host's adapter to fetch the client [client_id]
    {name} sc - run static correlator & static users correlator
    {name} sc (devices/users)- run static correlator & static users correlator
    {name} de [dry/wet] - run static correlator to detect errors, pass 'de wet' to fix errors 
    {name} cd - run clean devices (clean db) [specific_adapter] [--do-not-look-at-last-cycle]
                if --do-not-look-at-last-cycle is specified, only in a specific adapter, it will clean without the 
                'do not clean devices that has been fetched in last cycle' protection.
    {name} rr - run reports
    {name} sa - run static analysis [job_name]
    {name} rta - run reimage tags analysis
    {name} re [service/adapter] - restart some service/adapter
    {name} frontend-build - rebuild frontend (locally)
    {name} rel [service/adapter] - uwsgi-reload the flask server of some service/adapter (reload only the python)
    {name} migrate [service/adapter] - run db migrations on some service/adapter. e.g. `migrate aggregator`
    {name} db rf [device/user] [plugin_name] [field] - removes a field from an adapter. 
                                                       e.g. `db rf device aws_adapter _old`
                                                       will remove '_old' from all aws devices.
    {name} fields remove_dynamic [plugin_unique_name] - remove all dynamic fields of a certain plugin. requires a
                                                        restart and a refetch of the adapter for it to apply in gui! 
    {name} disable_client_evaluation [adapter_name] - 'e.g. aws_adapter'. disable client evaluation for the next run
    {name} s3_backup - Trigger s3 backup
    {name} smb_backup - Trigger SMB backup
    {name} azure_backup - Trigger Azure backup
    {name} root_master_s3_restore - Trigger 'Root Master mode' s3 restore
    {name} root_master_smb_restore - Trigger 'Root Master mode' SMB restore
    {name} root_master_azure_restore - Trigger 'Root Master mode' Azure restore
    {name} compliance run (aws/azure) - Run Compliance Report
    {name} tag remove [device/user] [query] [startswith=abcd / eq=abcd] - deletes a tag (gui label)
    {name} trigger [service_name] (execute) - Trigger a job (by default execute) on the service name, on this node.
    {name} ru [container-name] - Recover uwsgi
    {name} kill [adapters] - kill all adapters
    {name} wd [kill/restart] - kill all watchdogs / restart all watchdogs
    {name} wd disable [x] - disable watchdogs for x minutes
    {name} tc [run/stop] Run tunnel (mongo & core) to core 
    '''


# pylint: disable=too-many-branches, too-many-statements
def main():
    try:
        component = sys.argv[1]
    except Exception:
        print(usage())
        return -1

    try:
        action = sys.argv[2]
    except Exception:
        action = None

    ag = AggregatorService()
    core = CoreService()
    sc = StaticCorrelatorService()
    scu = StaticUsersCorrelatorService()
    rr = ReportsService()
    sa = StaticAnalysisService()
    rta = ReimageTagsAnalysisService()
    ss = SystemSchedulerService()
    cs = ComplianceService()

    def get_all_running_adapters_and_scanners():
        result = dict()
        for plugin_unique_name, plugin_dict in core.get_registered_plugins().json().items():
            plugin_subtype = plugin_dict.get('plugin_subtype')
            if plugin_subtype in [PluginSubtype.ScannerAdapter.name, PluginSubtype.AdapterBase.name]:
                result[plugin_unique_name] = plugin_subtype

        return result

    if component == 'al':
        for plugin_name, pst in get_all_running_adapters_and_scanners().items():
            print(f'{plugin_name} - {pst}')

    elif component == 'af':
        plugin_name = action
        assert plugin_name, usage()
        assert plugin_name in get_all_running_adapters_and_scanners().keys(), \
            f'{plugin_name} not running!'

        print(f'Fetching & Rebuilding db (Blocking) for {plugin_name}...')
        try:
            blocking = sys.argv[3] != '--nonblock'
        except Exception:
            blocking = True
        ag.query_devices(plugin_name, blocking=blocking)

    elif component == 'afc':
        if not action:
            print('Please specify an adapter/service')
            return -1
        try:
            client_name = sys.argv[3]
        except Exception:
            print('Please specify client_id')
            return -1
        try:
            service = _get_docker_service(action, type_name='adapters')
        except Exception:
            print(f'No such adapter "{action}"!')
            return -1
        try:
            blocking = sys.argv[4] != '--nonblock'
        except Exception:
            blocking = True

        print(f'Requesting {action} on this host to fetch client {client_name}...')
        service.trigger_insert_to_db(client_name, blocking=blocking)

    elif component == 'sc':
        if not action or action == 'devices':
            print('Running static correlator..')
            sc.correlate(True)
        if not action or action == 'users':
            print('Running static users correlator..')
            scu.correlate(True)

    elif component == 'de':
        fix_errors = action == 'wet'
        print(f'Running detect errors on static correlator, fixing errors {fix_errors}')
        res = sc.trigger('detect_errors', blocking=True, post_json={
            'should_fix_errors': fix_errors
        })
        print(f'Response: {res.json().get("devices_cleared")} errors found')

    elif component == 'compliance':
        compliance_name = sys.argv[3] if len(sys.argv) > 3 else None

        post_json = {'report': compliance_name.lower()} if compliance_name else None

        if action == 'run':
            print(f'Running compliance report generation...')
            cs.trigger('execute_force', True, post_json=post_json)
        else:
            print(f'Invalid action {action}')
            return -1

    elif component == 'trigger':
        job_name = sys.argv[3] if len(sys.argv) > 3 else 'execute'
        try:
            service = _get_docker_service(action)
        except Exception:
            print(f'No such service "{action}"!')
            return -1

        print(f'Triggering {job_name} on {action}...')
        service.trigger(job_name, True)

    elif component == 'cd':
        if not action:
            print('Running clean devices for all adapters(Blocking)...')
            ag.clean_db(True)
        else:
            try:
                service = _get_docker_service(action, type_name='adapters')
            except Exception:
                print(f'No such adapter "{action}"!')
                return -1

            print(f'Running clean devices for {action} (Blocking)...')
            if len(sys.argv) > 3 and sys.argv[3] == '--do-not-look-at-last-cycle':
                print(f'Not looking at last cycle')
                service.trigger_clean_db(do_not_look_at_last_cycle=True)
            else:
                service.trigger_clean_db()

    elif component == 'rr':
        print('Running reports (Blocking)...')
        rr.trigger_execute(True)

    elif component == 'sa':
        print('Running Static Analysis (Blocking)...')
        if not action:
            action = 'execute'
        if action not in JOB_NAMES:
            print(f'Invalid action {action}, actions: {JOB_NAMES}')
            return -1
        sa.trigger(action, True)

    elif component == 'rta':
        print(f'Running Reimage Tags Analysis (Blocking)...')
        rta.trigger_execute(True)

    elif component == 're':
        service_filename = f'{action}_service.py'
        if os.path.exists(os.path.join(ADAPTERS_DIR, service_filename)):
            service_type = 'adapter'
        elif os.path.exists(os.path.join(PLUGINS_DIR, service_filename)):
            service_type = 'service'
        else:
            print(f'No such adapter or action!')
            return -1

        print(f'Restarting {service_type} {action}...')
        subprocess.check_call(
            f'{AXONIUS_SH} {service_type} {action} up --restart --prod', shell=True, cwd=ROOT_DIR
        )

    elif component == 'frontend-build':
        print(f'Rebuilding frontend')
        subprocess.check_call(
            'docker exec -w /home/axonius/app/gui/frontend -t gui npm run build', shell=True, cwd=ROOT_DIR
        )
    elif component == 'rel':
        if not action:
            print('Please specify an adapter/service')
            return -1
        try:
            service = _get_docker_service(action)
        except Exception:
            print(f'No such adapter/service "{action}"!')
            return -1

        print(f'Reloading {action}...')
        service.reload_uwsgi()

    elif component == 'migrate':
        service = _get_docker_service(action)
        print(f'Running DB Migration for {action}...')
        service._migrate_db()   # pylint: disable=protected-access
        print(f'Done!')

    elif component == 'disable_client_evaluation':
        plugin_name = action
        assert plugin_name, usage()

        print(f'Disabling client evaluation for {plugin_name}...')
        ag.db.plugins.get_plugin_settings(plugin_name).plugin_settings_keyval[SHOULD_NOT_REFRESH_CLIENTS] = True

    elif component == 's3_backup':
        ss.trigger_s3_backup()

    elif component == 'smb_backup':
        ss.trigger_smb_backup()

    elif component == 'azure_backup':
        ss.trigger_azure_backup()

    elif component == 'root_master_s3_restore':
        ss.trigger_root_master_s3_restore()

    elif component == 'root_master_smb_restore':
        ss.trigger_root_master_smb_restore()

    elif component == 'root_master_azure_restore':
        ss.trigger_root_master_azure_restore()

    elif component == 'db':
        if action == 'rf':
            try:
                entity, plugin_name, field = sys.argv[3], sys.argv[4], sys.argv[5]
            except Exception:
                print(usage())
                return -1

            try:
                yes_for_all = sys.argv[6].lower() == '--yes'
                blueprint('Identified --yes!')
            except Exception:
                yes_for_all = False

            entity = entity.lower()
            assert entity in ['device', 'user']

            entity_type = EntityType.Devices if entity == 'device' else EntityType.Users

            entity_db = ag._entity_db_map[entity_type]
            match_type = 'adapters' if 'adapter' in plugin_name else 'tags'
            print(f'Note - searching in "{match_type}"')

            def rf_function():
                match = {
                    match_type: {
                        '$elemMatch': {
                            'plugin_name': plugin_name,
                            f'data.{field}': {'$exists': True}
                        }
                    }
                }
                count = entity_db.count(match)
                redprint(f'You are going to remove the field {field} from {count} {plugin_name} {entity}s. '
                         f'This is unrecoverable!')
                redprint(f'Are you sure? [yes/no]')
                if yes_for_all:
                    greenprint('Yes')
                else:
                    res = input()
                    if res != 'yes':
                        print(f'Not continuing.')
                        return 0

                result = entity_db.update_many(
                    match,
                    {
                        '$unset': {f'{match_type}.$.data.{field}': 1}
                    }
                )

                print(f'Matched {result.matched_count}, modified {result.modified_count}')

                new_count = entity_db.count(match)
                if new_count > 0:
                    yellowprint(f'Warning - {plugin_name} {entity}s with {field} still exist. '
                                f'This happens because only the first occurrence of {plugin_name} in the {entity} '
                                f'is deleted. please run this script again.')

                    return False
                else:
                    print('Done')
                    return True

            has_finished = rf_function()
            if yes_for_all:
                while not has_finished:
                    has_finished = rf_function()

        else:
            print(usage())
            return -1

    elif component == 'fields':

        if action == 'remove_dynamic':

            try:

                entity, plugin_unique_name = sys.argv[3], sys.argv[4]

            except Exception:

                print(usage())

                return -1

            entity = entity.lower()

            assert entity in ['device', 'user']

            if entity == 'device':
                entity_db = ag.db.client['aggregator']['devices_fields']
            else:
                entity_db = ag.db.client['aggregator']['users_fields']

            dynamic_schema = {
                'plugin_unique_name': plugin_unique_name,
                'name': 'dynamic'
            }

            all_items = entity_db.find_one(dynamic_schema)

            if not all_items:
                redprint(f'Did not found any dynamic fields declaration. Are you sure this plugin unique name exists?')
                return -1

            count = len(all_items['schema']['items'])

            redprint(f'You are going to remove the {count} dynamic fields from {plugin_unique_name} {entity}s. '

                     f'This is unrecoverable!')

            redprint(f'Are you sure? [yes/no]')

            res = input()

            if res != 'yes':
                print(f'Not continuing.')

                return 0

            entity_db.update_one(

                dynamic_schema,

                {
                    '$set': {
                        'schema.items': []
                    }
                }

            )

            print('Done')

        else:

            print(usage())

            return -1

    elif component == 'tag':
        if action == 'remove':
            try:
                entity_type, query, tag_filter = sys.argv[3], sys.argv[4], sys.argv[5]
            except Exception:
                print(usage())
                return -1

            print(f'Entity Type: {entity_type}')
            print(f'Query: {query}')
            print(f'Filter: {tag_filter}')

            entity_type = entity_type.lower()

            assert entity_type in ['device', 'user']

            if entity_type == 'device':
                entity_db = ag._entity_db_map[EntityType.Devices]
            else:
                entity_db = ag._entity_db_map[EntityType.Users]

            if query == '*':
                query = {}
            elif query == 'input':
                query = json.loads(input('Query: '))
            else:
                query = json.loads(query)

            op, string = tag_filter.split('=')
            op = op.strip()
            string = string.strip()

            if op == 'eq':
                value = string
            elif op == 'startswith':
                value = {'$regex': f'^{string}'}
            else:
                raise ValueError(f'Unknown op {op}')

            query = {
                '$and': [
                    query,
                    {
                        'labels': value
                    }
                ]
            }

            tag_removal_count = 0
            affected_entities_count = 0
            to_fix = []
            for entity in entity_db.find(query, projection={'labels': 1, '_id': 1}):
                original_tags = entity.get('labels') or []
                if op == 'eq':
                    new_labels = [label for label in original_tags if not label == string]

                elif op == 'startswith':
                    new_labels = [label for label in original_tags if not label.startwidth(string)]
                else:
                    raise ValueError(f'Unknown op {op}')

                affected_entities_count += 1
                tag_removal_count += len(original_tags) - len(new_labels)

                to_fix.append(
                    pymongo.operations.UpdateOne(
                        {'_id': entity['_id']},
                        {'$set': {'labels': new_labels}}
                    )
                )

            redprint(f'You are going to remove {tag_removal_count} labels '
                     f'from {affected_entities_count} entities. This is unrecoverable!')
            redprint(f'Are you sure? [yes/no]')

            res = input()

            if res != 'yes':
                print(f'Not continuing.')

                return 0

            print(f'Deleting tags...')
            if to_fix:
                for i in range(0, len(to_fix), 1000):
                    entity_db.bulk_write(to_fix[i: i + 1000], ordered=False)
                    print(f'Fixed Chunk of {i + 1000} records')

                print(f'Done deleting tags')
            else:
                print('Nothing to delete.')

        else:
            print(usage())
            return -1

    elif component == 'ru':
        try:

            container_name = sys.argv[2]

        except Exception:
            print(usage())
            return -1

        subprocess.check_call(
            f'docker exec {container_name} python3 -u ../hacks/recover_uwsgi.py', shell=True, cwd=ROOT_DIR
        )

    elif component == 'kill':
        try:
            what_to_kill = sys.argv[2]
        except Exception:
            print(usage())
            return -1

        if what_to_kill == 'adapters':
            kill_command = 'docker rm -f `docker ps -a -q --filter "name=-adapter"`'
            subprocess.check_call(
                kill_command, shell=True, cwd=ROOT_DIR
            )
        else:
            print(usage())
            return -1

    elif component == 'wd':
        def kill_wd():
            wd_pids = subprocess.check_output(
                'ps aux | grep python | grep watchdog | grep -v "ps aux" | awk \'{print $2}\'',
                shell=True, cwd=ROOT_DIR
            )
            wd_pids = wd_pids.decode("utf-8").strip().replace("\n", " ")
            if wd_pids:
                kill_command = f'kill -9 {wd_pids}'
                subprocess.check_call(
                    kill_command, shell=True, cwd=ROOT_DIR
                )
                print(f'Killed watchdogs {wd_pids}')
            else:
                print(f'No watchdogs are currently running')
        if action == 'kill':
            kill_wd()
        elif action == 'restart':
            kill_wd()
            watchdog_main.run_tasks('restart')
        elif action == 'disable':
            try:
                time_to_disable = int(sys.argv[3])
            except Exception:
                redprint(f'did not get number of minutes to disable')
                print(usage())
                return -1

            time_to_disable = datetime.datetime.utcnow() + datetime.timedelta(minutes=time_to_disable)
            PYTHON_LOCKS_DIR.mkdir(parents=True, exist_ok=True)
            WATCHDOGS_ARE_DISABLED_FILE.write_text(str(time_to_disable))
            print(f'Disabled until {time_to_disable}')
        else:
            print(usage())
            return -1

    elif component == 'tc':
        if action == 'run':
            run_tunnel_for_adapters_register()
        elif action == 'stop':
            stop_tunnel_for_adapters_register()
        else:
            print(usage())
            return -1
    else:
        print(usage())
        return -1

    return 0


if __name__ == '__main__':
    sys.exit(main())
