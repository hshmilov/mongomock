"""
System engineering common tasks.
"""
# pylint: disable=too-many-locals, too-many-return-statements, protected-access
import importlib
import sys
import os
import subprocess

from axonius.consts.adapter_consts import SHOULD_NOT_REFRESH_CLIENTS, ADAPTER_SETTINGS
from axonius.consts.plugin_subtype import PluginSubtype
from axonius.utils.debug import redprint, yellowprint
from axonius.entities import EntityType
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
    {name} frontend-install - run npm install inside gui
    {name} rel [service/adapter] - uwsgi-reload the flask server of some service/adapter (reload only the python)
    {name} migrate [service/adapter] - run db migrations on some service/adapter. e.g. `migrate aggregator`
    {name} db rf [device/user] [plugin_name] [field] - removes a field from an adapter. 
                                                       e.g. `db rf device aws_adapter _old`
                                                       will remove '_old' from all aws devices.
    {name} disable_client_evaluation [adapter_unique_name] - disables client evaluation for the next run only
    {name} s3_backup - Trigger s3 backup
    {name} root_master_s3_restore - Trigger 'Root Master mode' s3 restore
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

    def get_all_running_adapters_and_scanners():
        result = dict()
        for plugin_unique_name, plugin_dict in core.get_registered_plugins().json().items():
            plugin_subtype = plugin_dict.get('plugin_subtype')
            if plugin_subtype in [PluginSubtype.ScannerAdapter.name, PluginSubtype.AdapterBase.name]:
                result[plugin_unique_name] = plugin_subtype

        return result

    if component == 'al':
        for pun, pst in get_all_running_adapters_and_scanners().items():
            print(f'{pun} - {pst}')

    elif component == 'af':
        pun = action
        assert pun, usage()
        assert pun in get_all_running_adapters_and_scanners().keys(), \
            f'{pun} not running!'

        print(f'Fetching & Rebuilding db (Blocking) for {pun}...')
        try:
            blocking = not (sys.argv[3] == '--nonblock')
        except Exception:
            blocking = True
        ag.query_devices(pun, blocking=blocking)

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
            blocking = not (sys.argv[4] == '--nonblock')
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
    elif component == 'frontend-install':
        # In customers appliance we don't really need to install npm locally, because upgrade is doing this for us,
        # but this shouldn't effected them.
        # In local builds we need this.
        print(f'Installing npm')
        subprocess.check_call(
            'docker exec -w /home/axonius/app/gui/frontend -t gui npm install', shell=True, cwd=ROOT_DIR
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
        pun = action
        assert pun, usage()
        assert pun in get_all_running_adapters_and_scanners().keys(), \
            f'{pun} not running!'

        print(f'Disabling client evaluation for {pun}...')
        ag.db.client[pun][ADAPTER_SETTINGS].update_one(
            {
                SHOULD_NOT_REFRESH_CLIENTS: {'$exists': True}
            },
            {
                '$set': {
                    SHOULD_NOT_REFRESH_CLIENTS: True
                }
            },
            upsert=True
        )

    elif component == 's3_backup':
        ss.trigger_s3_backup()

    elif component == 'root_master_s3_restore':
        ss.trigger_root_master_s3_restore()

    elif component == 'db':
        if action == 'rf':
            try:
                entity, plugin_name, field = sys.argv[3], sys.argv[4], sys.argv[5]
            except Exception:
                print(usage())
                return -1

            entity = entity.lower()
            assert entity in ['device', 'user']

            entity_type = EntityType.Devices if entity == 'device' else EntityType.Users

            entity_db = ag._entity_db_map[entity_type]
            match_type = 'adapters' if 'adapter' in plugin_name else 'tags'
            print(f'Note - searching in "{match_type}"')

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
            else:
                print('Done')
        else:
            print(usage())
            return -1

    else:
        print(usage())
        return -1

    return 0


if __name__ == '__main__':
    sys.exit(main())
