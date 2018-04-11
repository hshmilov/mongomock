import datetime
import threading
from general_info.subplugins.wmi_utils import wmi_date_to_datetime, wmi_query_commands, is_wmi_answer_ok
from general_info.subplugins.general_info_subplugin import GeneralInfoSubplugin
from axonius.devices.device_adapter import DeviceAdapter

USERS_QUERY_TRESHOLD_HOURS = 1  # Hours to query users_to_sids per each adapter


class GetUserLogons(GeneralInfoSubplugin):
    """ Using wmi queries, determines who is the last user that logged into the machine. """
    users_to_sids = None  # a cache var for storing users_to_sids from adapters. Note that this is a class var.
    users_to_sids_last_query = None
    users_to_sids_query_lock = threading.Lock()

    def __init__(self, *args, **kwargs):
        """
        initialization.
        """
        super().__init__(*args, **kwargs)

    def get_sid_to_users_db(self):
        """
        Instead of querying the users_to_sids db for each device again and again, query it once and return it.
        :return: sids_to_users[sid] -> ("name@domain", bool(is_local_user))
        """

        with GetUserLogons.users_to_sids_query_lock:
            if GetUserLogons.users_to_sids is None \
                or GetUserLogons.users_to_sids_last_query + \
                    datetime.timedelta(hours=USERS_QUERY_TRESHOLD_HOURS) < datetime.datetime.now():

                # If we haven't queried users_to_sids, or if too much time has passed, Lets query and enrich.
                GetUserLogons.users_to_sids = {}
                list_of_users_from_users_db = self.plugin_base.users_db_view.find(
                    filter={"specific_data.data.sid": {"$exists": True}},
                    projection={"specific_data.data.sid": 1, "specific_data.data.username": 1,
                                "specific_data.data.domain": 1}
                )

                for user in list_of_users_from_users_db:
                    # we always take the first one. if that device has more than one adapter that reports sid, the name
                    # is going to be the same - its the correlation rule for users_to_sids (its their id!)
                    data = user["specific_data"][0]["data"]
                    sid = data.get("sid")    # there because that is our filter.
                    username = data.get("username")  # should always be there
                    domain = data.get("domain")  # not necessarily there...
                    if domain is not None:
                        username = f"{username}@{domain}"

                    self.logger.debug(f"enriching sids_to_users: {sid} -> {username}")
                    GetUserLogons.users_to_sids[sid] = username, False  # False for is_local_user

                    GetUserLogons.users_to_sids_last_query = datetime.datetime.now()

            return GetUserLogons.users_to_sids.copy()

    @staticmethod
    def get_wmi_smb_commands():
        return wmi_query_commands(
            [
                "select SID,LastUseTime from Win32_UserProfile",
                "select SID,Caption, LocalAccount from Win32_UserAccount"
            ])

    def handle_result(self, device, executer_info, result, adapterdata_device: DeviceAdapter):
        super().handle_result(device, executer_info, result, adapterdata_device)
        if not all(is_wmi_answer_ok(a) for a in result):
            self.logger.error("Not handling result, result has exception")
            return False

        user_profiles_data = result[0]["data"]
        user_accounts_data = result[1]["data"]

        # Lets build the sids_to_users table. We get the base sids_to_users from the users db first.
        sids_to_users = self.get_sid_to_users_db()
        for user in user_accounts_data:
            # a caption is domain + username.
            # Note! we can also get many more interesting info. like, is that user a local user, was is locked out,
            # whats the actual name of the account, is it disabled, and more.
            caption = user.get('Caption')  # This comes in a format of domain\user. transform to user@domain.
            sid = user.get('SID')
            is_local_account = user.get('LocalAccount')
            if caption is None or sid is None or is_local_account is None:
                self.logger.error(f"Couldn't find Caption/SID/LocalAccount in user_accounts_data: {user} "
                                  f"not enriching")
            else:
                if sid in sids_to_users:
                    # If it exists it means we have seen it in the user db. Just change the is local account
                    # which should be false but might be on weird circumstances true? (deleting user etc?)
                    sids_to_users[1] = bool(is_local_account)
                else:
                    local_hostname, local_username = caption.split("\\")
                    sids_to_users[sid] = f"{local_username}@{local_hostname}", bool(is_local_account)

        # Now, go over all users, parse their last use time date and add them to the array.
        last_used_time_arr = []
        for profile in user_profiles_data:
            sid = profile.get('SID')
            last_use_time = profile.get('LastUseTime')

            if sid is None or last_use_time is None:
                self.logger.error(f"Couldn't find SID/LastUseTime in user_profiles_data: {profile}. "
                                  f"Returning")
                return False

            # Specifically, we have to get rid of non-users sid's like NT_AUTHORITY, groups sid's, etc.
            # Any domain/local user starts with S-1-5-21.
            if not sid.startswith("S-1-5-21"):
                continue

            # For some reason last_use_time is sometimes 0....
            try:
                last_use_time = wmi_date_to_datetime(last_use_time)
            except:
                self.logger.exception(f"Error parsing LastUseTime ({last_use_time}). Setting to 1 Jan 01")
                last_use_time = datetime.datetime(1, 1, 1)

            # This is a string in a special format, we need to parse it.
            # In case we don't have a user here, we need a hostname. Lets take one of the
            user = sids_to_users.get(sid, [f"Unknown@{local_hostname}", False])
            last_used_time_arr.append(
                {"Sid": sid,
                 "User": user[0],
                 "Is Local": user[1],
                 "Last Use": last_use_time})

        # Now sort the array.
        last_used_time_arr = sorted(last_used_time_arr, key=lambda k: k["Last Use"], reverse=True)

        # Update our adapterdata_device.
        for u in last_used_time_arr:
            adapterdata_device.add_users(
                username=u["User"],
                last_use_date=u["Last Use"],
                is_local=u["Is Local"],
                origin_unique_adapter_name=executer_info["adapter_unique_name"],
                origin_unique_adapter_data_id=executer_info["adapter_unique_id"]
            )

        # Now we have a sorted list of sid's, users, and last_use_time.
        # We could have a couple of last logged users. Usually, if a user is logged in, and then we remotely
        # query for wmi queries, the last use date will be the same one.
        # so we take the top user & users that were active in the last minute before it.
        # If one of them is local we tag the device with a label that says one of the last logons is not from a domain.
        if len(last_used_time_arr) > 0:
            try:
                last_used_user = last_used_time_arr[0]
                one_min_last_used_users = [last_used_user['User']]
                is_last_login_local = last_used_user["Is Local"]

                for u in last_used_time_arr[1:]:
                    if u['Last Use'] + datetime.timedelta(seconds=60) > last_used_user['Last Use']:
                        # Its a lst logon.
                        one_min_last_used_users.append(u['User'])
                        if u['Is Local'] is True:
                            is_last_login_local = True

                # Add data to that device.
                adapterdata_device.last_used_users = one_min_last_used_users

                # If the last user is local, we should tag this device.
                if is_last_login_local is True:
                    self.plugin_base.devices.add_label(
                        [(executer_info["adapter_unique_name"], executer_info["adapter_unique_id"])],
                        "Last logon not from domain"
                    )

                return True
            except Exception:
                self.logger.exception(f"Failed Setting last user logon!")
                raise

        else:
            self.logger.error("Did not find any users_to_sids. That is very weird and should not happen.")

        return False
