import time
import threading
import functools
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.executors.pool import ThreadPoolExecutor
from axonius.plugin_base import PluginBase, add_rule
from axonius.consts.plugin_consts import PLUGIN_UNIQUE_NAME, AGGREGATOR_PLUGIN_NAME
from axonius.mixins.activatable import Activatable
from axonius.mixins.triggerable import Triggerable
from axonius.parsing_utils import get_exception_string
from datetime import tzinfo, datetime, timedelta
import re


WMI_QUERIES_CHUNK_SIZE = 10  # we are going to send 10 wmi queries each time.
WMI_QUERY_SLEEP_BETWEEN_CHUNKS = 10  # 10 seconds of sleep between each chunk.

# A help class for dealing with CIMTYPE_DateTime (returning from wmi...)


class MinutesFromUTC(tzinfo):
    """Fixed offset in minutes from UTC."""

    def __init__(self, offset):
        self.__offset = timedelta(minutes=offset)

    def utcoffset(self, dt):
        return self.__offset

    def dst(self, dt):
        return timedelta(0)


class AdUsersAssociatorPlugin(PluginBase, Activatable, Triggerable):
    def _is_work_in_progress(self) -> bool:

        if self.associate_lock.acquire(False):
            self.associate_lock.release()
            return False
        return True

    def _stop_activatable(self):
        assert self.scheduler is not None, "ad_users_associator_plugin is not running"

        self.scheduler.remove_all_jobs()
        self.scheduler.shutdown(wait=True)
        self.scheduler = None

    def _start_activatable(self):
        """
        Start the scheduler
        :return:
        """
        assert self.scheduler is None, "ad_users_associator_plugin is already running"

        executors = {'default': ThreadPoolExecutor(1)}
        self.scheduler = BackgroundScheduler(executors=executors)
        self.scheduler.add_job(func=self._associate_ad_users_to_devices_thread,
                               trigger=IntervalTrigger(hours=1),
                               next_run_time=datetime.now(),
                               name='ad_users_associator',
                               id='ad_users_associator',
                               max_instances=1)
        self.scheduler.start()

    def _triggered(self, job_name, post_json):
        """
        Returns any errors as-is.
        :return:
        """

        acquired = False
        try:
            if self.associate_lock.acquire(False):
                acquired = True
                self._associate_ad_users_to_devices_thread()
            else:
                raise RuntimeError("ad users association is already taking place, try again later")
        finally:
            if acquired:
                self.associate_lock.release()

    def __init__(self, *args, **kargs):
        super().__init__(*args, **kargs)

        self.associate_lock = threading.RLock()
        self.scheduler = None
        #  self.start_activatable()     # just for debug..

    def _associate_ad_users_to_devices_thread(self):
        """
        Runs wmi queries on ad devices to understand what is the last user logon on them.
        """

        self.logger.info("associate ad users to devices thread started.")
        with self.associate_lock:
            self.logger.debug("acquired associate lock")
            """
            1. Get a list of devices from ad, and get a list of users from ad.
            2. Execute a wmiquery on them, and determine their last logon.
            3. Set up a relevant tag.
            """
            ad_adapters = self.get_plugin_by_name('ad_adapter', verify_single=False)

            for ad_adapter in ad_adapters:
                ad_adapter_unique_name = ad_adapter[PLUGIN_UNIQUE_NAME]
                self.logger.info(f"Working on {ad_adapter_unique_name}")
                list_of_users_per_ad_adapter = self.request_remote_plugin("users", ad_adapter_unique_name).json()

                hosts = self._get_collection("devices_db",
                                             db_name=AGGREGATOR_PLUGIN_NAME)\
                    .find(
                    {"adapters.plugin_unique_name": ad_adapter_unique_name},
                    projection={'internal_axon_id': True,
                                'adapters.data.id': True,
                                'adapters.plugin_unique_name': True,
                                'adapters.client_used': True})

                # Go over all hosts, but make it in chunks so that we could delay a little bit. If we have too many
                # hosts its smart to delay to not make the system be with thousands of requests.
                # TODO: make this a lot faster. try to shoot more actions when results come and not with a delay.
                hosts = list(hosts)
                for o_index in range(0, len(hosts), WMI_QUERIES_CHUNK_SIZE):
                    for o in hosts[o_index:o_index + WMI_QUERIES_CHUNK_SIZE]:
                        # The device could have a couple of adapters, select the active directory id.
                        adapter_part = [adap for adap in o["adapters"]
                                        if adap["plugin_unique_name"] == ad_adapter_unique_name][0]

                        self.logger.debug("wmi-querying device '{0}' of adapter '{1}'",
                                          adapter_part["data"]["id"], ad_adapter_unique_name)

                        self._get_and_update_last_user_logon(
                            ad_adapter_unique_name,
                            adapter_part["data"]["id"],
                            o["internal_axon_id"],
                            adapter_part["client_used"],
                            list_of_users_per_ad_adapter)

                    time.sleep(WMI_QUERY_SLEEP_BETWEEN_CHUNKS)

    def _get_and_update_last_user_logon(self, adapter_unique_name, adapter_unique_id, internal_axon_id,
                                        client_used, list_of_users_per_ad_adapter):
        """
        Get the last user logon of this device and update the db.
        :param adapter_unique_name: the unique name of the adapter, for setting a tag.
        :param adapter_unique_id: the unique id this adapter gave to this device.
        :param internal_axon_id: the internal axon id on which we run code.
        :param client_used: the client used for querying this device.
        :param list_of_users_per_ad_adapter: a list of users per ad adapter, as returned from "/users".
        :return:
        """

        # We need two queries. one is to get the last user logon of the users. but this returns only SID's.
        # So the second one is a translation of SID's to domain\user format.
        p = self.request_action("execute_wmi_queries", internal_axon_id,
                                {"wmi_queries": [
                                    "select SID,LastUseTime from Win32_UserProfile",
                                    "select SID,Caption from Win32_UserAccount"
                                ]})
        p.then(did_fulfill=functools.partial(self._handle_wmi_execution_success,
                                             adapter_unique_name,
                                             adapter_unique_id,
                                             internal_axon_id,
                                             client_used,
                                             list_of_users_per_ad_adapter),
               did_reject=functools.partial(self._handle_wmi_execution_failure,
                                            adapter_unique_name,
                                            adapter_unique_id,
                                            internal_axon_id))

        q = self.request_action("execute_wmi_queries", internal_axon_id,
                                {"wmi_queries": [
                                    "select * from Win32_Product"
                                ]})
        q.then(did_fulfill=functools.partial(self._handle_product_success,
                                             adapter_unique_name,
                                             adapter_unique_id,
                                             internal_axon_id),
               did_reject=functools.partial(self._handle_product_failure,
                                            adapter_unique_name,
                                            adapter_unique_id,
                                            internal_axon_id))

    def _handle_wmi_execution_success(self, adapter_unique_name, adapter_unique_id, internal_axon_id,
                                      client_used, list_of_users_per_ad_adapter, data):
        try:
            self.logger.info("successfully got info for {0} of adapter {1} with adapter unique id {2}."
                             .format(internal_axon_id, adapter_unique_name, adapter_unique_id))

            data = data["output"]["product"]
            user_profiles_data = data[0]
            user_accounts_data = data[1]

            # First, lets build the sids_to_users table.
            sids_to_users = {}
            for user in user_accounts_data:
                # a caption is domain + username.
                # Note! we can also get many more interesting info. like, is that user a local user, was is locked out,
                # whats the actual name of the account, is it disabled, and more.
                caption = user['Caption']['value']  # This comes in a format of domain\user. transform to user@domain.
                caption = "@".join(caption.split("\\")[::-1])
                sid = user['SID']['value']
                sids_to_users[sid] = caption

            """
            We gotta enrich this array with the sid's we got from the ad-adapter.
            reminder: the format is as follows:
            {
              "plugin_unique_name":
              {
                  "user_unique_id":
                  {
                      "raw":
                      {
                          "sid": "the sid",
                          "caption": "the caption"
                       }
                  }
              }
            }
            """
            if client_used in list_of_users_per_ad_adapter:
                for sid in list_of_users_per_ad_adapter[client_used]:
                    caption = list_of_users_per_ad_adapter[client_used][sid]["raw"]["caption"]
                    self.logger.debug(f"enriching sids_to_users: {sid} -> {caption}")
                    sids_to_users[sid] = caption

            # Now, go over all users, parse their last use time date and add them to the array.
            last_used_time_arr = []
            for profile in user_profiles_data:
                sid = profile['SID']['value']

                # Specifically, we have to get rid of non-users sid's like NT_AUTHORITY, groups sid's, etc.
                # Any domain/local user starts with S-1-5-21.
                if not sid.startswith("S-1-5-21"):
                    continue

                # This is a string in a special format, we need to parse it.
                lastusetime = profile['LastUseTime']['value']

                # Parse the date. this is how the str format defined here:
                # https://msdn.microsoft.com/en-us/library/system.management.cimtype(v=vs.110).aspx
                date_pattern = re.compile(r'^(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})\.(\d{6})([+|-])(\d{3})')
                s = date_pattern.search(lastusetime)
                if s is not None:
                    g = s.groups()
                    offset = int(g[8])
                    if g[7] == '-':
                        offset = -offset
                    dt = datetime(int(g[0]), int(g[1]),
                                  int(g[2]), int(g[3]),
                                  int(g[4]), int(g[5]),
                                  int(g[6]), MinutesFromUTC(offset))
                    last_used_time_arr.append({"sid": sid, "lastusetime": dt})

            # Now sort the array.
            last_used_time_arr = sorted(last_used_time_arr, key=lambda k: k["lastusetime"], reverse=True)

            # Now we have a sorted list of sid's and lastusetime, and we can get the caption by sids_to_users.
            # If we have at least one user, lets update the db.
            if len(last_used_time_arr) > 0:
                last_used_user = sids_to_users.get(last_used_time_arr[0]["sid"], "Unknown user")

                self.add_data_to_device((adapter_unique_name, adapter_unique_id),
                                        "FIELD",
                                        {"fieldname": "last_used_user", "fieldvalue": last_used_user})

                self.logger.info("Found last used user for axon_id {0}. sid: {0}, caption: {1}, lastusedtime: {2}"
                                 .format(internal_axon_id,
                                         last_used_time_arr[0]["sid"],
                                         last_used_user,
                                         last_used_time_arr[0]["lastusetime"]))

        except Exception as e:
            self.logger.exception("An error occured while processing wmi result: {0}, {1}"
                                  .format(str(e), get_exception_string()))

    def _handle_wmi_execution_failure(self, adapter_unique_name, adapter_unique_id, internal_axon_id, exc):
        self.logger.error("Could not update last user logon of {0} of adapter {1}, with adapter unique id {2}, "
                          "error: {3}"
                          .format(internal_axon_id, adapter_unique_name, adapter_unique_id, str(exc)))

    def _handle_product_success(self, adapter_unique_name, adapter_unique_id, internal_axon_id, data):
        try:
            self.logger.info("successfully got software installed for {0} of adapter {1} with adapter unique id {2}."
                             .format(internal_axon_id, adapter_unique_name, adapter_unique_id))

            data = data["output"]["product"]
            installed_softwares_answer = data[0]
            installed_softwares = []

            # Lets build an installed softwares array.
            for software_answer in installed_softwares_answer:
                software = {}
                if int(software_answer['InstallState']['value']) == 5:
                    # 5 == installed
                    software['vendor'] = software_answer['Vendor']['value']
                    software['name'] = software_answer['Name']['value']
                    software['version'] = software_answer['Version']['value']
                    installed_softwares.append(software)

            self._tag_device(adapter_unique_id,
                             tagname="FIELD2",
                             tagvalue={"fieldname": "installed_softwares", "fieldvalue": installed_softwares},
                             adapter_unique_name=adapter_unique_name)

        except Exception as e:
            self.logger.exception("An error occured while processing wmi result: {0}, {1}"
                                  .format(str(e), get_exception_string()))

    def _handle_product_failure(self, adapter_unique_name, adapter_unique_id, internal_axon_id, exc):
        self.logger.error("Could not get product of {0} of adapter {1}, with adapter unique id {2}, "
                          "error: {3}"
                          .format(internal_axon_id, adapter_unique_name, adapter_unique_id, str(exc)))

    @add_rule('associate', methods=['POST'], should_authenticate=False)
    def associate_now(self):
        self._associate_now()
        return ""

    def _associate_now(self):
        if self.scheduler is None:
            self.start_activatable()

        else:
            jobs = self.scheduler.get_jobs()
            reset_job = next(job for job in jobs if job.name == 'ad_users_associator')
            reset_job.modify(next_run_time=datetime.now())
            self.scheduler.wakeup()
