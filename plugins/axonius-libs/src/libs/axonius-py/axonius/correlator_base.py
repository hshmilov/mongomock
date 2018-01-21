import threading
from abc import ABC, abstractmethod
from datetime import datetime

from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.triggers.interval import IntervalTrigger
from namedlist import namedlist

from axonius.background_scheduler import LoggedBackgroundScheduler
from axonius.plugin_base import PluginBase
from axonius.mixins.activatable import Activatable
from axonius.mixins.triggerable import Triggerable
from axonius.mixins.feature import Feature
from axonius.consts.plugin_consts import AGGREGATOR_PLUGIN_NAME

# the reason for these data types is that it allows separation of the code that figures out correlations
# and code that links devices (aggregator) or sends notifications.
"""
Represent a link that should take place.

associated_adapter_devices  - tuple between unique adapter name and id, e.g.
    (
        ("aws_adapter_30604", "i-0549ca2d6c2e42a70"),
        ("esx_adapter_14575", "527f5691-de18-6657-783e-56fd1a5322cd")
    )

data                        - associated data with this link, e.g. {"reason": "they look the same"}
reason                      - 'Execution' or 'Logic' or whatever else correlators will use
                              'Execution' means the second part has plugin_name
                              'Logic' means the second part has plugin_unique_name
"""
CorrelationResult = namedlist('CorrelationResult', ['associated_adapter_devices', 'data', ('reason', 'Execution')])

"""
Represents a warning that should be passed on to the GUI.
"""
WarningResult = namedlist('WarningResult', ['title', 'content', ('notification_type', 'basic')])


class OSTypeInconsistency(Exception):
    pass


class UnsupportedOS(Exception):
    pass


def is_scanner_device(adapters):
    for device_info in adapters:
        if device_info['data'].get('scanner'):
            return True
    return False


def figure_actual_os(adapters):
    """
    Figures out the OS of the device according to the adapters.
    If they aren't consistent about the OS, return None
    :param adapters: list
    :return:
    """

    def get_os_type(adapter):
        os = adapter.get('OS')
        if os is not None:
            return os.get('type')

    oses = list(set(get_os_type(adapter['data']) for adapter in adapters))

    if None in oses:
        # None might be in oses if at least one adapter couldn't figure out the OS,
        # if all other adapters are consistent regarding the OS - we accept it
        oses.remove(None)

    if len(oses) == 0:
        return None  # no adapters know anything - we have no clue which OS the device is running

    if len(oses) == 1:
        return oses[0]  # no adapters disagree (except maybe those which don't know)

    raise OSTypeInconsistency(oses)  # some adapters disagree


class CorrelatorBase(PluginBase, Activatable, Triggerable, Feature, ABC):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._correlation_scheduler = None

        self._correlation_lock = threading.RLock()
        self._refresh_devices_filter()

    @classmethod
    def specific_supported_features(cls) -> list:
        return ["Correlator"]

    def _refresh_devices_filter(self):
        """
        in "correlator_xxx:filter" will always be one (or none, which means default) document that
        will represent the mongodb query to apply over the devices when correlating.
        this can be used to set up a correlator that will only correlate a subset of the devices
        :return:
        """
        collection = self._get_collection("filter")
        self._devices_filter = collection.find_one()
        if self._devices_filter is None:
            self._devices_filter = {}

    def _start_activatable(self):
        """
        Start the scheduler
        :return:
        """
        self._refresh_devices_filter()

        assert self._correlation_scheduler is None, "Correlation is already scheduled"

        executors = {'default': ThreadPoolExecutor(1)}
        self._correlation_scheduler = LoggedBackgroundScheduler(self.logger, executors=executors)
        self._correlation_scheduler.add_job(func=self.__correlate,
                                            trigger=IntervalTrigger(hours=2),
                                            next_run_time=datetime.now(),
                                            name='correlation',
                                            id='correlation',
                                            max_instances=1)
        self._correlation_scheduler.start()

    def _stop_activatable(self):
        """
        Stop the scheduler
        :return:
        """
        assert self._correlation_scheduler is not None, "Correlation is not running"

        self._correlation_scheduler.remove_all_jobs()
        self._correlation_scheduler.shutdown(wait=True)
        self._correlation_scheduler = None

    def _is_work_in_progress(self) -> bool:
        if self._correlation_lock.acquire(False):
            self._correlation_lock.release()
            return False
        return True

    def _triggered(self, job_name, post_json, *args):
        """
        Returns any errors as-is.
        Post data is a list of axon-ids. Otherwise, will query DB-wise.
        :return:
        """
        devices_to_correlate = None
        if post_json is not None:
            devices_to_correlate = list(post_json)
        acquired = False
        try:
            if self._correlation_lock.acquire(False):
                acquired = True
                self.__correlate(devices_to_correlate)
            else:
                raise RuntimeError("Correlation is already taking place, try again later")
        finally:
            if acquired:
                self._correlation_lock.release()

    def get_devices_from_ids(self, devices_ids=None):
        """
        Virtual by design.
        Gets devices by their axonius ID.
        :param devices_ids:
        :return:
        """
        with self._get_db_connection(True) as db:
            aggregator_db = db[AGGREGATOR_PLUGIN_NAME]
            if devices_ids is None:
                return list(aggregator_db['devices_db'].find(self._devices_filter))
            else:
                return list(aggregator_db['device_db'].find({
                    'internal_axon_id': {
                        "$in": devices_ids
                    }
                }))

    def __correlate(self, devices_ids=None):
        """
        Correlate and process devices
        :param devices_ids:
        :return:
        """
        devices_to_correlate = self.get_devices_from_ids(devices_ids)
        self.logger.info(
            f"Correlator {self.plugin_unique_name} started to correlate {len(devices_to_correlate)} devices")
        for result in self._correlate_with_lock(devices_to_correlate):
            if isinstance(result, WarningResult):
                self.logger.warn(f"{result.title}, {result.content}: {result.notification_type}")
                self.create_notification(result.title, result.content, result.notification_type)

            if isinstance(result, CorrelationResult):
                self.logger.debug(f"Correlation: {result.data}, for {dict(result.associated_adapter_devices)}")
                self.request_remote_plugin('plugin_push', AGGREGATOR_PLUGIN_NAME, 'post', json={
                    "plugin_type": "Plugin",
                    "data": result.data,
                    "associated_adapter_devices": dict(result.associated_adapter_devices),
                    "association_type": "Link"
                })

    def _correlate_with_lock(self, devices: list):
        """
        Some primitive filters
        Just calls _correlate with a lock
        """
        with self._correlation_lock:
            return self._correlate(devices)

    @abstractmethod
    def _correlate(self, devices: list):
        """
        Correlate using the given devices
        :param devices: list of full axonius devices (not devices IDs!)
        :return: list(CorrelationResult or WarningResult)
        """
        pass
