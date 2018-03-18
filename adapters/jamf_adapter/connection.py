from concurrent.futures import ThreadPoolExecutor, wait, ALL_COMPLETED
from datetime import datetime
import requests
import base64

from axonius.fields import Field
from axonius.parsing_utils import parse_date
from jamf_adapter.exceptions import JamfConnectionError, JamfRequestException
from jamf_adapter import consts
from axonius.utils.xml2json_parser import Xml2Json
from axonius.smart_json_class import SmartJsonClass


class JamfPolicy(SmartJsonClass):
    """ A definition for a Jamf Policy field"""
    policy_id = Field(int, "Policy Id")
    policy_name = Field(str, "Policy Name")
    last_runtime_date = Field(datetime, "Last Runtime Date")
    last_runtime_status = Field(str, "Last Runtime Status")
    last_completed_date = Field(datetime, "Last Successfully Completed Date")


class JamfConnection(object):
    def __init__(self, logger, domain, num_of_simultaneous_devices,
                 http_proxy=None, https_proxy=None):
        """ Initializes a connection to Jamf using its rest API

        :param obj logger: Logger object of the system
        :param str domain: domain address for Jamf
        """
        self.logger = logger
        url = domain
        if not url.lower().startswith('https://'):
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
        self.logger.info(f"Proxies: {self.proxies}")
        self.num_of_simultaneous_devices = num_of_simultaneous_devices

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
        response = self.get("accounts")

        # the only case where we get 200 and no accounts is if the domain is not the Jamf one
        # i.e. someone lied in the domain and somehow the page <domain>/JSSResource/accounts exists
        if 'accounts' not in response:
            raise JamfConnectionError(str(response))

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
        response = requests.post(self.get_url_request(name), headers=headers, data=data, proxies=self.proxies)
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            raise JamfRequestException(str(e))
        return response.json()

    def get(self, name, headers=None):
        """ Serves a POST request to Jamf API

        :param str name: the name of the page to request
        :param dict headers: the headers for the post request
        :return: the service response or raises an exception if it's not 200
        """
        headers = headers or self.headers
        response = requests.get(self.get_url_request(name), headers=headers, proxies=self.proxies)
        try:
            response.raise_for_status()
            return Xml2Json(response.text).result
        except requests.HTTPError as e:
            raise JamfRequestException(str(e))

    def _run_in_thread_pool_per_device(self, devices, func):
        self.logger.info("Starting {0} worker threads.".format(self.num_of_simultaneous_devices))
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
                self.logger.exception("An exception was raised while trying to get the data.")

        self.logger.info("Finished getting all device data.")

    def threaded_get_devices(self, url, device_list_name, device_type):
        def get_device(device, device_number):
            try:
                device_id = device['id']
                device_details = self.get(url + '/id/' + device_id).get(device_type)
                if device_number % print_modulo == 0:
                    self.logger.info(f"Got {device_number} devices out of {num_of_devices}.")
                device_list.append(device_details)
            except:
                self.logger.exception(f'error retrieving details of device id {device_id}')
        devices = (self.get(url).get(device_list_name) or {})
        num_of_devices = devices.get('size')
        if num_of_devices:
            num_of_devices = int(num_of_devices)
        if not num_of_devices:
            # for the edge case '0'
            return
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
                device_details = self.get(consts.COMPUTER_HISTORY_URL + (device.get('general') or {}).get('id'))
                policies = device_details[consts.COMPUTER_HISTORY_XML_NAME][
                    consts.COMPUTER_HISTORY_POLICY_LIST_NAME].get(consts.COMPUTER_HISTORY_POLICY_INFO_TYPE, [])
                device_policies = {}
                for policy in reversed(policies):
                    try:
                        policy_key = policy['policy_id']
                        policy_date = parse_date(policy['date_completed_utc'])
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
                        self.logger.exception(f"failed to parse policy: {policy}")

                device['policies'] = list(device_policies.values())
            except Exception as err:
                self.logger.exception("An exception occured while getting and parsing device policies.")

            if device_number % print_modulo == 0:
                self.logger.info(f"Got {device_number} devices out of {num_of_devices}.")
            return device_details

        num_of_devices = len(devices)
        print_modulo = max(int(num_of_devices / 10), 1)
        self.logger.info("Starting {0} worker threads.".format(self.num_of_simultaneous_devices))
        self._run_in_thread_pool_per_device(devices, get_history_worker)

        return devices

    def get_devices(self):
        """ Returns a list of all agents
        :return: the response
        :rtype: list of computers and phones
        """
        # Getting all devices at once so no progress is logged
        # alive_hours/24 evaluates to an int on purpose
        computers = self.threaded_get_devices(
            url=consts.COMPUTERS_URL,
            device_list_name=consts.COMPUTERS_DEVICE_LIST_NAME,
            device_type=consts.COMPUTER_DEVICE_TYPE)

        self.threaded_get_policy_history(computers)

        mobile_devices = self.threaded_get_devices(
            url=consts.MOBILE_DEVICE_URL,
            device_list_name=consts.MOBILE_DEVICE_LIST_NAME,
            device_type=consts.MOBILE_DEVICE_TYPE)

        return computers + mobile_devices
