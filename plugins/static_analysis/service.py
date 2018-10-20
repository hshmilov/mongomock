import logging
import threading
from datetime import datetime
from typing import Iterable, Tuple, Dict

from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.triggers.interval import IntervalTrigger
from axonius.consts.plugin_subtype import PluginSubtype

from axonius.background_scheduler import LoggedBackgroundScheduler
from axonius.consts.plugin_consts import PLUGIN_NAME, PLUGIN_UNIQUE_NAME
from axonius.devices.device_adapter import DeviceAdapter
from axonius.mixins.triggerable import Triggerable
from axonius.plugin_base import PluginBase
from axonius.utils.files import get_local_config_file

from static_analysis.nvd_nist.nvd_search import NVDSearcher

logger = logging.getLogger(f'axonius.{__name__}')

NVD_DB_UPDATE_HOURS = 12  # amount of hours after of which we update the db, if possible


def _get_id_and_associated_adapter(adapter_device) -> Tuple[str, object]:
    """
    For every adapter entity we process we must create an adapterdata (tag).
    That tag must have an ID and also a list of associated_adapters.
    The associated_adapters vary between two cases, described in the comment in the code.
    :param adapter_device: the adapter device to receive the identifications for
    :return: tuple of (id) and (associated_adapters)
    """
    _id = adapter_device[PLUGIN_UNIQUE_NAME] + ',' + adapter_device['data']['id']
    associated_adapters = adapter_device.get('associated_adapters')
    if not associated_adapters:
        # If `associated_adapters` are part of the original device than this device
        # is actually an adapterdata so we shall inherit its
        # associated_adapters for consistency - we will be associated with the same adapter
        # as it is.
        # Otherwise the adapter is not an adapterdata but rather is a real adapters,
        # thus we want to be associated with it.
        associated_adapters = [(adapter_device[PLUGIN_UNIQUE_NAME],
                                adapter_device['data']['id'])]
    return _id, associated_adapters


