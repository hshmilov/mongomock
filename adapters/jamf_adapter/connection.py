import logging
logger = logging.getLogger(f'axonius.{__name__}')
from concurrent.futures import ThreadPoolExecutor, wait, ALL_COMPLETED
from datetime import datetime
import requests
import base64
import time

from axonius.fields import Field
from axonius.utils.datetime import parse_date
from jamf_adapter.exceptions import JamfConnectionError, JamfRequestException
from jamf_adapter import consts
from axonius.utils.xml2json_parser import Xml2Json
from axonius.smart_json_class import SmartJsonClass
from axonius.utils import gui_helpers
from axonius.plugin_base import EntityType
import re


class JamfPolicy(SmartJsonClass):
    """ A definition for a Jamf Policy field"""
    policy_id = Field(int, "Policy Id")
    policy_name = Field(str, "Policy Name")
    last_runtime_date = Field(datetime, "Last Runtime Date")
    last_runtime_status = Field(str, "Last Runtime Status")
    last_completed_date = Field(datetime, "Last Successfully Completed Date")


class JamfConnection(object):
    def __init__(self, domain, users_db, http_proxy=None, https_proxy=None):
        """ Initializes a connection to Jamf using its rest API

        :param str domain: domain address for Jamf
        """
        url = domain
        self.users_db = users_db
        if not url.lower().startswith('https://') and not url.lower().startswith("http://"):
            url = 'https://' + url
        if not url.endswith('/'):
            url += '/'
        self.url = url + 'JSSResource/'
        self.headers = {'Content-Type': 'application/xml',
                        'Accept': 'application/xml'}
        self.auth = None
        self.proxies = {}
        if http_proxy is not None:
            self.proxies['http'] = http_proxy
        if https_proxy is not None:
            self.proxies['https'] = https_proxy
        logger.info(f"Proxies: {self.proxies}")
        self.num_of_simultaneous_devices = 0
        self.__threads_time_sleep = 0
        self.__should_not_keepalive = False

    def set_credentials(self, username, password):
        """ Set the connection credentials

        :param str username: The username
        :param str password: The password
        """
        self.auth = username + ":" + password
        self.headers['authorization'] = 'Basic ' + base64.b64encode(self.auth.encode()).decode()

    def get_url_request(self, request_name):
        """ Builds and returns the full url for the request

        :param request_name: the request name
        :return: the full request url
        """
        return self.url + request_name

    def connect(self):
        """ Connects to the service """

        if self.auth is None:
            raise JamfConnectionError(f"Username and password is None")
        self.get(consts.COMPUTERS_URL)

    def __del__(self):
        self.logout()

    def logout(self):
        """ Logs out of the service"""
        self.close()

    def close(self):
        """ Closes the connection """

    def _post(self, name, headers=None, data=None):
        """ Serves a POST request to Jamf API

        :param str name: the name of the page to request
        :param dict headers: the headers for the post request
        :param str data: the body of the request
        :return: the service response or raises an exception if it's not 200
        """
        response = None
        try:
            response = requests.post(self.get_url_request(name), headers=headers,
                                     data=data, proxies=self.proxies, timeout=(5, 30))
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise JamfRequestException(str(e))
        finally:
            if response is not None and self.__should_not_keepalive is True:
                response.close()

    def get(self, name, headers=None):
        """ Serves a POST request to Jamf API

        :param str name: the name of the page to request
        :param dict headers: the headers for the post request
        :return: the service response or raises an exception if it's not 200
        """
        headers = headers or self.headers
        response = None
        try:
            response = requests.get(self.get_url_request(name), headers=headers, proxies=self.proxies, timeout=(5, 30))
            response.raise_for_status()
            return Xml2Json(response.text).result
        except Exception as e:
            raise JamfRequestException(str(e))
        finally:
            if response is not None and self.__should_not_keepalive is True:
                response.close()

    def _run_in_thread_pool_per_device(self, devices, func):
        logger.info("Starting {0} worker threads.".format(self.num_of_simultaneous_devices))
        with ThreadPoolExecutor(max_workers=self.num_of_simultaneous_devices) as executor:
            try:
                device_counter = 0
                futures = []

                # Creating a future for all the device summaries to be executed by the executors.
                for device in devices:
                    device_counter += 1
                    futures.append(executor.submit(
                        func, device, device_counter))

                wait(futures, timeout=None, return_when=ALL_COMPLETED)
            except Exception as err:
                logger.exception("An exception was raised while trying to get the data.")

        logger.info("Finished getting all device data.")

    def get_users_department(self, device_details):
        """ A function for getting the department of local users.

        For each local user associated to this device this function will try to find a matching user in Axonius
        users table, if found, this function will try to add the department of the user (if applied in the user data)
        to the local associated user for this device.
        This function uses logics that might seem unreasonable, but the purpose is to avoid mistakes as much as we can.
        This is not trivial since we don't have a real connection between the local user and the users from our users
        table.

        :param device_details: Raw device details as returned from the Jamf server. This object is changed inside the
                               function (Adding the department details to it)
        :return:
        """
        try:
            # Just getting all users
            users_raw = (device_details.get('groups_accounts') or {}).get('local_accounts', [])
            if users_raw is not None and isinstance(users_raw, dict) and users_raw.get("user"):
                users_raw_user_object = users_raw["user"]
                if isinstance(users_raw_user_object, dict):
                    users_raw = [users_raw_user_object]
                elif isinstance(users_raw_user_object, list):
                    users_raw = users_raw_user_object
                else:
                    users_raw = []
        except Exception:
            logger.error("Got Exception while fetching users department")
        for user_raw in users_raw:
            try:
                # Taking only "real" users, and not services users like "mcafee user" and such..
                if not ((user_raw.get("home") or "").lower().startswith("/users")):
                    continue

                # Get a list of words for the real name
                user_real_name = re.findall(r"[\w']+", user_raw.get("realname") or '')
                if len(user_real_name) == 0:
                    continue

                # Checking if the some of the user name is part of the hostname. This will help us to determine that
                # this user is the owner of this device
                is_part_of_hostname = False
                for one_word in user_real_name:
                    general_info = device_details['general']
                    if len(one_word) > 2 and one_word in general_info.get('name', ''):
                        is_part_of_hostname = True

                # If the last condition is true, than we should fill this user with department
                if is_part_of_hostname:
                    conditions_list = []
                    for one_word in user_real_name:
                        # We expect each word of the user real name field from Jamf. For example, if the real name is
                        # "Ofir Yefet", we expect to find a user that has the word "ofir", and the word "yefet" in
                        # one of the following fields: first_name, last_name, username
                        conditions_list.append({"$or": [{"adapters.data.first_name":
                                                         {"$regex": f"(?i){one_word}"}},
                                                        {"adapters.data.last_name":
                                                         {"$regex": f"(?i){one_word}"}},
                                                        {"adapters.data.username":
                                                         {"$regex": f"(?i){one_word}"}}]})
                    # We only want users that have the "user_department" field
                    conditions_list.append({"adapters.data.user_department": {"$exists": True}})
                    mongo_filter = {"$and": conditions_list}
                    project_fields = ["adapters.data.first_name", "adapters.data.last_name", "adapters.data.username",
                                      "adapters.data.user_department"]

                    relevant_users = list(self.users_db.find(mongo_filter, project_fields))
                    if len(relevant_users) == 0:
                        # Couldn't find user
                        continue
                    else:
                        # Great!! we found one relevant user (just need to get the department from this user
                        if len(relevant_users) > 1:
                            # Found more then one relevant user
                            logger.warning(f"Found more than one user for {user_real_name} when fetching department. "
                                           f"Taking only first")
                        for relevant_user in relevant_users:
                            for one_adapter in relevant_user.get("adapters", []):
                                if one_adapter.get("data", {}).get("user_department", "") != "":
                                    user_raw["user_department"] = one_adapter["data"]["user_department"]
                                    break
                            if "user_department" in user_raw:
                                break
                        pass
            except Exception:
                logger.exception(f"Error getting users department data for user {user_raw}")

    def threaded_get_devices(self, url, device_list_name, device_type, should_fetch_department=False):
        def get_device(device, device_number):
            try:
                if self.__threads_time_sleep:
                    time.sleep(self.__threads_time_sleep)
                device_id = device['id']
                device_details = self.get(url + '/id/' + device_id).get(device_type)
                if should_fetch_department:
                    # Trying to add the department of local users
                    self.get_users_department(device_details)
                if device_number % print_modulo == 0:
                    logger.info(f"Got {device_number} devices out of {num_of_devices}.")
                device_list.append(device_details)
            except Exception:
                logger.exception(f'error retrieving details of device id {device_id}')
        devices = (self.get(url).get(device_list_name) or {})
        num_of_devices = devices.get('size')
        if num_of_devices:
            num_of_devices = int(num_of_devices)
        if not num_of_devices:
            # for the edge case '0'
            return []
        print_modulo = max(int(num_of_devices / 10), 1)
        devices = devices.get(device_type)
        devices = [devices] if type(devices) != list else devices
        device_list = []
        self._run_in_thread_pool_per_device(devices, get_device)

        return device_list

    def threaded_get_policy_history(self, devices):
        def get_history_worker(device, device_number):
            device_details = {}
            try:
                device['policies'] = []
                device_details = self.get(consts.COMPUTER_HISTORY_URL + (device.get('general') or {}).get('id'))
                policies = device_details[consts.COMPUTER_HISTORY_XML_NAME][
                    consts.COMPUTER_HISTORY_POLICY_LIST_NAME].get(consts.COMPUTER_HISTORY_POLICY_INFO_TYPE, [])
                device_policies = {}
                for policy in reversed(policies):
                    try:
                        policy_key = policy.get('policy_id')
                        policy_date = parse_date(policy.get('date_completed_utc')
                                                 ) or parse_date(policy.get('date_completed'))
                        if not policy_date:
                            logging.warning(f'Bad Policy with no date or key {policy}')
                            continue
                        device_policy = device_policies.get(policy_key)
                        if device_policy is None or device_policy.last_runtime_date < policy_date:
                            device_policy = JamfPolicy()
                            device_policy.policy_id = policy['policy_id']
                            device_policy.policy_name = policy['policy_name']
                            device_policy.last_runtime_date = policy_date
                            device_policy.last_runtime_status = policy['status']
                            device_policy.last_completed_date = parse_date(-1)
                        if policy['status'] == 'Completed' and \
                                (('last_completed_date' not in device_policy.to_dict()) or
                                 (device_policy.last_completed_date < policy_date)):
                            device_policy.last_completed_date = policy_date
                        device_policies[policy_key] = device_policy
                    except Exception:
                        logger.exception(f"failed to parse policy: {policy}")

                device['policies'] = list(device_policies.values())
            except Exception as err:
                logger.debug("An exception occured while getting and parsing device policies.")

            if device_number % print_modulo == 0:
                logger.info(f"Got {device_number} devices out of {num_of_devices}.")
            return device_details

        num_of_devices = len(devices)
        print_modulo = max(int(num_of_devices / 10), 1)
        logger.info("Starting {0} worker threads.".format(self.num_of_simultaneous_devices))
        self._run_in_thread_pool_per_device(devices, get_history_worker)

        return devices

    def get_devices(self,
                    should_fetch_department,
                    should_fetch_policies,
                    num_of_simultaneous_devices,
                    should_not_keepalive,
                    threads_time_sleep
                    ):
        """ Returns a list of all agents
        :return: the response
        :rtype: list of computers and phones
        """
        self.num_of_simultaneous_devices = num_of_simultaneous_devices
        self.__threads_time_sleep = threads_time_sleep
        self.__should_not_keepalive = should_not_keepalive
        if should_not_keepalive is True:
            self.headers['Connection'] = 'close'
        else:
            self.headers.pop('Connection', None)

        # Getting all devices at once so no progress is logged
        # alive_hours/24 evaluates to an int on purpose
        try:
            computers = self.threaded_get_devices(
                url=consts.COMPUTERS_URL,
                device_list_name=consts.COMPUTERS_DEVICE_LIST_NAME,
                device_type=consts.COMPUTER_DEVICE_TYPE,
                should_fetch_department=should_fetch_department)
            if should_fetch_policies:
                self.threaded_get_policy_history(computers)
            yield from computers
        except Exception:
            logger.exception(f'Problem with computers')
        try:
            mobile_devices = self.threaded_get_devices(
                url=consts.MOBILE_DEVICE_URL,
                device_list_name=consts.MOBILE_DEVICE_LIST_NAME,
                device_type=consts.MOBILE_DEVICE_TYPE)
            yield from mobile_devices
        except Exception:
            logger.exception(f'Problem with mobiles')
