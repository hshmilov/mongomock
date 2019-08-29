"""
System engineering common tasks.
"""
# pylint: disable=too-many-locals, too-many-return-statements, protected-access
import importlib
import sys
import os
import subprocess

from axonius.consts.plugin_subtype import PluginSubtype
from axonius.utils.debug import redprint, yellowprint
from axonius.entities import EntityType
from services.plugins.reimage_tags_analysis_service import ReimageTagsAnalysisService
from services.plugins.reports_service import ReportsService
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
    {name} af [plugin_unique_name] - fetches devices from a specific plugin unique name
    {name} sc - run static correlator & static users correlator
    {name} cd - run clean devices (clean db)
    {name} rr - run reports
    {name} sa - run static analysis [job_name]
    {name} rta - run reimage tags analysis
    {name} re [service/adapter] - restart some service/adapter
    {name} migrate [service/adapter] - run db migrations on some service/adapter. e.g. `migrate aggregator`
    {name} db rf [device/user] [plugin_name] [field] - removes a field from an adapter. 
                                                       e.g. `db rf device aws_adapter _old`
                                                       will remove '_old' from all aws devices.
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
        ag.query_devices(pun)

    elif component == 'sc':
        print('Running static correlator..')
        sc.correlate(True)
        print('Running static users correlator..')
        scu.correlate(True)

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

    elif component == 'migrate':
        service = _get_docker_service(action)
        print(f'Running DB Migration for {action}...')
        service._migrate_db()   # pylint: disable=protected-access
        print(f'Done!')

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
