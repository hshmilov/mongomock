import requests
import datetime
import threading
from general_info.subplugins.wmi_utils import wmi_date_to_datetime, wmi_query_commands, is_wmi_answer_ok
from general_info.subplugins.general_info_subplugin import GeneralInfoSubplugin
from axonius.devices.device import Device

USERS_QUERY_TRESHOLD_HOURS = 1  # Hours to query users per each adapter


class GetUserLogons(GeneralInfoSubplugin):
    """ Using wmi queries, determines who is the last user that logged into the machine. """
    users = {}  # a cache var for storing users from adapters. Note that this is a class var.
    users_query_lock = threading.Lock()

    def __init__(self, plugin_base_delegate):
        """
        initialization.
        :param plugin_base_delegate: the "self" of a relevant plugin base.
        """
        super().__init__(plugin_base_delegate)

    def get_users(self, list_of_adapters):
        # This whole thing is a temp solution until we implement 'users' in aggregator.
        dict_of_users = {}

        with GetUserLogons.users_query_lock:
            for adap in list_of_adapters:
                # Try to see if we already have it in our 'cache'
                users = GetUserLogons.users.get(adap)
                if users is not None \
                        and (users['lastquery'] +
                             datetime.timedelta(hours=USERS_QUERY_TRESHOLD_HOURS) > datetime.datetime.now()):
                    dict_of_users[adap] = users['users']
                else:
                    # we have to get it
                    try:
                        resp = self.plugin_base.request_remote_plugin("users", adap)
                        if resp.status_code == 200:
                            users_json = resp.json()
                            GetUserLogons.users[adap] = {'users': users_json, 'lastquery': datetime.datetime.now()}
                            dict_of_users[adap] = users_json
                        else:
                            self.logger.error(f"Tried to reach /users of {adap} but got status {resp.status_code}")
                    except requests.exceptions.RequestException:
                        self.logger.exception("Got a requests exception in get_users")

            return dict_of_users

    @staticmethod
    def get_wmi_commands():
        return wmi_query_commands(
            [
                "select SID,LastUseTime from Win32_UserProfile",
                "select SID,Caption, LocalAccount from Win32_UserAccount"
            ])

    def handle_result(self, device, executer_info, result, adapterdata_device: Device):
        super().handle_result(device, executer_info, result, adapterdata_device)
        if not all(is_wmi_answer_ok(a) for a in result):
            self.logger.info("Not handling result, result has exception")
            return False

        clients_used = [p['client_used'] for p in device['adapters']]

        user_profiles_data = result[0]
        user_accounts_data = result[1]

        # First, lets build the sids_to_users table.
        sids_to_users = {}
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
                sids_to_users[sid] = "@".join(caption.split("\\")[::-1]), bool(is_local_account)

        """
        We gotta enrich this array with the sid's we got from the adapter.
        reminder: the format from self.get_users is as follows:
        {
          "plugin_unique_name":
          {
              "client_id":
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
        }
        """

        list_of_users = self.get_users([p['plugin_unique_name'] for p in device['adapters']])
        # Todo: make this look less terrible.
        for clients_per_adapter in list_of_users.values():
            # we are now in the adapter level
            for client_used_name, client_used in clients_per_adapter.items():
                # Now iterate through all clients of that adapter. If you found one that this device uses.
                if client_used_name in clients_used:
                    # In that case you gotta iterate through all users here.
                    for unique_user_value in client_used.values():
                        sid = unique_user_value["raw"]["sid"]
                        caption = unique_user_value["raw"]["caption"]
                        if sid not in sids_to_users:
                            self.logger.debug(f"enriching sids_to_users: {sid} -> {caption}")
                            sids_to_users[sid] = caption, False

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
            user = sids_to_users.get(sid, ["Unknown Name", False])
            last_used_time_arr.append(
                {"Sid": sid,
                 "User": user[0],
                 "Is Local": user[1],
                 "Last Use": last_use_time})

        # Now sort the array.
        last_used_time_arr = sorted(last_used_time_arr, key=lambda k: k["Last Use"], reverse=True)

        # Update our adapterdata_device.
        for u in last_used_time_arr:
            adapterdata_device.add_users(username=u["User"], last_use_date=u["Last Use"], is_local=u["Is Local"])

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
                    self.plugin_base.add_label_to_device(
                        (executer_info["adapter_unique_name"], executer_info["adapter_unique_id"]),
                        "Last logon not from domain"
                    )

                return True
            except Exception:
                self.logger.exception(f"Failed Setting last user logon!")
                raise

        else:
            self.logger.error("Did not find any users. That is very weird and should not happen.")

        return False
