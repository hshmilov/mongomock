import logging

from axonius.entities import EntityType

logger = logging.getLogger(f'axonius.{__name__}')
from axonius.thread_stopper import stoppable
from funcy import chunks
import threading
import multiprocessing
from abc import ABC, abstractmethod

from namedlist import namedlist

from axonius.devices.device_adapter import MAC_FIELD, OS_FIELD, NETWORK_INTERFACES_FIELD
from axonius.plugin_base import PluginBase
from axonius.mixins.triggerable import Triggerable
from axonius.mixins.feature import Feature
from axonius.consts.plugin_consts import AGGREGATOR_PLUGIN_NAME
from enum import Enum, auto
from multiprocessing.dummy import Pool as ThreadPool

DEFAULT_SEND_TO_AGGREGATOR_CHUNK_SIZE = 100


class CorrelationReason(Enum):
    Execution = auto()
    Logic = auto()
    NonexistentDeduction = auto()  # Associativity over a nonexisting entity (a->b and b->c therefore a->c)
    StaticAnalysis = auto()


# the reason for these data types is that it allows separation of the code that figures out correlations
# and code that links entities (aggregator) or sends notifications.
"""
Represent a link that should take place.

associated_adapters  - tuple between unique adapter name and id, e.g.
    (
        ("aws_adapter_30604", "i-0549ca2d6c2e42a70"),
        ("esx_adapter_14575", "527f5691-de18-6657-783e-56fd1a5322cd")
    )

data                        - associated data with this link, e.g. {"reason": "they look the same"}
reason (CorrelationReason)  - 'Execution' or 'Logic' or whatever else correlators will use
                              'Logic' means the second part has plugin_unique_name
                              Anything else means the second part has plugin_name
"""
CorrelationResult = namedlist('CorrelationResult',
                              ['associated_adapters', 'data', ('reason', CorrelationReason.Execution)])

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


def has_hostname(adapters):
    return does_entity_have_field(adapters, lambda adapter_data: 'hostname' in adapter_data)


def has_serial(adapters):
    return does_entity_have_field(adapters, lambda adapter_data: adapter_data.get('device_serial'))  # not none


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

        self._correlation_scheduler = None

        self._correlation_lock = threading.RLock()
        self._refresh_entities_filter()

    @classmethod
    def specific_supported_features(cls) -> list:
        return ["Correlator"]

    def _refresh_entities_filter(self):
        """
        in "correlator_xxx:filter" will always be one (or none, which means default) document that
        will represent the mongodb query to apply over the entities when correlating.
        this can be used to set up a correlator that will only correlate a subset of the entities
        :return:
        """
        collection = self._get_collection("filter")
        self._entities_filter = collection.find_one()
        if self._entities_filter is None:
            self._entities_filter = {}

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
        if entities_ids is None:
            return list(db.find(self._entities_filter))
        else:
            return list(db.find({
                'internal_axon_id': {
                    "$in": entities_ids
                }
            }))

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

        def multilink(correlations):
            self.request_remote_plugin('multi_plugin_push', AGGREGATOR_PLUGIN_NAME, 'post', json=[{
                "plugin_type": "Plugin",
                "data": result.data,
                "associated_adapters": result.associated_adapters,
                "association_type": "Link",
                "entity": self._entity_to_correlate.value
            } for result in correlations])

        for chunk in chunks(DEFAULT_SEND_TO_AGGREGATOR_CHUNK_SIZE, self._correlate_with_lock(entities_to_correlate)):
            for result in chunk:
                if isinstance(result, WarningResult):
                    logger.warn(f"{result.title}, {result.content}: {result.notification_type}")
                    self.create_notification(result.title, result.content, result.notification_type)
            correlations = [r for r in chunk if isinstance(r, CorrelationResult)]
            for result in correlations:
                logger.debug(f"Correlation: {result.data}, for {result.associated_adapters}")
            logger.info(f"Sending {len(correlations)} correlation to aggregator async")
            pool.apply_async(multilink, args=[correlations])
        logger.info("Waiting for aggregator...")
        pool.close()
        pool.join()
        logger.info("Done!")

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
