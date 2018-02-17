"""
Using wmi queries, determines who is the last user that logged into the machine.
"""
import requests
from .wmi_utils import wmi_date_to_datetime
from .general_info_subplugin import GeneralInfoSubplugin


class GetLastUserLogon(GeneralInfoSubplugin):
    """
    Understands what is the last user that logged into a device.
    """

    def __init__(self, plugin_base_delegate):
        """
        initialization.
        :param plugin_base_delegate: the "self" of a relevant plugin base.
        """
        super().__init__(plugin_base_delegate)
        self.users = {}  # a cache var for storing users from adapters.
        self.logger.info("Initialized GetLastUserLogon plugin")

    def get_users(self, list_of_adapters):
        dict_of_users = {}

        for adap in list_of_adapters:
            # Try to see if we already have it in our 'cache'.
            users = self.users.get(adap)
            if users is not None:
                dict_of_users[adap] = users
            else:
                # we have to get it
                try:
                    resp = self.plugin_base.request_remote_plugin("users", adap)
                    if resp.status_code == 200:
                        self.users[adap] = resp.json()
                        dict_of_users[adap] = self.users[adap]
                        self.logger.info(f"Returned new users set from ad: {dict_of_users[adap]}")
                    else:
                        self.logger.warning(f"Warning - tried to reach /users of {adap} "
                                            f"but got status {resp.status_code}")
                except requests.exceptions.RequestException:
                    self.logger.exception("Got a requests exception in get_users")

        return dict_of_users

    def get_wmi_commands(self):
        return [
            {"type": "query", "args": ["select SID,LastUseTime from Win32_UserProfile"]},
            {"type": "query", "args": ["select SID,Caption from Win32_UserAccount"]}
        ]

    def handle_result(self, device, executer_info, result, adapterdata_device):
        internal_axon_id = device['internal_axon_id']
        clients_used = [p['client_used'] for p in device['adapters']]
        self.logger.info(f"The clients used for {internal_axon_id} are {clients_used}")

        user_profiles_data = result[0]
        user_accounts_data = result[1]

        # First, lets build the sids_to_users table.
        sids_to_users = {}
        for user in user_accounts_data:
            # a caption is domain + username.
            # Note! we can also get many more interesting info. like, is that user a local user, was is locked out,
            # whats the actual name of the account, is it disabled, and more.
            caption = user['Caption']  # This comes in a format of domain\user. transform to user@domain.
            caption = "@".join(caption.split("\\")[::-1])
            sid = user['SID']
            sids_to_users[sid] = caption

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
                        self.logger.debug(f"enriching sids_to_users: {sid} -> {caption}")
                        sids_to_users[sid] = caption

        # Now, go over all users, parse their last use time date and add them to the array.
        last_used_time_arr = []
        for profile in user_profiles_data:
            sid = profile['SID']

            # Specifically, we have to get rid of non-users sid's like NT_AUTHORITY, groups sid's, etc.
            # Any domain/local user starts with S-1-5-21.
            if not sid.startswith("S-1-5-21"):
                continue

            # This is a string in a special format, we need to parse it.
            last_use_time = wmi_date_to_datetime(profile['LastUseTime'])
            if last_use_time is not None:
                last_used_time_arr.append(
                    {"Sid": sid,
                     "User": sids_to_users.get(sid, "Unknown Name"),
                     "Last Use": last_use_time})

        # Now sort the array.
        last_used_time_arr = sorted(last_used_time_arr, key=lambda k: k["Last Use"], reverse=True)

        # Update our adapterdata_device.
        for u in last_used_time_arr:
            adapterdata_device.add_users(username=u["User"], last_use_date=u["Last Use"])

        # Now we have a sorted list of sid's, users, and lastusetime.
        # If we have at least one user, lets update the db.
        if len(last_used_time_arr) > 0:
            try:
                last_used_user = last_used_time_arr[0]["User"]
                self.logger.info("Found last used user for axon_id {0}. sid: {0}, caption: {1}, lastusedtime: {2}"
                                 .format(internal_axon_id,
                                         last_used_time_arr[0]["Sid"],
                                         last_used_user,
                                         last_used_time_arr[0]["Last Use"]))

                # Add data to that device.
                adapterdata_device.last_logged_user = last_used_user
                self.plugin_base.add_data_to_device(
                    (executer_info["adapter_unique_name"], executer_info["adapter_unique_id"]),
                    "Known Users Last Logins", last_used_time_arr)

                return True
            except KeyError:
                self.logger.info("No translation between sid to caption! axon_id {0}. sid: {0}, lastusedtime: {1}"
                                 .format(internal_axon_id,
                                         last_used_time_arr[0]["Sid"],
                                         last_used_time_arr[0]["Last Use"]))

        else:
            self.logger.error("Did not find any users. That is very weird and should not happen.")

        return False
