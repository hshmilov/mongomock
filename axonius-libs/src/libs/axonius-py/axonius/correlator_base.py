import logging
import multiprocessing
import threading
from abc import ABC, abstractmethod
from multiprocessing.dummy import Pool as ThreadPool

from axonius.devices.device_adapter import (MAC_FIELD,
                                            NETWORK_INTERFACES_FIELD, OS_FIELD)
from axonius.entities import EntityType
from axonius.mixins.feature import Feature
from axonius.mixins.triggerable import Triggerable
from axonius.plugin_base import PluginBase
from axonius.thread_stopper import stoppable
from funcy import chunks
from namedlist import namedlist

from axonius.types.correlation import CorrelationResult

logger = logging.getLogger(f'axonius.{__name__}')

"""
Represents a warning that should be passed on to the GUI.
"""
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


def has_serial(adapters):
    # not none
    return does_entity_have_field(adapters, lambda adapter_data: (adapter_data.get('device_serial'))) or \
        does_entity_have_field(adapters, lambda adapter_data: (adapter_data.get('bios_serial')))


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


class CorrelatorBase(PluginBase, Triggerable, Feature, ABC):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._correlation_lock = threading.RLock()

    @classmethod
    def specific_supported_features(cls) -> list:
        return ["Correlator"]

    def _triggered(self, job_name, post_json, *args):
        """
        Returns any errors as-is.
        Post data is a list of axon-ids. Otherwise, will query DB-wise.
        :return:
        """
        if job_name != 'execute':
            raise ValueError("The only job name supported is execute")

        entities_to_correlate = None
        if post_json is not None:
            entities_to_correlate = list(post_json)
        acquired = False
        try:
            acquired = self._correlation_lock.acquire(False)
            if acquired:
                self.__correlate(entities_to_correlate)
            else:
                raise RuntimeError("Correlation is already taking place, try again later")
        finally:
            if acquired:
                self._correlation_lock.release()

    def get_entities_from_ids(self, entities_ids=None):
        """
        Virtual by design.
        Gets entities by their axonius ID.
        :param entities_ids:
        :return:
        """
        db = self._entity_db_map[self._entity_to_correlate]
        if entities_ids:
            return list(db.find({
                'internal_axon_id': {
                    "$in": entities_ids
                }
            }))

        return list(db.find({}))

    @stoppable
    def __correlate(self, entities_ids=None):
        """
        Correlate and process entities
        :param entities_ids:
        :return:
        """
        entities_to_correlate = self.get_entities_from_ids(entities_ids)
        logger.info(
            f"Correlator {self.plugin_unique_name} started to correlate {len(entities_to_correlate)} entities")
        pool = ThreadPool(processes=2 * multiprocessing.cpu_count())

        def process_correlation_result(result):
            if isinstance(result, CorrelationResult):
                try:
                    self.link_adapters(self._entity_to_correlate, result)
                except Exception:
                    logger.exception(f'Failed linking for some reason, {result}')
            if isinstance(result, WarningResult):
                logger.warn(f"{result.title}, {result.content}: {result.notification_type}")
                self.create_notification(result.title, result.content, result.notification_type)
                return

        pool.map_async(process_correlation_result, self._correlate_with_lock(entities_to_correlate))
        logger.info("Waiting for correlation")
        pool.close()
        pool.join()
        logger.info("Done!")
        self._request_db_rebuild(sync=False)

    def _correlate_with_lock(self, entities: list):
        """
        Some primitive filters
        Just calls _correlate with a lock
        """
        with self._correlation_lock:
            return self._correlate(entities)

    @property
    @abstractmethod
    def _entity_to_correlate(self) -> EntityType:
        """
        Which type of entity to correlate.
        This decides which DB the correlator will look at.
        """
        pass

    @abstractmethod
    def _correlate(self, entities: list):
        """
        Correlate using the given entities
        :param entities: list of full axonius entities (not entities IDs!)
        :return: list(CorrelationResult or WarningResult)
        """
        pass

    @property
    def plugin_subtype(self):
        return "Correlator"