class StaticAnalysisService(PluginBase, Triggerable):
    class MyDeviceAdapter(DeviceAdapter):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(get_local_config_file(__file__), *args, **kwargs)
        self.__nvd_lock = threading.Lock()

        self.__nvd_searcher = NVDSearcher()
        self.__scheduler = LoggedBackgroundScheduler(executors={'default': ThreadPoolExecutor(1)})
        self.__scheduler.add_job(
            func=self.__update_nvd_db,
            trigger=IntervalTrigger(hours=NVD_DB_UPDATE_HOURS),
            next_run_time=datetime.now(),
            name='update_nvd_db',
            id='update_nvd_db_thread',
            max_instances=1)

    def __update_nvd_db(self):
        try:
            with self.__nvd_lock:
                logger.info('Update NVD started')
                self.__nvd_searcher.update()
                logger.info('Update NVD complete')
        except Exception:
            logger.exception('Exception while updating')

    def _triggered(self, job_name: str, post_json: dict, *args):
        if job_name != 'execute':
            raise ValueError('The only job name supported is execute')
        self.__start_analysis()

    def __start_analysis(self):
        try:
            self.__analyze_cves()
        except Exception:
            logger.exception('Exception while trying to analyze cves')

    def __analyze_cves(self):
        """
        Analyses all devices that have some installed software on them and looks for software
        that have known CVEs from the NVD. Tags those devices with the appropriate tags.
        """
        # We can divide all devices into two groups:
        # 1. those that have at least one 'specific_data.data.installed_software.name'
        # 2. those that don't
        # if we deal with both groups we deal with all devices.

        # dealing with group (1)
        # those devices must be processed - i.e. to find any CVEs in them and tag appropriately.
        with self.__nvd_lock:
            # filter to find only devices with any installed software
            for device in self.devices_db_view.find(
                    {
                        'specific_data.data.installed_software.name': {
                            '$exists': True
                        }
                    }):
                self.__process_devices(device)

        # find all devices that -
        # 1. are part of group (2)
        # 2. also have been tagged by us, and we have given it some CVE
        # imagine the case that some axonius device that used to have installed_software
        # and them we tagged it with some CVE.
        # then that device looses its installed_software, so the previous loop won't find it, then the CVE
        # will never be untagged!
        # this loop will find those devices and search them :)
        with self.__nvd_lock:
            for device in self.devices_db_view.find(
                    {
                        'specific_data.data.installed_software.name': {
                            '$exists': False
                        },
                        'specific_data': {
                            '$elemMatch': {
                                '$and': [
                                    {
                                        PLUGIN_NAME: self.plugin_name,
                                    },
                                    {
                                        'data.software_cves': {
                                            '$exists': True
                                        }
                                    },
                                    {
                                        'data.software_cves': {'$ne': []}
                                    }
                                ]
                            }
                        }
                    }):
                self.__process_devices(device)

    def __process_devices(self, device) -> None:
        """
        Given an axonius devices, tag it with the appropriate CVEs.
        """
        try:
            for adapter_device in device.get('specific_data', []):
                # don't run on ourselves
                if adapter_device[PLUGIN_NAME] == self.plugin_name:
                    continue

                # this includes both real devices and virtual devices from other plugins
                created_device = self._new_device_adapter()
                _id, associated_adapters = _get_id_and_associated_adapter(adapter_device)
                created_device.id = _id
                created_device.software_cves = []

                installed_software = adapter_device['data'].get('installed_software', [])

                for found_cve in self.__process_installed_software(installed_software):
                    created_device.add_vulnerable_software(**found_cve)

                # Add the final one
                self.devices.add_adapterdata(
                    associated_adapters,
                    created_device.to_dict(),
                    action_if_exists='update',
                    # If the tag exists, we update it using deep merge (and not replace it).
                    client_used=adapter_device.get('client_used'),
                    additional_data={
                        'hidden_for_gui': True
                    }
                )
        except Exception:
            logger.exception(f'Exception while processing device {device}')

    def __process_installed_software(self, installed_software: Iterable[Dict]) -> Iterable[dict]:
        """
        Processes all installed softwares and returns all CVEs found in those softwares
        :param installed_software: Iterable of tuples from DB, the tuples represent DeviceAdapterInstalledSoftware
        :return: yields dicts that each represent a DeviceAdapterSoftwareCVE
        """
        for software in installed_software:
            software_vendor = software.get('vendor') or ''
            software_name = software.get('name') or ''
            software_version = software.get('version') or ''

            try:
                # We want all of our params to be strings, and only strings. but, software_vendor might be empty,
                # so our conditions will be:
                # software_vendor, software_name, and software_version are strings
                # software_name, software_version are not empty strings.

                if not all(isinstance(x, str) for x in (software_vendor, software_name, software_version)):
                    # Sometimes, that happens.
                    logger.error(f'Error: installed software contains not strings: {installed_software}')
                    continue

                if not software_name or not software_version:
                    # Sometimes, that also happens.
                    # do note that we allow empty software_vendor as some adapters do not give it.
                    logger.error(f'Error: installed software contains name/version empty strings: {installed_software}')
                    continue

                if 'microsoft' in software_vendor.lower() and 'office' in software_name.lower():
                    # Microsoft Office is not supported since the CVE's there are too broad.
                    # e.g. https://portal.msrc.microsoft.com/en-US/security-guidance/advisory/CVE-2018-8161
                    # is a cve for all versions of Office 2016. This could lead to many false-positives.
                    # However we do get information about patches for office and other microsoft products from
                    # our patch management modules.
                    continue

                for cve in self.__nvd_searcher.search_vuln(software_vendor, software_name, software_version):
                    try:
                        cve_id = cve['id']
                        cve_description = cve.get('description')
                        cve_references = cve.get('references')
                        cve_severity = cve.get('severity')
                        yield dict(
                            software_vendor=software_vendor,
                            software_name=software_name,
                            software_version=software_version,
                            cve_id=cve_id,
                            cve_description=cve_description,
                            cve_references=cve_references,
                            cve_severity=cve_severity
                        )
                    except Exception:
                        logger.exception(
                            f'Exception parsing cve {cve} for {software_vendor}:{software_name}:{software_version}')
            except Exception:
                logger.exception(
                    f'Exception while searching for vuln for {software_vendor}:{software_name}:{software_version}')

    @property
    def plugin_subtype(self) -> PluginSubtype:
        return PluginSubtype.PostCorrelation
