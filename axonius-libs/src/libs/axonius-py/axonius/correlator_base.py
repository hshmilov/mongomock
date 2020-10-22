import logging
from abc import ABC, abstractmethod
from multiprocessing import cpu_count
from multiprocessing.dummy import Pool as ThreadPool

from namedlist import namedlist

from axonius.consts.plugin_subtype import PluginSubtype
from axonius.devices.device_adapter import (MAC_FIELD,
                                            NETWORK_INTERFACES_FIELD, OS_FIELD)
from axonius.entities import EntityType
from axonius.mixins.feature import Feature
from axonius.mixins.triggerable import Triggerable, RunIdentifier
from axonius.plugin_base import PluginBase
from axonius.types.correlation import CorrelationResult
from axonius.utils.db_querying_helper import iterate_axonius_entities

logger = logging.getLogger(f'axonius.{__name__}')

'''
Represents a warning that should be passed on to the GUI.
'''
WarningResult = namedlist('WarningResult', ['title', 'content', ('notification_type', 'basic')])


class OSTypeInconsistency(Exception):
    pass


class UnsupportedOS(Exception):
    pass


def does_entity_have_field(adapters, check_data):
    return any(check_data(entity_info['data']) for entity_info in adapters)


def has_name(adapters):
    return does_entity_have_field(adapters, lambda adapter_data: 'name' in adapter_data)


def has_hostname(adapters):
    return does_entity_have_field(adapters, lambda adapter_data: 'hostname' in adapter_data)


def has_resource_id(adapters):
    return does_entity_have_field(adapters, lambda adapter_data: 'resource_id' in adapter_data)


def has_nessus_scan_no_id(adapters):
    return does_entity_have_field(adapters, lambda adapter_data: 'nessus_no_scan_id' in adapter_data)


def has_serial(adapters):
    # not none
    return does_entity_have_field(adapters, lambda adapter_data: (adapter_data.get('device_serial'))) or \
        does_entity_have_field(adapters, lambda adapter_data: (adapter_data.get('bios_serial')))


def has_public_ips(adapters):
    return does_entity_have_field(adapters, lambda adapter_data: adapter_data.get('public_ips'))


def has_last_used_users(adapters):
    return does_entity_have_field(adapters, lambda adapter_data: adapter_data.get('last_used_users'))  # not none


def has_cloud_id(adapters):
    return does_entity_have_field(adapters, lambda adapter_data: adapter_data.get('cloud_id'))  # not none


def has_ad_or_azure_name(adapters):
    # not none
    return does_entity_have_field(adapters, lambda adapter_data: (adapter_data.get('ad_name'))) or \
        does_entity_have_field(adapters, lambda adapter_data: (adapter_data.get('azure_display_name')))


def has_mac(adapters):
    return does_entity_have_field(adapters, _has_mac)


def _has_mac(adapter_data):
    return any(nic.get(MAC_FIELD) for nic in adapter_data.get(NETWORK_INTERFACES_FIELD) or [])


def figure_actual_os(adapters):
    """
    Figures out the OS of the entity according to the adapters.
    If they aren't consistent about the OS, return None
    :param adapters: list
    :return:
    """

    def get_os_type(adapter):
        os = adapter.get(OS_FIELD)
        if os is not None:
            return os.get('type')
        return None

    oses = list(set(get_os_type(adapter['data']) for adapter in adapters))

    if None in oses:
        # None might be in oses if at least one adapter couldn't figure out the OS,
        # if all other adapters are consistent regarding the OS - we accept it
        oses.remove(None)

    if len(oses) == 0:
        return None  # no adapters know anything - we have no clue which OS the entity is running

    if len(oses) == 1:
        return oses[0]  # no adapters disagree (except maybe those which don't know)

    raise OSTypeInconsistency(oses)  # some adapters disagree


class CorrelatorBase(Triggerable, PluginBase, Feature, ABC):
    @classmethod
    def specific_supported_features(cls) -> list:
        return ['Correlator']

    def _triggered(self, job_name, post_json, run_identifier: RunIdentifier, *args):
        """
        Returns any errors as-is.
        Post data is a list of axon-ids. Otherwise, will query DB-wise.
        :return:
        """
        if job_name == 'execute':
            entities_to_correlate = None
            if post_json is not None:
                entities_to_correlate = list(post_json)
            return self.__correlate(entities_to_correlate)

        if job_name == 'detect_errors':
            return self.detect_errors(should_fix_errors=bool((post_json or {}).get('should_fix_errors')))

        raise ValueError('The only job name supported is execute')

    def get_entities_from_ids(self, entities_ids=None):
        """
        Virtual by design.
        Gets entities by their axonius ID.
        :param entities_ids:
        :return:
        """
        db = self._entity_db_map[self._entity_to_correlate]
        if entities_ids:
            return list(iterate_axonius_entities(self._entity_to_correlate, entities_ids))

        return list(db.find({}))

    def _process_correlation_result(self, result):
        """ for each correlation link the adapter
            :param result: should  be _correlate result
        """
        if isinstance(result, CorrelationResult):
            try:
                self.link_adapters(self._entity_to_correlate, result)
            except Exception:
                logger.debug(f'Failed linking for some reason, {result}', exc_info=True)
        if isinstance(result, WarningResult):
            logger.warning(f'{result.title}, {result.content}: {result.notification_type}')
            self.create_notification(result.title, result.content, result.notification_type)

    def _map_correlation(self, entities_to_correlate):
        """ for each entity process it and link adapters """
        with ThreadPool(processes=2 * cpu_count()) as pool:
            logger.info('Waiting for correlation')
            pool.map(self._process_correlation_result, self._correlate(entities_to_correlate))
            logger.info('Done!')

    def __correlate(self, entities_ids=None):
        """
        Correlate and process entities
        :param entities_ids:
        :return:
        """
        logger.info(f'Correlator {self.plugin_unique_name} getting entities')
        entities_to_correlate = self.get_entities_from_ids(entities_ids)
        logger.info(
            f'Correlator {self.plugin_unique_name} started to correlate {len(entities_to_correlate)} entities')
        self._map_correlation(entities_to_correlate)

    def detect_errors(self, should_fix_errors: bool):
        """
        If implemented, will respond to 'detect_errors' triggers, and will detect errors on made correlations
        :param should_fix_errors: Whether or not to try to fix the errors
        """

    @property
    @abstractmethod
    def _entity_to_correlate(self) -> EntityType:
        """
        Which type of entity to correlate.
        This decides which DB the correlator will look at.
        """

    @abstractmethod
    def _correlate(self, entities: list):
        """
        Correlate using the given entities
        :param entities: list of full axonius entities (not entities IDs!)
        :return: list(CorrelationResult or WarningResult)
        """

    @property
    def plugin_subtype(self) -> PluginSubtype:
        return PluginSubtype.Correlator
