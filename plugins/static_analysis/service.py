import logging
import threading
import uuid
from collections import defaultdict
from datetime import datetime
from typing import Iterable, Tuple, Dict, List

import cachetools
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.triggers.interval import IntervalTrigger

from axonius.background_scheduler import LoggedBackgroundScheduler
from axonius.consts import adapter_consts
from axonius.entities import EntityType, AxoniusUser

from axonius.consts.plugin_subtype import PluginSubtype

from axonius.consts.plugin_consts import PLUGIN_NAME, PLUGIN_UNIQUE_NAME
from axonius.devices.device_adapter import DeviceAdapter
from axonius.mixins.triggerable import Triggerable, RunIdentifier
from axonius.plugin_base import PluginBase
from axonius.users.user_adapter import UserAdapter, ASSOCIATED_FIELD
from axonius.utils.axonius_query_language import convert_db_entity_to_view_entity
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import is_valid_user

from static_analysis.nvd_nist.nvd_search import NVDSearcher
from static_analysis.consts import AnalysisTypes, JOB_NAMES

logger = logging.getLogger(f'axonius.{__name__}')

NVD_DB_UPDATE_HOURS = 12  # amount of hours after of which we update the db, if possible
LIST_OF_DEFAULT_USERS = ['', 'n/a', 'none', 'guest', 'administrator', 'admin', 'unknown']


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


