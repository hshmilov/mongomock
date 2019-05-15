import itertools
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import DefaultDict, List, Tuple

from axonius.entities import EntityType
from axonius.utils.parsing import normalize_hostname, compare_normalized_hostnames
from axonius.devices.device_adapter import LAST_SEEN_FIELD, AdapterProperty
from axonius.consts.plugin_consts import PLUGIN_UNIQUE_NAME
from axonius.consts.plugin_subtype import PluginSubtype
from axonius.mixins.triggerable import Triggerable, RunIdentifier
from axonius.plugin_base import PluginBase
from axonius.utils.files import get_local_config_file
from axonius.utils.axonius_query_language import parse_filter

logger = logging.getLogger(f'axonius.{__name__}')


class ReimageTagsAnalysisService(Triggerable, PluginBase):
    def __init__(self, *args, **kwargs):
        super().__init__(get_local_config_file(__file__), *args, **kwargs)

    def _triggered(self, job_name: str, post_json: dict, run_identifier: RunIdentifier, *args):
        if job_name != 'execute':
            raise ValueError('The only job name supported is execute')
        self.__start_analysis()

    def __start_analysis(self):
        """
        https://axonius.atlassian.net/browse/AX-4020
        """
        now = datetime.utcnow()
        old_threshold = now - timedelta(days=7)
        new_threshold = now - timedelta(days=2)

        count_of_labels = 0

        for associated_devices in self.__get_devices_by_macs().values():
            if len(associated_devices) < 2:
                continue

            # relatively "old" adapters
            older_adapter_devices = [adapter_device
                                     for date, adapter_device
                                     in associated_devices
                                     if date <= old_threshold]

            # relatively "new" adapters
            newer_adapter_devices = [adapter_device
                                     for date, adapter_device
                                     in associated_devices
                                     if date >= new_threshold
                                     and adapter_device['data'].get('hostname')]

            if not older_adapter_devices or not newer_adapter_devices:
                continue

            hostnames = set()
            for adapter_device in newer_adapter_devices:
                hostnames.add(tuple(normalize_hostname(adapter_device['data'])))

            unique_hostnames = set(hostnames)

            for host1, host2 in itertools.combinations(hostnames, 2):
                if compare_normalized_hostnames(host1, host2):  # but actually they are the same logically
                    # remove the shorter
                    unique_hostnames.discard(min(host1, host2, key=len))
            del hostnames

            for older_adapter_device in older_adapter_devices:
                for hostname in unique_hostnames:
                    tagname = '.'.join(hostname)
                    tagname = f'Reimaged by {tagname}'
                    adapter_identity = [(older_adapter_device[PLUGIN_UNIQUE_NAME], older_adapter_device['data']['id'])]
                    self.add_label_to_entity(EntityType.Devices, adapter_identity, tagname)
                count_of_labels += 1

        logger.info(f'Performed {count_of_labels} labels, thresholds are - {old_threshold}, {new_threshold}')

    def __get_devices_by_macs(self) -> DefaultDict[str, List[Tuple[datetime, dict]]]:
        """
        Returns a dict between mac to list of associated adapter devices and their max_last_seen
        """
        # mac -> list of associated adapter devices and their max_last_seen
        macs: DefaultDict[str, List[Tuple[datetime, dict]]] = defaultdict(list)

        for axonius_device in list(self.devices_db.find(
                parse_filter('((specific_data.data.network_interfaces.manufacturer == exists(true) and not '
                             'specific_data.data.network_interfaces.manufacturer == type(10)) and '
                             'specific_data.data.network_interfaces.manufacturer != "") and '  # mac manufacturer exists
                             '((specific_data.data.hostname == exists(true) and not '
                             'specific_data.data.hostname == type(10)) and '
                             'specific_data.data.hostname != "") and '  # hostname exists
                             '(specific_data.data.last_seen == exists(true) and not '
                             'specific_data.data.last_seen == type(10)) and '  # last_seen exists
                             f'specific_data.data.adapter_properties == "{AdapterProperty.Agent.name}"'),  # Agent
                projection={
                    '_id': False,
                    'adapters.data.network_interfaces.mac': True,
                    'adapters.data.hostname': True,
                    'adapters.data.last_seen': True,
                    'adapters.data.adapter_properties': True,
                    f'adapters.{PLUGIN_UNIQUE_NAME}': True,
                    f'adapters.data.id': True
                })):
            max_last_seen = max(axonius_device['adapters'],
                                key=lambda x: x['data'].get(LAST_SEEN_FIELD, datetime.min))['data'].get(LAST_SEEN_FIELD)
            if not max_last_seen:
                # Not dealing with those that don't have any last_seen
                continue

            for adapter_device in axonius_device['adapters']:
                # Ignore non-agents
                if AdapterProperty.Agent.name not in adapter_device['data']['adapter_properties']:
                    continue

                for ni in adapter_device['data'].get('network_interfaces') or []:
                    mac = ni.get('mac')
                    if mac:
                        macs[mac].append((max_last_seen, adapter_device))
        return macs

    @property
    def plugin_subtype(self) -> PluginSubtype:
        return PluginSubtype.PostCorrelation
