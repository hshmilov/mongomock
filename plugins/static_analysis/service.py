import logging
import re
import threading
from datetime import datetime
from typing import Iterable, Tuple, Dict

from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.triggers.interval import IntervalTrigger
from axonius.entities import EntityType

from axonius.consts.plugin_subtype import PluginSubtype

from axonius.background_scheduler import LoggedBackgroundScheduler
from axonius.consts.plugin_consts import PLUGIN_NAME, PLUGIN_UNIQUE_NAME
from axonius.devices.device_adapter import DeviceAdapter
from axonius.mixins.triggerable import Triggerable
from axonius.plugin_base import PluginBase
from axonius.users.user_adapter import UserAdapter
from axonius.utils.axonius_query_language import parse_filter, convert_db_entity_to_view_entity
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import is_valid_user

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


class StaticAnalysisService(Triggerable, PluginBase):
    class MyDeviceAdapter(DeviceAdapter):
        pass

    class MyUserAdapter(UserAdapter):
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
        self.__scheduler.start()

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

        try:
            self.__associate_users_with_devices()
        except Exception:
            logger.exception('Exception while trying to associate devices and users')

    # CVE Analysis

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
            # Since the process_devices operation can take a lot time, this can lead to a situation where
            # mongodb throws 'cursor not found' . This happens if we did not fetch a page from mongodb within 10 minutes
            # and this is possible if a page takes at least 10 minutes to process. a page, by default, is 100 documents.
            # to handle this we save all candidates' internal_axon_ids and then fetch them only when needed.
            for internal_axon_id_doc in list(self.devices_db.find(
                    parse_filter('specific_data.data.installed_software.name == exists(true)'),
                    projection={
                        '_id': False,
                        'internal_axon_id': True
                    }
            )):
                device = self.devices_db.find_one({'internal_axon_id': internal_axon_id_doc['internal_axon_id']})
                self.__analyze_cves_process_devices(convert_db_entity_to_view_entity(device))

        # find all devices that -
        # 1. are part of group (2)
        # 2. also have been tagged by us, and we have given it some CVE
        # imagine the case that some axonius device that used to have installed_software
        # and them we tagged it with some CVE.
        # then that device looses its installed_software, so the previous loop won't find it, then the CVE
        # will never be untagged!
        # this loop will find those devices and search them :)
        with self.__nvd_lock:
            for internal_axon_id_doc in list(self.devices_db.find(
                    parse_filter(
                        f'not (specific_data.data.installed_software.name == exists(true)) and '
                        f'adapters_data.{self.plugin_name}.software_cves == '
                        f'match([software_cves == exists(true) and software_cves != []])'),
                    projection={
                        '_id': False,
                        'internal_axon_id': True
                    }
            )):
                device = self.devices_db.find_one({'internal_axon_id': internal_axon_id_doc['internal_axon_id']})
                self.__analyze_cves_process_devices(convert_db_entity_to_view_entity(device))

    def __analyze_cves_process_devices(self, device) -> None:
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

                for found_cve in self.__analyze_cves_process_installed_software(installed_software):
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
                self._save_field_names_to_db(EntityType.Devices)
        except Exception:
            logger.exception(f'Exception while processing device {device}')

    def __analyze_cves_process_installed_software(self, installed_software: Iterable[Dict]) -> Iterable[dict]:
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
                    logger.error(f'Error: installed software contains not strings: {software}')
                    continue

                if not software_name or not software_version:
                    # Sometimes, that also happens.
                    # do note that we allow empty software_vendor as some adapters do not give it.
                    logger.debug(f'Error: installed software contains name/version empty strings: {software}')
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
                return f'{name}@{dns_name}'
        except Exception:
            pass
        return username

    @staticmethod
    def get_first_data(fd_d, fd_attr):
        # Gets the first 'hostname', for example, from a device object.
        for sd in fd_d.get('specific_data', []):
            if isinstance(sd.get('data'), dict):
                value = sd['data'].get(fd_attr)
                if value:
                    return value
        return None

    # pylint: disable=too-many-locals, too-many-branches, too-many-statements
    def __associate_users_with_devices(self):
        """
        Assuming devices were associated with users, now we associate users with devices.
        :return:
        """
        logger.info('Associating users with devices')

        # 1. Get all devices which have users associations, and map all these devices to one global users object.
        # Notice that we select by filter. we do this to include users that came both from adapters and plugins.
        devices_with_users_association = self.devices_db.find(
            parse_filter(
                'specific_data.data.users == exists(true) or specific_data.data.last_used_users == exists(true)'),
        )

        users = {}
        for device_raw in devices_with_users_association:
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
                            creation_plugin_type = user['creation_source_plugin_type']
                            creation_plugin_name = user['creation_source_plugin_name']
                            creation_plugin_unique_name = user['creation_source_plugin_unique_name']
                        except Exception:
                            logger.exception(f'Exception - should create if not exists is True but there '
                                             f'is no creation identity tuple! bypassing')
                            continue
                        users[current_username]['creation_identity_tuple'] = (
                            creation_plugin_type, creation_plugin_name, creation_plugin_unique_name
                        )
                        users[current_username]['should_create_if_not_exists'] = True

            # We also go over the last used user.
            sd_last_used_users_list = [
                d['data']['last_used_users'] for d in all_device_data
                if isinstance(d['data'], dict) and isinstance(d['data'].get('last_used_users'), list)
            ]
            for sd_last_used_users in sd_last_used_users_list:
                for sd_last_used_user in sd_last_used_users:
                    sd_last_used_user = self.__try_convert_username_prefix_to_username_upn(sd_last_used_user)
                    if users.get(sd_last_used_user) is None:
                        users[sd_last_used_user] = {
                            'should_create_if_not_exists': False,
                            'creation_identity_tuple': None,
                            'associated_devices': []
                        }

                    users[sd_last_used_user]['associated_devices'].append((sd_last_used_user, device))

        # 2. Go over all users. whatever we don't have, and should be created, we must create first.
        for username, username_data in users.copy().items():
            user = list(self.users.get(
                axonius_query_language=f'specific_data.data.id == regex("^{re.escape(username)}$", "i")'))
            if len(user) == 0 and username_data['should_create_if_not_exists']:
                # user does not exists, create it.
                user_dict = self._new_user_adapter()
                user_dict.id = username  # Should be the unique identifier of that user.
                try:
                    user_dict.username, user_dict.domain = username.split('@')  # expecting username to be user@domain.
                except ValueError:
                    logger.exception(f'Bad user format! expected \'username@domain\' format, got {username}. bypassing')
                    continue
                self._save_data_from_plugin(
                    self.plugin_unique_name,
                    data_of_client={'raw': [], 'parsed': [user_dict.to_dict()]},
                    entity_type=EntityType.Users,
                    should_log_info=False,
                    plugin_identity=username_data['creation_identity_tuple'])

            if len(user) == 0 and not username_data['should_create_if_not_exists']:
                # This user doesn't exist, and we should not create it. lets pop it out of our users dict.
                users.pop(username)

        # 4. Now go over all users again. for each user, associate all known devices.
        for username, username_data in users.items():
            linked_devices_and_users_list = username_data['associated_devices']
            # Create the new adapterdata for that user
            adapterdata_user = self._new_user_adapter()
            number_of_associated_devices = 0

            # Find that user. It should be in the view new.
            user = list(self.users.get(
                axonius_query_language=f'specific_data.data.id == regex("^{re.escape(username)}$", "i")'))

            # Do we have it? or do we need to create it?
            if len(user) > 1:
                # Can't be! how can we have a user with the same id? should have been correlated.
                logger.critical(f'Found a couple of users (expected one) with same id: {username} -> {user}')
                continue
            elif len(user) == 0:
                logger.error(f'User {username} should have been created in the view but is not there! Continuing')
                continue

            # at this point the user exists, go over all associated devices and add them.
            user = user[0]
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
            adapterdata_user.id = username
            user.add_adapterdata(
                adapterdata_user.to_dict(),
                additional_data={
                    'hidden_for_gui': True
                }
            )
            self._save_field_names_to_db(EntityType.Users)

        logger.info('Finished associating users with devices')

    @property
    def plugin_subtype(self) -> PluginSubtype:
        return PluginSubtype.PostCorrelation