class StaticAnalysisService(Triggerable, PluginBase):
    class MyDeviceAdapter(DeviceAdapter):
        pass

    class MyUserAdapter(UserAdapter):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(get_local_config_file(__file__), *args, **kwargs)
        self.__nvd_lock = threading.Lock()

        self.__nvd_searcher = NVDSearcher()

        # Currently commented out due to AX-9249 (NVD changing their API)
        self.__scheduler = LoggedBackgroundScheduler(executors={'default': ThreadPoolExecutor(1)})
        self.__scheduler.add_job(
            func=self.__update_nvd_db,
            trigger=IntervalTrigger(hours=NVD_DB_UPDATE_HOURS),
            next_run_time=datetime.now(),
            name='update_nvd_db',
            id='update_nvd_db_thread',
            max_instances=1)
        self.__scheduler.start()

        self.__jobs = AnalysisTypes(user_devices_association=self.__associate_users_with_devices,
                                    last_used_user_association=self.__parse_devices_last_used_users_departments,
                                    virtual_host=self.__add_virtual_host,
                                    cve_enrichment=self.__add_enriched_cve_data)

    def __update_nvd_db(self):
        try:
            with self.__nvd_lock:
                logger.info('Update NVD started')
                self.__nvd_searcher.update()
                logger.info('Update NVD complete')
        except Exception:
            logger.exception('Exception while updating')

    def _triggered(self, job_name: str, post_json: dict, run_identifier: RunIdentifier, *args):
        if job_name not in JOB_NAMES:
            raise ValueError(f'The only job names supported are {JOB_NAMES}')

        logger.info(f'Static Analysis triggered {job_name}')

        if job_name == 'execute':
            triggers = self.__jobs._fields
        else:
            triggers = (job_name, )

        self.__start_analysis(triggers)

        logger.info('Static Analysis trigger Finished')

    def __start_analysis(self, job_names):
        jobs = {k: v for k, v in self.__jobs._asdict().items() if k in job_names}

        for name, callback in jobs.items():
            try:
                logger.info(f'Static Analysis: Calling {name}')
                callback()
                logger.info(f'Static Analysis: {name} finished')
            except Exception:
                logger.exception(f'Exception while calling job {name}')

    def _is_device_virtual(self, device_test):
        """
        Checks a specific devices if its a virtual host or not, made specially for testing,
        code replecated from __add_virtual_host
        :param device_test:
        :return: True if virtual host and False if not
        """
        devices_from_containers_adapter = list(self.devices_db.find(
            self.common.query.parse_aql_filter(
                '((adapters_data.esx_adapter.id == ({"$exists":true,"$ne":""}))) or'
                '((adapters_data.hyper_v_adapter.id == ({"$exists":true,"$ne":""}))) or'
                '((adapters_data.proxmox_adapter.id == ({"$exists":true,"$ne":""}))) or'
                '((adapters_data.nutanix_adapter.id == ({"$exists":true,"$ne":""})))'),
            batch_size=10
        ))
        if device_test in devices_from_containers_adapter:
            return True

        devices_with_vmware_manuf = self.devices_db.find(
            self.common.query.parse_aql_filter(
                '(specific_data.data.network_interfaces.mac == regex("^00:15:5D")) or '
                '(specific_data.data.network_interfaces.manufacturer == regex("^Nutanix")) or '
                '(specific_data.data.network_interfaces.manufacturer == regex("^VMware"))'),
            batch_size=10
        )
        for device in devices_with_vmware_manuf:
            if device != device_test:
                continue
            is_virtual = False
            non_vmware_count = 0
            vmware_count = 0
            for adapter in device['adapters']:
                nics = adapter['data'].get('network_interfaces')
                if not isinstance(nics, list) or nics == []:
                    continue
                for nic in nics:
                    if 'manufacturer' in nic and \
                        (nic['manufacturer'].startswith('Nutanix') or
                         nic['mac'].startswith('00:15:5D')):
                        non_vmware_count += 1
                        is_virtual = True
                    elif 'manufacturer' in nic and nic['manufacturer'].startswith('VMware'):
                        vmware_count += 1
                    else:
                        non_vmware_count += 1

            if is_virtual or (vmware_count > 0 and non_vmware_count == 0):
                return True

        return False

    def __add_virtual_host(self):
        """
        All devices correlated with at least one of the following adapter: ESX,Hyper-V,Proxmox or Nutanix
        are considered as virtual hosts
        All devices with specific MAC Vendor of a Hypervisor or container management software
        are considered as a virtual host.
        All the reset are not virtual hosts
        https://axonius.atlassian.net/browse/AX-6269
        https://github.com/proxmox/pve-common/blob/master/src/PVE/Tools.pm#L976 (No specific vendor for proxmox)
        https://support.microsoft.com/en-us/help/2804678/windows-hyper-v-server-has-a-default-limit-of-256-dynamic-mac-addresse
        https://portal.nutanix.com/#page/kbs/details?targetId=kA03200000099jkCAA
        """
        devices_from_containers_adapter = self.devices_db.find(
            self.common.query.parse_aql_filter(
                '((adapters_data.esx_adapter.id == ({"$exists":true,"$ne":""}))) or'
                '((adapters_data.hyper_v_adapter.id == ({"$exists":true,"$ne":""}))) or'
                '((adapters_data.proxmox_adapter.id == ({"$exists":true,"$ne":""}))) or'
                '((adapters_data.nutanix_adapter.id == ({"$exists":true,"$ne":""}))) or'
                '((adapters_data.azure_adapter.id == ({"$exists":true,"$ne":""}))) or '
                '((adapters_data.gce_adapter.id == ({"$exists":true,"$ne":""}))) or '
                '((adapters_data.aws_adapter.id == ({"$exists":true,"$ne":""})))'),
            batch_size=10
        )
        for device in devices_from_containers_adapter:
            self._update_virtual_host_to_device(device, True)

        devices_with_vmware_manuf = self.devices_db.find(
            self.common.query.parse_aql_filter(
                '(specific_data.data.network_interfaces.mac == regex("^00:15:5D")) or '
                '(specific_data.data.network_interfaces.manufacturer == regex("^Nutanix")) or '
                '(specific_data.data.network_interfaces.manufacturer == regex("^VMware"))'),
            batch_size=10
        )

        for device in devices_with_vmware_manuf:
            is_virtual = False
            non_vmware_count = 0
            vmware_count = 0
            for adapter in device['adapters']:
                nics = adapter['data'].get('network_interfaces')
                if not isinstance(nics, list) or nics == []:
                    continue
                for nic in nics:
                    if 'manufacturer' in nic and \
                        (nic['manufacturer'].startswith('Nutanix') or
                         nic['mac'].startswith('00:15:5D')):
                        non_vmware_count += 1
                        is_virtual = True
                    elif 'manufacturer' in nic and nic['manufacturer'].startswith('VMware'):
                        vmware_count += 1
                    else:
                        non_vmware_count += 1

            if is_virtual or (vmware_count > 0 and non_vmware_count == 0):
                self._update_virtual_host_to_device(device, True)

    def _update_virtual_host_to_device(self, device: dict, is_virtual: bool):
        try:
            device_adapter = self._new_device_adapter()
            device_adapter.virtual_host = is_virtual

            try:
                device_object = list(self.devices.get(internal_axon_id=device.get('internal_axon_id')))[0]
            except IndexError:
                logger.error(f'Error, Couldn\'t get the original device from '
                             f'mongo db {device.get("internal_axon_id")}')
                return

            device_object.add_adapterdata(device_adapter.to_dict(),
                                          action_if_exists='update',
                                          additional_data={'hidden_for_gui': True})
            # Update the device in mongo db
            self._save_field_names_to_db(EntityType.Devices)
        except Exception:
            logger.exception(f'Exception while trying to add virtual_host for device. Continuing')

    # pylint: disable=too-many-branches, inconsistent-return-statements
    def __add_enriched_cve_data(self):
        """
        This function will check for installed software and CVEs listed in a device's
        general data (software_cves)
        It will search the NIST NVD based on existing CVEs and enrich the device's software_cves
        with additional information like CVSS, severity, and affected software
        It maps installed software to CVEs, then searches the NIST NVD with those CVEs and adds
        them to the device with the corresponding installed software
        :return:
        """
        logger.info('Cve Enrichment Started')
        with self.__nvd_lock:
            # Filters and searches the database
            devices_with_cve = self.__get_devices_with_software_or_cves()
            for device in devices_with_cve:
                try:
                    # Create a device with the enriched cves
                    created_device = self.create_device_with_enriched_cves(device)
                    if not created_device:
                        logger.error(f'Error, did not parse device {device.get("internal_axon_id")}')
                        continue
                    # Get the original device from mongo db
                    try:
                        device_object = list(self.devices.get(internal_axon_id=device.get('internal_axon_id')))[0]
                    except IndexError:
                        logger.error(f'Error, Couldn\'t get the original device from '
                                     f'mongo db {device.get("internal_axon_id")}')
                        continue
                    # Add the enriched cve data from the created device to the one from mongo db
                    device_object.add_adapterdata(created_device.to_dict(),
                                                  action_if_exists='update',
                                                  additional_data={'hidden_for_gui': True})
                    # Update the device in mongo db
                    self._save_field_names_to_db(EntityType.Devices)
                except Exception:
                    logger.exception(f'Exception while trying to add cves for device. Continuing')
        logger.info('Cve Enrichment Ended')

    def create_device_with_enriched_cves(self, device):
        """
        This function creates a device adapter object that holds the enriched cves
        from the NVD search
        :param device: a device from the mongo db search
        :return: a DeviceAdapter object with enriched cves
        """
        try:
            device_id = device.get('internal_axon_id')
            if not device_id:
                logger.exception('Failed to get internal axon id for device')
                return
        except Exception:
            logger.exception('Failed to get internal axon id for device')
            return

        try:
            device_cves = []
            software_cves = []
            if not device.get('specific_data'):
                logger.info(f'Cannot get data for device {device}')
                return

            for adapter_data in device.get('specific_data') or []:
                # Don't run on a static analysis plugin tag

                # This check is what updates old tags for devices that, for example, have enriched
                # cves from an old run of static analysis but no longer report those cves
                # or installed software
                if adapter_data[PLUGIN_NAME] == self.plugin_name:
                    continue

                # Now search the NVD for enriched data
                adapter_specific_data = adapter_data.get('data') or {}
                if adapter_specific_data.get('software_cves'):
                    device_cves += self.__get_cve_data_from_device(adapter_specific_data=adapter_specific_data)
                if adapter_specific_data.get('installed_software'):
                    software_cves += self.__get_cve_data_from_installed_software(
                        adapter_specific_data=adapter_specific_data)

        except Exception:
            logger.exception(f'Problem getting cve data for device')
            return

        created_device = self._new_device_adapter()
        created_device.id = self.plugin_unique_name + '!' + 'cve' + '!' + device_id
        created_device.software_cves = []

        # Add the enriched cve data to a new DeviceAdapter object and return it
        if device_cves:
            for device_cve in device_cves:
                try:
                    if device_cve:
                        self.add_cve_data_to_device(created_device=created_device, cve_data=device_cve)
                except Exception:
                    logger.exception(f'Problem adding CVE data for {device_cve}')

        if software_cves:
            for software_cve in software_cves:
                try:
                    if software_cve:
                        self.add_cve_data_to_device(created_device=created_device, cve_data=software_cve)
                except Exception:
                    logger.exception(f'Problem adding CVE data for {software_cve}')

        return created_device
    # pylint: enable=too-many-branches, inconsistent-return-statements

    @staticmethod
    def add_cve_data_to_device(created_device, cve_data):
        """
        Will add the CVSS and severity ranking from version 3 of the CVSS if available,
        if not will use the version 2
        :param created_device: a new DeviceAdapter object
        :param cve_data: CVE data fetched from the NVD
        :return:
        """
        if not cve_data:
            return
        cvss = cve_data.get('cvss_v3') or cve_data.get('cvss_v2')
        cve_severity = cve_data.get('severity_v3') or cve_data.get('severity_v2')
        cvss_metric_version = 'v3.0' if cve_data.get('severity_v3') else 'v2.0'
        created_device.add_vulnerable_software(cve_id=cve_data.get('id'),
                                               cve_severity=cve_severity,
                                               cvss=cvss,
                                               cvss_version=cvss_metric_version,
                                               software_name=cve_data.get('software_name'),
                                               software_vendor=cve_data.get('software_vendor'))

    def __get_devices_with_software_or_cves(self):
        """
        This queries Axonius's database for devices we want to enrich with CVE data from the NVD
        :return:
        """
        # Since the process_devices operation can take a lot time, this can lead to a situation where
        # mongodb throws 'cursor not found' . This happens if we did not fetch a page from mongodb within 10 minutes
        # and this is possible if a page takes at least 10 minutes to process. a page, by default, is 100 documents.
        # to handle this we save all candidates' internal_axon_ids and then fetch them only when needed.

        # We want to run static analysis on devices that have one or both of the following:
        # a) The device's adapter reports CVEs (i.e. Shodan, Tenable SC) alone
        # b) The device has installed software and we can search for CVEs associated with it
        devices_with_cve_or_softwares = list(self.devices_db.find(
            self.common.query.parse_aql_filter(
                '(specific_data.data.software_cves.cve_id == ({"$exists":true,"$ne": ""})) '
                'or (specific_data.data.installed_software.name == ({"$exists":true,"$ne": ""}))'),
            projection={
                '_id': False,
                'internal_axon_id': True}
        ))

        devices_seen = set([])      # Don't want to enrich the same device twice
        for axon_id in devices_with_cve_or_softwares:
            if axon_id.get('internal_axon_id') in devices_seen:
                continue
            # Get the whole device and all its data from the database by searching with its internal axon id
            device = self.devices_db.find_one({'internal_axon_id': axon_id['internal_axon_id']})
            # XXX: somehow I got error where device is None
            if not device:
                logger.debug(f'internal_axon_id {axon_id["internal_axon_id"]} not found')
                continue
            yield convert_db_entity_to_view_entity(device, ignore_errors=True)
            devices_seen.add(axon_id.get('internal_axon_id'))

    def _get_devices_with_virtual_host_positive(self):
        """
        This queries Axonius's database for devices with virtual_host field positive
        :return:
        """
        devices_with_virtual_host_positive = list(self.devices_db.find(
            self.common.query.parse_aql_filter(
                '(specific_data.data.virtual_host == true)'),
            projection={
                '_id': False,
                'internal_axon_id': True}
        ))

        for axon_id in devices_with_virtual_host_positive:
            # Get the whole device and all its data from the database by searching with its internal axon id
            device = self.devices_db.find_one({'internal_axon_id': axon_id['internal_axon_id']})
            # XXX: somehow I got error where device is None
            if not device:
                logger.debug(f'internal_axon_id {axon_id["internal_axon_id"]} not found')
                continue
            yield convert_db_entity_to_view_entity(device, ignore_errors=True)

    def __get_cve_data_from_installed_software(self, adapter_specific_data):
        """
        Searches the NVD with a device's installed software
        :param adapter_specific_data: specific data dict from a device returned by the db
        :return:
        """
        try:
            device_installed_software = adapter_specific_data.get('installed_software') or []
            if device_installed_software:
                software_cves = self.__query_nvd_with_software(device_installed_software)
                yield from software_cves
        except Exception:
            logger.exception(f'Exception while processing device')

    def __get_cve_data_from_device(self, adapter_specific_data):
        """
        Searches the NVD with a device's existing CVE ids
        :param adapter_specific_data: specific data dict from a device returned by the db
        :return:
        """
        try:
            device_cves = adapter_specific_data.get('software_cves') or []
            if device_cves:
                for cve in device_cves:
                    try:
                        data = self.__query_nvd_with_cve(cve_id=cve.get('cve_id'))
                        if data:
                            yield data
                    except Exception:
                        logger.exception(f'CVE search in NVD failed for {cve}')
        except Exception:
            logger.exception(f'Exception while processing device')

    def __query_nvd_with_cve(self, cve_id):
        try:
            return self.__nvd_searcher.search_by_cve(cve_id_to_search=cve_id)
        except Exception:
            logger.exception(f'Failed to get CVE data for {cve_id}')

    def __query_nvd_with_software(self, installed_software: Iterable[Dict]) -> Iterable[dict]:
        software_to_query = []
        try:
            for software in installed_software:
                software_vendor = software.get('vendor') or ''
                software_name = software.get('name') or ''
                software_version = software.get('version') or ''

                # Check for valid software input
                if not all(isinstance(x, str) for x in (software_vendor, software_name, software_version)):
                    logger.error(f'Error: installed software contains not strings: {software}')
                    continue

                if not software_name or not software_version:
                    logger.debug(f'Error: installed software contains name/version empty strings: {software}')
                    continue

                if 'microsoft' in software_vendor.lower() and 'office' in software_name.lower():
                    # Microsoft Office is not supported since the CVE's there are too broad.
                    # e.g. https://portal.msrc.microsoft.com/en-US/security-guidance/advisory/CVE-2018-8161
                    # is a cve for all versions of Office 2016. This could lead to many false-positives.
                    # However we do get information about patches for office and other microsoft products from
                    # our patch management modules.
                    continue

                if not self._fetch_empty_vendor_software_vulnerabilites and not software_vendor:
                    continue
                software_to_query.append({uuid.uuid4(): (software_vendor, software_name, software_version)})
            software_cves = self.__nvd_searcher.search_vulns(software_to_query)
            if not software_cves:
                return
            for software_id, cve_matches in software_cves.items():
                software_data = [x for x in software_to_query if uuid.UUID(software_id) in x]
                for cve in cve_matches:
                    if software_data and software_data[0].get(uuid.UUID(software_id), ['', '', ''])[0]:
                        cve['software_vendor'] = software_data[0][uuid.UUID(software_id)][0]
                    if software_data and software_data[0].get(uuid.UUID(software_id), ['', '', ''])[1]:
                        cve['software_name'] = software_data[0][uuid.UUID(software_id)][1]
                    if software_data and software_data[0].get(uuid.UUID(software_id), ['', '', ''])[2]:
                        cve['software_version'] = software_data[0][uuid.UUID(software_id)][2]
                    yield cve
        except Exception:
            logger.exception(f'Exception while searching for vulns for {software_to_query}')

    # Devices/Users association

    def __try_convert_username_prefix_to_username_upn(self, username: str):
        """
        Tries to convert TestDomain\\Administrator to Administrator@testdomain.test
        username: the username to convert
        :return:
        """
        try:
            prefix, name = username.split('\\')
            prefix_to_dns = self.get_global_keyval('ldap_nbns_to_dns') or {}
            dns_name = prefix_to_dns.get(prefix.lower())
            if dns_name:
                return f'{name}@{dns_name}'.lower()
            return f'{name}@{prefix}'.lower()
        except Exception:
            pass
        return username.lower()

    @staticmethod
    def get_first_data(fd_d, fd_attr):
        # Gets the first 'hostname', for example, from a device object.
        for sd in fd_d.get('specific_data', []):
            if isinstance(sd.get('data'), dict):
                value = sd['data'].get(fd_attr)
                if value:
                    return value
        return None

    @cachetools.cached(cachetools.TTLCache(maxsize=1, ttl=60 * 60 * 6), lock=threading.Lock())
    def get_all_users(self):
        logger.info('Pulling all users')
        projection_fields = ['id', 'username', 'domain', 'mail', 'first_name',  'last_name']
        entities = ['adapters', 'tags']

        users_by_internal_axon_id = {x['internal_axon_id']: x for x in self.users_db.find({}, projection={
            'internal_axon_id': 1,
            **{f'{entity_type}.data.{field}': 1 for entity_type in entities for field in projection_fields}
        })}
        logger.info(f'Pulled users information')

        users_by_id = defaultdict(set)
        users_by_username = defaultdict(set)
        users_by_username_and_domain = defaultdict(set)
        users_by_mail = defaultdict(set)
        users_by_full_name = defaultdict(set)

        for entity_type in entities:
            for user_internal_axon_id, user in users_by_internal_axon_id.items():
                if not isinstance(user.get(entity_type), list):
                    continue

                for entity_data in user[entity_type]:
                    if 'data' not in entity_data:
                        continue

                    data = entity_data['data']

                    if not isinstance(data, dict):
                        continue

                    if data.get('id'):
                        users_by_id[str(data['id']).lower()].add(user_internal_axon_id)
                    if data.get('username'):
                        users_by_username[str(data['username']).lower()].add(user_internal_axon_id)
                        if data.get('domain'):
                            username_and_domain = f'{data["username"]}_{data["domain"]}'.lower()
                            users_by_username_and_domain[username_and_domain].add(user_internal_axon_id)
                    if data.get('mail'):
                        users_by_mail[str(data['mail']).lower()].add(user_internal_axon_id)
                    if data.get('first_name') or data.get('last_name'):
                        full_name = f'{data.get("first_name") or ""}_{data.get("last_name") or ""}'.lower()
                        users_by_full_name[full_name].add(user_internal_axon_id)

        logger.info(f'Built Indexes')
        return users_by_id, users_by_username, users_by_username_and_domain, users_by_mail, users_by_full_name

    def __get_users_by_identifier(self, username) -> List[str]:
        """
        Gets a username. tries to find it by id, then by username/domain if possible, then only by username.
        :param username:
        :return:
        """

        username = username.replace('"', '').lower()

        llu_username = username
        llu_domain = None
        try:
            if '\\' in username:
                llu_domain, llu_username = username.split('\\')
            elif '@' in username:
                llu_username, llu_domain = username.split('@')
        except Exception:
            pass

        users_by_id, users_by_username, users_by_username_and_domain, users_by_mail, users_by_full_name = \
            self.get_all_users()

        users = users_by_id.get(username)

        if not users and llu_domain:
            users = users_by_username_and_domain.get(f'{llu_username}_{llu_domain}')

        if not users:
            users = users_by_mail.get(username)

        if not users:
            users = users_by_full_name.get(username)

        if not users:
            users = users_by_username.get(username)

        return list(users or [])

    # pylint: disable=too-many-locals, too-many-branches, too-many-statements
    def __associate_users_with_devices(self):
        """
        Assuming devices were associated with users, now we associate users with devices.
        :return:
        """
        logger.info('Associating users with devices')

        associated_plugin_unique_names = set()
        # 1. Get all devices which have users associations, and map all these devices to one global users object.
        # Notice that we select by filter. we do this to include users that came both from adapters and plugins.
        devices_with_users_association = self.devices_db.find(
            self.common.query.parse_aql_filter(
                'specific_data.data.users == exists(true) or specific_data.data.last_used_users == exists(true) or '
                'specific_data.data.assigned_to == exists(true) or '
                'specific_data.data.top_user == exists(true) or '
                'specific_data.data.current_logged_user == exists(true) or '
                'adapters_data.azure_ad_adapter.user_principal_name == ({"$exists":true,"$ne":""}) or '
                'specific_data.data.email == ({"$exists":true,"$ne":""})'),
            batch_size=10
        )

        logger.info(f'Approximate devices with users association: {devices_with_users_association.count()}')

        users = {}
        for device_i, device_raw in enumerate(devices_with_users_association):
            if device_i % 10000 == 0:
                logger.info(f'Users Devices association - Step 1 - pulled {device_i}')
            # Get a list of all users associated for this device.
            device = convert_db_entity_to_view_entity(device_raw, ignore_errors=True)
            all_device_data = device.get('specific_data', [])
            for sd_users in [d['data']['users'] for d in all_device_data
                             if isinstance(d['data'], dict) and d['data'].get('users') is not None]:
                # for each user associated, add a (device, user) tuple.
                for user in sd_users:
                    if 'username' not in user:
                        logger.warning(f'Bad user {user}')
                        continue

                    current_username = self.__try_convert_username_prefix_to_username_upn(user['username'])

                    if not is_valid_user(current_username):
                        continue

                    if users.get(current_username) is None:
                        users[current_username] = {
                            'should_create_if_not_exists': False,
                            'creation_identity_tuple': None,
                            'associated_devices': []
                        }

                    # Users is a dict that maps between username (the user 'id') and a dict that represents
                    # if this user should be created if it doesn't exist, and all of its associated users
                    device_caption = \
                        self.get_first_data(device, 'hostname') or self.get_first_data(device, 'name') or \
                        self.get_first_data(device, 'id')
                    users[current_username]['associated_devices'].append((user, device_caption))
                    if user.get('should_create_if_not_exists'):
                        try:
                            # creation_plugin_type = user['creation_source_plugin_type']
                            creation_plugin_name = user['creation_source_plugin_name']
                            creation_plugin_unique_name = user['creation_source_plugin_unique_name']

                            # Notice! plugin_type of types 'plugin' aren't shown in the gui. If this is a user
                            # marked for creation we change ad-hoc the type to 'adapter' to make this be seen
                            # as an 'adapter' in the gui user page
                            creation_plugin_type = adapter_consts.ADAPTER_PLUGIN_TYPE
                        except Exception:
                            logger.exception(f'Exception - should create if not exists is True but there '
                                             f'is no creation identity tuple! bypassing')
                            continue
                        users[current_username]['creation_identity_tuple'] = (
                            creation_plugin_type, creation_plugin_name, creation_plugin_unique_name
                        )
                        users[current_username]['should_create_if_not_exists'] = True
                        if creation_plugin_unique_name:
                            associated_plugin_unique_names.add(creation_plugin_unique_name)
            # We also go over the last used user.
            sd_last_used_users_list = [
                d['data']['last_used_users'] for d in all_device_data
                if isinstance(d['data'], dict) and isinstance(d['data'].get('last_used_users'), list)
            ]
            for d in all_device_data:
                if isinstance(d['data'], dict) and isinstance(d['data'].get('user_principal_name'), str):
                    sd_last_used_users_list.append([d['data']['user_principal_name']])
                if isinstance(d['data'], dict) and isinstance(d['data'].get('assigned_to'), str):
                    sd_last_used_users_list.append([d['data']['assigned_to']])
                if isinstance(d['data'], dict) and isinstance(d['data'].get('top_user'), str):
                    sd_last_used_users_list.append([d['data']['top_user']])
                if isinstance(d['data'], dict) and isinstance(d['data'].get('current_logged_user'), str):
                    sd_last_used_users_list.append([d['data']['current_logged_user']])
                if isinstance(d['data'], dict) and isinstance(d['data'].get('email'), str):
                    sd_last_used_users_list.append([d['data']['email']])

            for sd_last_used_users in sd_last_used_users_list:
                for sd_last_used_user in sd_last_used_users:
                    sd_last_used_user = self.__try_convert_username_prefix_to_username_upn(sd_last_used_user)
                    if users.get(sd_last_used_user) is None:
                        users[sd_last_used_user] = {
                            'should_create_if_not_exists': False,
                            'creation_identity_tuple': None,
                            'associated_devices': []
                        }

                    device_caption = \
                        self.get_first_data(device, 'hostname') or self.get_first_data(device, 'name') or \
                        self.get_first_data(device, 'id')
                    users[sd_last_used_user]['associated_devices'].append((sd_last_used_user, device_caption))

        logger.info(f'Finished step 1')
        # 2. Go over all users. whatever we don't have, and should be created, we must create first.
        user_id = 0
        for username, username_data in users.copy().items():
            user_id += 1
            if user_id % 10000 == 0:
                logger.info(f'Users Devices association - Step 2 - finished {user_id}')
            user = self.__get_users_by_identifier(username)
            if not user:
                if username_data['should_create_if_not_exists']:
                    # user does not exists, create it.
                    user_dict = self._new_user_adapter()
                    user_dict.id = username  # Should be the unique identifier of that user.
                    try:
                        user_dict.username, user_dict.domain = username.split('@')  # expecting to be user@domain.
                    except ValueError:
                        logger.exception(f'Bad user format! expected \'username@domain\' format, '
                                         f'got {username}. bypassing')
                        continue
                    try:
                        self._save_data_from_plugin(
                            self.plugin_unique_name,
                            data_of_client={'raw': [], 'parsed': [user_dict.to_dict()]},
                            entity_type=EntityType.Users,
                            should_log_info=False,
                            plugin_identity=username_data['creation_identity_tuple'])
                    except Exception:
                        logger.exception(f'Could not create new user!')

                # If the user has been created it will be populated in the next cycle.
                # Otherwise it should not be in the list anyway.
                users.pop(username)

        logger.info(f'Finished step 2. Final users to associate: {len(users)}')
        # 4. Now go over all users again. for each user, associate all known devices.
        users_dict: Dict[str, Tuple[AxoniusUser, UserAdapter]] = dict()
        for username, username_data in users.items():
            linked_devices_and_users_list = username_data['associated_devices']
            # Create the new adapterdata for that user
            number_of_associated_devices = 0

            # Find that user. It should be in the view new.
            user = self.__get_users_by_identifier(username)

            # Do we have it? or do we need to create it?
            if len(user) > 1:
                # Can't be! how can we have a user with the same id? should have been correlated.
                if str(username).lower() not in LIST_OF_DEFAULT_USERS:
                    logger.warning(f'Found a couple of users (expected one) with same id: {username} -> {user}')
                continue
            elif len(user) == 0:
                logger.error(f'User {username} should have been created in the view but is not there! Continuing')
                continue

            # at this point the user exists, go over all associated devices and add them.
            user_internal_axon_id = user[0]

            if user_internal_axon_id in users_dict:
                adapterdata_user = users_dict[user_internal_axon_id][1]
            else:
                adapterdata_user = self._new_user_adapter()
                adapterdata_user.id = username
                users_dict[user_internal_axon_id] = (user_internal_axon_id, adapterdata_user)

            for linked_user, device_caption in linked_devices_and_users_list:
                if isinstance(linked_user, str):
                    linked_user = {'username': linked_user}  # an only string is considered a user with only a username
                try:
                    logger.debug(f'Associating {device_caption} with user {username}')

                    # Notice! except last_used_date, we do not handle situations where users have different
                    # sid's, is_disabled / is_admin / is_local statuses. In that cases the last one wins..
                    # otherwise we would have to create an 'adapters' mechanism for users.

                    try:
                        adapterdata_user.last_seen_in_devices = \
                            max(linked_user['last_use_date'], adapterdata_user.last_seen_in_devices)
                    except Exception:
                        if linked_user.get('last_use_date') is not None:
                            adapterdata_user.last_seen_in_devices = linked_user.get('last_use_date')

                    if linked_user.get('user_sid') is not None:
                        adapterdata_user.user_sid = linked_user.get('user_sid')

                    if linked_user.get('is_disabled') is not None:
                        adapterdata_user.account_disabled = linked_user.get('is_disabled')

                    if linked_user.get('is_admin') is not None:
                        adapterdata_user.is_admin = linked_user.get('is_admin')

                    if linked_user.get('is_local') is not None:
                        adapterdata_user.is_local = linked_user.get('is_local')

                    adapterdata_user.add_associated_device(
                        device_caption=device_caption,
                        last_use_date=linked_user.get('last_use_date')
                    )
                    number_of_associated_devices += 1
                    if number_of_associated_devices >= 1000:
                        logger.error(f'Error! too many associated devices (>1000) for user {username}. breaking')
                        break
                except Exception:
                    logger.exception(f'Cant associate user {linked_user}')

        # we have a new adapterdata_user, lets add it. we do not give any specific identity
        # since this tag isn't associated to a specific adapter.
        # Note - no need for action_if_exists='update' - this is an action on user, not device!
        logger.info(f'Saving adapterdata to {len(users_dict.keys())} users..')
        num_of_users = 0
        for internal_axon_id, internal_axon_id_data in users_dict.items():
            num_of_users += 1
            if num_of_users % 1000 == 0:
                logger.info(f'Already saved {num_of_users} users.')
            try:
                user_internal_axon_id, adapterdata_user = internal_axon_id_data
                user = next(self.users.get(internal_axon_id=user_internal_axon_id), None)
                if not user:
                    continue
                user.add_adapterdata(
                    adapterdata_user.to_dict(),
                    additional_data={
                        'hidden_for_gui': True
                    }
                )
            except Exception:
                logger.exception(f'Error saving data for internal axon id {internal_axon_id}!')
        self._save_field_names_to_db(EntityType.Users)
        for unique_name in associated_plugin_unique_names:
            self._save_field_names_to_db(EntityType.Users, unique_name)
        logger.info('Finished associating users with devices')

    # pylint: disable=invalid-name, too-many-nested-blocks
    def __parse_devices_last_used_users_departments(self):
        users_to_devices_fields = dict()
        for associcated_field in ASSOCIATED_FIELD:
            users_to_devices_fields[associcated_field] = dict()
        # Notice that we have a non-default batch_size of 10 here (instead of 100). We do this
        # because we want to interact with the server every 10 devices, and not 100. From our experience,
        # if the default is saved, then every batch will be fetched in more than every 10 minutes. But the default
        # of mongo is to lose a cursor that hasn't been fetched in 10 minutes, so this will cause a 'cursor not found'.
        devices_with_last_used_users = self.devices_db.find(
            self.common.query.parse_aql_filter(
                '((adapters_data.azure_ad_adapter.user_principal_name == ({"$exists":true,"$ne":""}))) '
                'or ((specific_data.data.last_used_users == ({"$exists":true,"$ne":""}))) '
                'or (specific_data.data.email == ({"$exists":true,"$ne":""}))'
            ),
            batch_size=10
        )

        logger.info(f'Associating {devices_with_last_used_users.count()} users')
        for device_i, device_view in enumerate(devices_with_last_used_users):
            if device_i and device_i % 1000 == 0:
                logger.info(f'Parsed {device_i} users in last_used_users_departments')
            # Get a list of all users associated for this device.
            device_raw = convert_db_entity_to_view_entity(device_view, ignore_errors=True)
            device_specific_data = device_raw.get('specific_data', [])
            device_last_used_users_set = set()

            for device_adapter_data in device_specific_data:
                device_adapter_data_last_used_users = (device_adapter_data.get('data') or {}).get('last_used_users')
                if device_adapter_data_last_used_users and isinstance(device_adapter_data_last_used_users, list):
                    for device_adapter_data_last_used_user in device_adapter_data_last_used_users:
                        upn_name = \
                            self.__try_convert_username_prefix_to_username_upn(device_adapter_data_last_used_user)
                        device_last_used_users_set.add(upn_name)
                user_principal_name = (device_adapter_data.get('data') or {}).get('user_principal_name')
                if user_principal_name:
                    upn_name = \
                        self.__try_convert_username_prefix_to_username_upn(user_principal_name)
                    device_last_used_users_set.add(upn_name)

                device_email = (device_adapter_data.get('data') or {}).get('email')
                if device_email:
                    upn_name = \
                        self.__try_convert_username_prefix_to_username_upn(device_email)
                    device_last_used_users_set.add(upn_name)

                jamf_location = (device_adapter_data.get('data') or {}).get('jamf_location')
                if isinstance(jamf_location, dict):
                    jamf_email = jamf_location.get('email_address')
                    if jamf_email:
                        upn_name = self.__try_convert_username_prefix_to_username_upn(jamf_email)
                        device_last_used_users_set.add(upn_name)

            # Now we have a set of all last used users for this device, from all of its adapters.
            # Lets try to get each of these users to achieve their department
            device_last_used_users_fields_sets = dict()
            for associcated_field in ASSOCIATED_FIELD:
                device_last_used_users_fields_sets[associcated_field] = set()
            for last_used_user in device_last_used_users_set:
                # if last used user is in one of them, it will also be in the second. so 'or' == 'and' here.
                if last_used_user in users_to_devices_fields[ASSOCIATED_FIELD[0]]:
                    for associcated_field in ASSOCIATED_FIELD:
                        if users_to_devices_fields[associcated_field].get(last_used_user):
                            device_last_used_users_fields_sets[associcated_field].add(users_to_devices_fields
                                                                                      [associcated_field]
                                                                                      [last_used_user])
                else:
                    user = self.__get_users_by_identifier(last_used_user)

                    if len(user) > 0:
                        if len(user) > 1 and str(last_used_user).lower() in LIST_OF_DEFAULT_USERS:
                            # Ignore 'default' users as they are probably incorrect
                            continue
                        for associcated_field in ASSOCIATED_FIELD:
                            field_candidate = None
                            for one_user_id in user:
                                one_user = next(self.users.get(internal_axon_id=one_user_id), None)
                                if not one_user:
                                    continue
                                field_candidate = one_user.get_first_data(associcated_field)
                                if field_candidate:
                                    field_candidate = str(field_candidate)
                                    break
                            if field_candidate:
                                device_last_used_users_fields_sets[associcated_field].add(field_candidate)
                            users_to_devices_fields[last_used_user] = field_candidate

            # Now that we have all departments for this device lets add the appropriate adapterdata.
            # be careful not to override an adapterdata which already exists like the vuln one.
            device_adapter = self._new_device_adapter()
            for associcated_field in ASSOCIATED_FIELD:
                if device_last_used_users_fields_sets[associcated_field]:
                    attr_name = f'last_used_users_{associcated_field}_association'
                    if attr_name == 'last_used_users_user_department_association':
                        attr_name = 'last_used_users_departments_association'
                    device_adapter.__setattr__(attr_name,
                                               list(device_last_used_users_fields_sets[associcated_field]))
            # Add the final one
            device_object = list(self.devices.get(internal_axon_id=device_raw['internal_axon_id']))
            if len(device_object) != 1:
                logger.warning(
                    f'Warning, could not get a device object for internal axon id {device_raw["internal_axon_id"]}'
                )
                continue
            device_object = device_object[0]
            device_object.add_adapterdata(
                device_adapter.to_dict(),
                action_if_exists='update',
                additional_data={
                    'hidden_for_gui': True
                }
            )
            self._save_field_names_to_db(EntityType.Devices)

    @property
    def plugin_subtype(self) -> PluginSubtype:
        return PluginSubtype.PostCorrelation
