from concurrent.futures import ThreadPoolExecutor, wait, ALL_COMPLETED
from datetime import datetime
import requests
import base64

from axonius.fields import Field
from axonius.parsing_utils import parse_date
from jamf_adapter.exceptions import JamfConnectionError, JamfRequestException
from jamf_adapter.search import JamfAdvancedSearch
from jamf_adapter import consts
import xml.etree.cElementTree as ET
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
    def __init__(self, logger, domain, search_name, all_permissions, num_of_simultaneous_devices,
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
        self.headers = {}
        self.auth = None
        self.proxies = {}
        if http_proxy is not None:
            self.proxies['http'] = http_proxy
        if https_proxy is not None:
            self.proxies['https'] = https_proxy
        self.logger.info(f"Proxies: {self.proxies}")
        self.all_permissions = all_permissions
        self.search_name = search_name
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

    def jamf_request(self, request_method, url_addition, data, error_message):
        post_headers = self.headers
        post_headers['Content-Type'] = 'application/xml'
        response = request_method(self.get_url_request(url_addition),
                                  headers=post_headers,
                                  data=data,
                                  proxies=self.proxies)
        try:
            response.raise_for_status()
            response_tree = ET.fromstring(response.text)
            int(response_tree.find("id").text)
        except ValueError:
            # conversion of the query id to int failed
            self.logger.exception(error_message + f": {response.text}")
            raise JamfRequestException(error_message + f": {response.text}")
        except Exception as e:
            # any other error during creation of the query or during the conversion
            self.logger.exception(error_message)
            raise JamfRequestException(error_message + str(e))

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

    def _get_jamf_devices(self, url, data, xml_name, device_list_name, device_type):
        """ Returns a list of all computers

        :return: the response
        :rtype: list of computers
        """
        search = JamfAdvancedSearch(self, url, data, self.search_name, self.all_permissions)
        # update has succeeded or an exception would have been raised
        with search:
            devices = search.search_results[xml_name][device_list_name].get(device_type, [])

        return [devices] if type(devices) == dict else devices

    def get_policy_history(self, devices):
        def get_history_worker(device, device_number):
            device_details = {}
            try:
                device_details = self.get(consts.COMPUTER_HISTORY_URL + device.get('id'))
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

            if (num_of_devices / device_number) % 10 == 0:
                self.logger.info(f"Got {device_number} devices out of {num_of_devices}.")
            return device_details

        self.logger.info("Starting {0} worker threads.".format(self.num_of_simultaneous_devices))
        with ThreadPoolExecutor(max_workers=self.num_of_simultaneous_devices) as executor:
            try:
                device_counter = 0
                num_of_devices = len(devices)
                futures = []

                # Creating a future for all the device summaries to be executed by the executors.
                for device in devices:
                    device_counter += 1
                    futures.append(executor.submit(
                        get_history_worker, device, device_counter))

                wait(futures, timeout=None, return_when=ALL_COMPLETED)
            except Exception as err:
                self.logger.exception("An exception was raised while trying to get the data.")

        self.logger.info("Finished getting all device data.")

        return devices

    def get_devices(self, alive_hours):
        """ Returns a list of all agents
        :return: the response
        :rtype: list of computers and phones
        """
        # Getting all devices at once so no progress is logged
        # alive_hours/24 evaluates to an int on purpose
        computers = self._get_jamf_devices(
            url=consts.ADVANCED_COMPUTER_SEARCH_URL,
            data=consts.ADVANCED_COMPUTER_SEARCH.format(self.search_name, int(alive_hours / 24)),
            xml_name=consts.ADVANCED_COMPUTER_SEARCH_XML_NAME,
            device_list_name=consts.ADVANCED_COMPUTER_SEARCH_DEVICE_LIST_NAME,
            device_type=consts.COMPUTER_DEVICE_TYPE)

        self.get_policy_history(computers)

        mobile_devices = self._get_jamf_devices(
            url=consts.ADVANCED_MOBILE_SEARCH_URL,
            data=consts.ADVANCED_MOBILE_SEARCH.format(self.search_name, int(alive_hours / 24)),
            xml_name=consts.ADVANCED_MOBILE_SEARCH_XML_NAME,
            device_list_name=consts.ADVANCED_MOBILE_SEARCH_DEVICE_LIST_NAME,
            device_type=consts.MOBILE_DEVICE_TYPE)

        return computers + mobile_devices
