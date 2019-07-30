"""
System engineering common tasks.
"""
import sys
import os
import subprocess

from axonius.consts.plugin_subtype import PluginSubtype
from services.plugins.reimage_tags_analysis_service import ReimageTagsAnalysisService
from services.plugins.reports_service import ReportsService
from testing.services.plugins.aggregator_service import AggregatorService
from testing.services.plugins.core_service import CoreService
from testing.services.plugins.static_correlator_service import StaticCorrelatorService
from testing.services.plugins.static_users_correlator_service import StaticUsersCorrelatorService
from testing.services.plugins.static_analysis_service import StaticAnalysisService

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SERVICES_DIR = os.path.join(ROOT_DIR, 'testing', 'services')
ADAPTERS_DIR = os.path.join(SERVICES_DIR, 'adapters')
PLUGINS_DIR = os.path.join(SERVICES_DIR, 'plugins')
AXONIUS_SH = os.path.join(ROOT_DIR, 'axonius.sh')


def usage():
    name = sys.argv[0]
    return f'''
    {name} al - list all running adapters & scanners
    {name} af [plugin_unique_name] - fetches devices from a specific plugin unique name
    {name} sc - run static correlator & static users correlator
    {name} cd - run clean devices (clean db)
    {name} rr - run reports
    {name} sa - run static analysis
    {name} rta - run reimage tags analysis
    {name} re [service/adapter] - restart some service/adapter  
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
        print('Running clean devices (Blocking)...')
        ag.clean_db(True)

    elif component == 'rr':
        print('Running reports (Blocking)...')
        rr.trigger_execute(True)

    elif component == 'sa':
        print('Running Static Analysis (Blocking)...')
        sa.trigger_execute(True)

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

    else:
        print(usage())
        return -1

    return 0


if __name__ == '__main__':
    sys.exit(main())
