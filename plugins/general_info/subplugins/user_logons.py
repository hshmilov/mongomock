import datetime
import threading
from general_info.subplugins.wmi_utils import wmi_date_to_datetime, wmi_query_commands, is_wmi_answer_ok
from general_info.subplugins.general_info_subplugin import GeneralInfoSubplugin
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.parsing import parse_bool_from_raw

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
                # This could be only from adapters.data, as it comes from active directory. Once we have
                # this information coming from tags we should change this.
                GetUserLogons.users_to_sids = {}
                list_of_users_from_users_db = self.plugin_base.users_db.find(
                    filter={"adapters.data.ad_sid": {"$exists": True}},
                    projection={"adapters.data.ad_sid": 1, "adapters.data.username": 1,
                                "adapters.data.domain": 1}
                )

                for user in list_of_users_from_users_db:
                    # we always take the first one. if that device has more than one adapter that reports sid, the name
                    # is going to be the same - its the correlation rule for users_to_sids (its their id!)
                    data = user["adapters"][0]["data"]
                    sid = data.get("ad_sid")    # there because that is our filter.
                    username = data.get("username")  # should always be there
                    domain = data.get("domain")  # not necessarily there...
                    if domain is not None:
                        username = f"{username}@{domain}"

                    self.logger.debug(f"enriching sids_to_users: {sid} -> {username}")
                    GetUserLogons.users_to_sids[sid] = {"username": username, "is_local": False}

                GetUserLogons.users_to_sids_last_query = datetime.datetime.now()

            return GetUserLogons.users_to_sids.copy()

    @staticmethod
    def get_wmi_smb_commands():
        return wmi_query_commands(
            [
                "select SID,LastUseTime from Win32_UserProfile",
                "select SID,Caption,LocalAccount,Disabled from Win32_UserAccount",
                "select GroupComponent, PartComponent from Win32_GroupUser"
            ])

    def handle_result(self, device, executer_info, result, adapterdata_device: DeviceAdapter):
        super().handle_result(device, executer_info, result, adapterdata_device)
        if not all(is_wmi_answer_ok(a) for a in result):
            self.logger.error(f"Not handling result, It has an exception: {result}")
            return False

        user_profiles_data = result[0]["data"]
        user_accounts_data = result[1]["data"]
        users_groups_data = result[2]["data"]

        try:
            for users_groups_data_raw in users_groups_data:
                try:
                    if ',Name="Administrators"' in users_groups_data_raw["GroupComponent"]:
                        domain_raw, username_raw = users_groups_data_raw["PartComponent"].split(',')
                        username_raw_name = username_raw.split('=')[1].strip('"')
                        domain_raw_type, domain_raw_name = domain_raw.split('=')
                        domain_raw_name = domain_raw_name.strip('"')
                        if 'UserAccount' in domain_raw_type:
                            domain_type = 'Admin User'
                        elif 'Group' in domain_raw_type:
                            domain_type = 'Group Membership'
                        else:
                            continue
                        username_full = f"{username_raw_name}@{domain_raw_name}"
                        adapterdata_device.add_local_admin(admin_name=username_full, admin_type=domain_type)

                except Exception:
                    self.logger.exception(f"Problem with {users_groups_data_raw}")
        except Exception:
            self.logger.exception(f"Problem handling users groups data {str(users_groups_data)}")

        users_on_this_device = dict()

        # Lets build the sids_to_users table. We get the base sids_to_users from the users db first.
        local_hostname = "local"    # will be changed in the following loop
        sids_to_users = self.get_sid_to_users_db()
        for user in user_accounts_data:
            # a caption is domain + username.
            # Note! we can also get many more interesting info. like, is that user a local user, was is locked out,
            # whats the actual name of the account, is it disabled, and more.
            caption = user.get('Caption')  # This comes in a format of domain\user. transform to user@domain.
            sid = user.get('SID')

            if caption is None or sid is None:
                self.logger.error(f"Couldn't find Caption/SID in user_accounts_data: {user} not enriching")
            elif str(sid) in sids_to_users:
                # This can happen if a user is a domain user but also exists as a local one. In these circumstances,
                # the local one would have a caption like "user@TESTDOMAIN" while the AD one will
                # have "user@TestDomain.test". We prefer the AD one from two reasons:
                # 1. Its more good looking
                # 2. An AD user already exists, we shouldn't create a new user here. Using the local user
                #    can cause us to create a new user (if the id is username and not sid)
                self.logger.debug(f"sid {sid} already exists from the db we get in AD, bypassing")
            else:
                local_hostname, local_username = caption.split("\\")
                user_object = {
                    "username": f"{local_username}@{local_hostname}",
                    "is_local": parse_bool_from_raw(user.get('LocalAccount')),
                    "is_disabled": parse_bool_from_raw(user.get('Disabled'))
                }
                users_on_this_device[sid] = user_object
                sids_to_users[sid] = user_object

        # Now, go over all users, parse their last use time date and add them to the array.
        # note that user_profiles is the profiles we have on this computer, not all users have profiles (unlogged users)
        # and some profiles have no useraccounts (remote domain users).
        # in general, win32_useraccount is for local users, win32_userprofile is profiles for logged in local and remote
        # users
        last_used_time_arr = []
        for profile in user_profiles_data:
            sid = profile.get('SID')
            last_use_time = profile.get('LastUseTime')

            if sid is None:
                self.logger.error(f"Couldn't find SID in user_profiles_data: {profile}. Moving on")
                continue

            # Specifically, we have to get rid of non-users sid's like NT_AUTHORITY, groups sid's, etc.
            # Any domain/local user starts with S-1-5-21.
            if not sid.startswith("S-1-5-21"):
                continue

            # For some reason last_use_time is sometimes 0....
            try:
                if last_use_time is not None and str(last_use_time) != "0":
                    last_use_time = wmi_date_to_datetime(last_use_time)
                else:
                    last_use_time = None
            except Exception:
                self.logger.exception(f"Error parsing LastUseTime ({last_use_time}). Continuing")
                last_use_time = None

            # we have an sid which can be local or remote. Lets try to get it, but in case we don't have any translation
            # which usually occurs if a user is deleted and then we have its profile but no data about it, put unknown.
            user = sids_to_users.get(sid,
                                     {
                                         "username": f"Unknown@{local_hostname}",
                                         "is_local": False,
                                         "is_disabled": False
                                     }
                                     )
            if last_use_time is not None:
                last_used_time_arr.append(
                    {"Sid": sid,
                     "User": user["username"],
                     "Is Local": user.get("is_local", False),
                     "Last Use": last_use_time})

            # Add these users. In case the user exists (Local User), we just add a last_use_date to it.
            # But if its a remote domain then we add it for the first time.
            users_on_this_device[sid] = {
                "username": user["username"],
                "is_local": user.get("is_local"),
                "is_disabled": user.get("is_disabled"),
                "last_use_date": last_use_time
            }

        # Update our adapterdata_device, add all users we have.
        for sid, u in users_on_this_device.items():
            adapterdata_device.add_users(
                user_sid=sid,
                username=u.get("username"),
                last_use_date=u.get("last_use_date"),
                is_local=u.get("is_local"),
                is_disabled=u.get("is_disabled"),
                origin_unique_adapter_name=executer_info["adapter_unique_name"],
                origin_unique_adapter_data_id=executer_info["adapter_unique_id"],
                origin_unique_adapter_client=executer_info["adapter_client_used"]
            )

        # Now sort the array.
        last_used_time_arr = sorted(last_used_time_arr, key=lambda k: k["Last Use"], reverse=True)

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
            self.logger.error(f"Did not find any users_to_sids. That is very weird and should not happen."
                              f"sids_to_users {sids_to_users}, user_accounts {user_accounts_data}, "
                              f"user_profiles {user_profiles_data}")

        return False
