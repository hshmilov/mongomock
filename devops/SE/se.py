"""
System engineering common tasks.
"""
import sys

from axonius.consts.plugin_subtype import PluginSubtype
from services.plugins.reports_service import ReportsService
from testing.services.plugins.aggregator_service import AggregatorService
from testing.services.plugins.core_service import CoreService
from testing.services.plugins.static_correlator_service import StaticCorrelatorService
from testing.services.plugins.static_users_correlator_service import StaticUsersCorrelatorService


def usage():
    name = sys.argv[0]
    return f'''
    {name} al - list all running adapters & scanners
    {name} af [plugin_unique_name] - fetches devices from a specific plugin unique name
    {name} sc - run static correlator & static users correlator
    {name} cd - run clean devices (clean db)
    {name} rr - run reports
    '''


# pylint: disable=too-many-branches
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

    else:
        print(usage())
        return -1

    return 0


if __name__ == '__main__':
    sys.exit(main())
