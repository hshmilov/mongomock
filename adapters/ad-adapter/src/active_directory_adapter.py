# TODO ofir: Change the return values protocol

__author__ = "Ofir Yefet"

from axonius.adapter_base import AdapterBase
from axonius.consts import adapter_consts
from axonius.background_scheduler import LoggedBackgroundScheduler
from axonius.plugin_base import add_rule
from axonius.parsing_utils import figure_out_os
from axonius import adapter_exceptions
from ldap_connection import LdapConnection
from base64 import standard_b64decode

from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.executors.pool import ThreadPoolExecutor

import ad_exceptions
import configparser
import subprocess
import os
import sys
import tempfile
import threading
import time
import json
from datetime import datetime, timedelta
from axonius.dns_utils import query_dns

TEMP_FILES_FOLDER = "/home/axonius/temp_dir/"


class ActiveDirectoryAdapter(AdapterBase):
    """ A class containing all the Active Directory capabilities.

    Check AdapterBase documentation for additional params and exception details.

    """

    # Functions
    def __init__(self, **kwargs):
        """Class initialization.

        Check AdapterBase documentation for additional params and exception details.

        """

        # Getting needed paths for execution
        config = configparser.ConfigParser()
        config.read('plugin_config.ini')
        self.__python_27_path = config['paths']['python_27_path']
        self.__use_psexec_path = config['paths']['psexec_path']
        self.__use_wmiquery_path = config['paths']['wmiquery_path']
        self.__ldap_page_size = int(config['others']['ldap_page_size'])

        # Initialize the base plugin (will initialize http server)
        super().__init__(**kwargs)

        self._resolving_thread_lock = threading.RLock()

        executors = {'default': ThreadPoolExecutor(2)}
        self._resolver_scheduler = LoggedBackgroundScheduler(self.logger, executors=executors)

        # Thread for resolving IP addresses of devices
        self._resolver_scheduler.add_job(func=self._resolve_hosts_addr_thread,
                                         trigger=IntervalTrigger(minutes=2),
                                         next_run_time=datetime.now(),
                                         name='resolve_host_thread',
                                         id='resolve_host_thread',
                                         max_instances=1)
        # Thread for resetting the resolving process
        self._resolver_scheduler.add_job(func=self._resolve_change_status_thread,
                                         trigger=IntervalTrigger(seconds=60 * 60 * 5),  # Every five hours
                                         next_run_time=datetime.now() + timedelta(hours=2),
                                         name='change_resolve_status_thread',
                                         id='change_resolve_status_thread',
                                         max_instances=1)

        self._resolver_scheduler.start()

        # create temp files dir
        os.makedirs(TEMP_FILES_FOLDER, exist_ok=True)
        # TODO: Weiss: Ask why not using tempfile to creage dir.

    def _get_client_id(self, dc_details):
        return dc_details['dc_name']

    def _connect_client(self, dc_details):
        try:
            return LdapConnection(self.logger,
                                  self.__ldap_page_size,
                                  dc_details['dc_name'],
                                  dc_details['domain_name'],
                                  dc_details['query_user'],
                                  dc_details['query_password'],
                                  dc_details.get('dns_server_address'))
        except ad_exceptions.LdapException as e:
            message = "Error in ldap process for dc {0}. reason: {1}".format(
                dc_details["dc_name"], str(e))
            self.logger.exception(message)
        except KeyError as e:
            if "dc_name" in dc_details:
                message = "Key error for dc {0}. details: {1}".format(
                    dc_details["dc_name"], str(e))
            else:
                message = "Missing dc name for configuration line"
            self.logger.error(message)
        raise adapter_exceptions.ClientConnectionException(message)

    def _clients_schema(self):
        """
        The keys AdAdapter expects from configs.abs

        :return: json schema
        """
        return {
            "properties": {
                "admin_password": {
                    "type": "password"
                },
                "admin_user": {
                    "type": "string"
                },
                "dc_name": {
                    "type": "string"
                },
                "domain_name": {
                    "type": "string"
                },
                "query_password": {
                    "type": "password"
                },
                "query_user": {
                    "type": "string"
                },
                "dns_server_address": {
                    "type": "string"
                }
            },
            "required": [
                "dc_name",
                "query_user",
                "admin_user",
                "query_password",
                "domain_name",
                "admin_password"
            ],
            "type": "object"
        }

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific Dc

        :param str client_name: The name of the client
        :param str client_data: The data of the client

        :return: iter(dict) with all the attributes returned from the DC per client
        """
        return client_data.get_device_list()

    def _resolve_hosts_addr_thread(self):
        """ Thread for ip resolving of devices.
        This thread will try to resolve IP's of known devices.
        """
        with self._resolving_thread_lock:
            hosts = self._get_collection("devices_data").find({'RESOLVE_STATUS': 'PENDING'},
                                                              projection={'_id': True,
                                                                          'raw.AXON_DNS_ADDR': True,
                                                                          'raw.AXON_DC_ADDR': True,
                                                                          'hostname': True})
            hosts = list(hosts)
            self.logger.info(f"Going to resolve for {len(hosts)} hosts")
            did_one_resolved = False
            for host in hosts:
                time_before_resolve = datetime.now()
                dns_name = host['raw'].get('AXON_DNS_ADDR')
                dc_name = host['raw'].get('AXON_DC_ADDR')
                try:
                    ip = self._resolve_device_name(host['hostname'], {"dns_name": dns_name, "dc_name": dc_name})
                    network_interfaces = [{"MAC": None, "IP": [ip]}]

                    self._get_collection("devices_data").update_one({"_id": host["_id"]},
                                                                    {'$set': {"network_interfaces": network_interfaces,
                                                                              "RESOLVE_STATUS": "RESOLVED"}})
                    did_one_resolved = True
                except Exception as e:
                    self.logger.debug(f"Error resolving host ip from dc. Err: {str(e)}")
                    self._get_collection("devices_data").update_one({"_id": host["_id"]},
                                                                    {'$set': {"network_interfaces": [],
                                                                              "RESOLVE_STATUS": "FAILED"}})
                finally:
                    resolve_time = (datetime.now() - time_before_resolve).microseconds / 1e6  # seconds
                    time_to_sleep = max(0.0, 0.05 - resolve_time)
                    time.sleep(time_to_sleep)
            if not did_one_resolved and len(hosts) != 0:
                # Raise log message only if no host could get resolved
                self.logger.error("Couldn't resolve IP's. Maybe dns is incorrect?")
            return

    def _resolve_change_status_thread(self):
        """ This thread is responsible for restarting the name resolving process
        """
        with self._resolving_thread_lock:
            hosts = self._get_collection("devices_data").find({'RESOLVE_STATUS': 'PENDING'}, limit=2)
            if hosts.count() == 0:
                self._get_collection("devices_data").update_many({}, {'$set': {'RESOLVE_STATUS': 'PENDING'}})
            return

    @add_rule('resolve_ip', methods=['POST'], should_authenticate=False)
    def resolve_ip_now(self):
        jobs = self._resolver_scheduler.get_jobs()
        reset_job = next(job for job in jobs if job.name == 'change_resolve_status_thread')
        reset_job.modify(next_run_time=datetime.now())
        self._resolver_scheduler.wakeup()
        resolve_job = next(job for job in jobs if job.name == 'resolve_host_thread')
        resolve_job.modify(next_run_time=datetime.now())
        self._resolver_scheduler.wakeup()
        return ''

    def _parse_raw_data(self, devices_raw_data):
        devices_collection = self._get_collection("devices_data")
        all_devices = devices_collection.find({}, projection={'_id': False, 'id': True,
                                                              'network_interfaces': True, 'RESOLVE_STATUS': True})
        all_devices_ids = {device['id']: {'network_interfaces': device['network_interfaces'],
                                          'RESOLVE_STATUS': device['RESOLVE_STATUS']} for device in all_devices}
        to_insert = []
        no_timestamp_count = 0
        for device_raw in devices_raw_data:
            if 'userCertificate' in device_raw:
                # Special case where we want to remove 'userCertificate' key
                del device_raw['userCertificate']
            if sys.getsizeof(device_raw) > 1e5:  # Device bigger than ~100kb
                self.logger.error(f"Device name {device_raw.get('dNSHostName', device_raw.get('name', ''))} "
                                  f"is to big for insertion. size is {sys.getsizeof(device_raw)} Bytes")
                continue
            last_seen = device_raw.get('lastLogon', device_raw.get('lastLogonTimestamp'))
            if last_seen is None:
                # No data on the last timestamp of the device. Not inserting this device.
                no_timestamp_count += 1
                continue
            if type(last_seen) != datetime:
                self.logger.error(f"Unrecognized date format for "
                                  f"{device_raw.get('dNSHostName', device_raw.get('name', ''))}. "
                                  f"Got type {type(last_seen)} instead of datetime")
                continue
            # Replacing to non timezone (To fit our schema). We know this is not accurate. But since we use
            # this value in days resolution it is fine
            last_seen.replace(tzinfo=None)

            device_doc = {
                'hostname': device_raw.get('dNSHostName', device_raw.get('name', '')),
                'OS': figure_out_os(device_raw.get('operatingSystem', '')),
                'network_interfaces': [],
                adapter_consts.LAST_SEEN_PARSED_FIELD: last_seen,
                'RESOLVE_STATUS': 'PENDING',
                'id': device_raw['distinguishedName'],
                'raw': device_raw}
            device_interfaces = all_devices_ids.get(device_raw['distinguishedName'])
            if device_interfaces is not None:
                device_doc['network_interfaces'] = device_interfaces['network_interfaces']
                device_doc['RESOLVE_STATUS'] = device_interfaces['RESOLVE_STATUS']
            else:
                to_insert.append(device_doc)
            yield device_doc

        if len(to_insert) > 0:
            devices_collection.insert_many(to_insert)
        if no_timestamp_count != 0:
            self.logger.warning(f"Got {no_timestamp_count} with no timestamp while parsing data")

    def _create_random_file(self, file_buffer, attrib='w'):
        """ Creating a random file in the temp_file folder.

        :param bytes file_buffer: The buffer of the file we want to save
        :param string attrib: The attributes for the 'open' command

        :return string: The name of the file created
        """
        (file_handle_os, os_path) = tempfile.mkstemp(
            suffix='.tmp', dir=TEMP_FILES_FOLDER)

        with os.fdopen(file_handle_os, attrib) as file_obj:
            # Using `os.fdopen` converts the handle to an object that acts like a
            # regular Python file object, and the `with` context manager means the
            # file will be automatically closed when we're done with it.
            file_obj.write(file_buffer)
            return os_path

    def _resolve_device_name(self, device_name, client_config, timeout=2):
        """ Resolve a device name address using dns servers.
        This function will first try to resolve IP using the machine network interface DNS servers.
        If the servers cant find an appropriate IP, The function will try to query the DC (assuming that it
        is also a DNS server).

        :param dict device_name: The name of the device to resolve
        :param dict client_config:  Client data. Must contain 'dc_name'
        :param int timeout: The timeout for the dns query process. Since we try twice the function ca block
                            up to 3*timeout seconds
        :return: The ip address of the device
        :raises exception.IpResolveError: In case of an error in the query process
        """
        # We are assuming that the dc is the DNS server
        full_device_name = device_name

        err = f"Resolving {full_device_name} {client_config}"
        try:
            dns_server = None
            return query_dns(full_device_name, timeout, dns_server)
        except Exception as e:
            err += f"failed to resolve from {dns_server} <{e}>; "

        try:
            dns_server = client_config["dns_name"]
            return query_dns(full_device_name, timeout, dns_server)
        except Exception as e:
            err += f"failed to resolve from {dns_server} <{e}>; "

        try:
            dns_server = client_config["dc_name"]
            return query_dns(full_device_name, timeout, dns_server)
        except Exception as e:
            err += f"failed to resolve from {dns_server} <{e}>; "

        raise ad_exceptions.IpResolveError(err)

    def _get_basic_wmiquery_command(self, device_data):
        """ Function for formatting the base wmiqery command.

        :param dict device_data: The device_data used to create this command
        :return string: The basic command
        """
        clients_config = self._get_clients_config()
        wanted_client = device_data['client_used']
        for client_config in clients_config:
            client_config = client_config['client_config']
            if client_config["dc_name"] == wanted_client:
                # We have found the correct client. Getting credentials
                domain_name, user_name = client_config['admin_user'].split('\\')
                password = client_config['admin_password']
                try:
                    device_ip = self._resolve_device_name(
                        device_data['data']['hostname'], client_config)
                except Exception as e:
                    self.logger.error(f"Could not resolve ip for execution. reason: {str(e)}")
                    raise ad_exceptions.IpResolveError("Cant Resolve Ip")

                # Putting the file using usePsexec.py
                return [self.__python_27_path, self.__use_wmiquery_path, domain_name, user_name, password, device_ip]
        raise ad_exceptions.NoClientError()  # Couldn't find an appropriate client

    def _get_basic_psexec_command(self, device_data):
        """ Function for formatting the base psexec command.

        :param dict device_data: The device_data used to create this command
        :return string: The basic command
        """
        clients_config = self._get_clients_config()
        wanted_client = device_data['client_used']
        for client_config in clients_config:
            client_config = client_config['client_config']
            if client_config["dc_name"] == wanted_client:
                # We have found the correct client. Getting credentials
                domain_name, user_name = client_config['admin_user'].split('\\')
                password = client_config['admin_password']
                try:
                    device_ip = self._resolve_device_name(device_data['data']['hostname'], client_config)
                except Exception as e:
                    self.logger.error(f"Could not resolve ip for execution. reason: {str(e)}")
                    raise ad_exceptions.IpResolveError("Cant Resolve Ip")

                # Putting the file using usePsexec.py
                return [self.__python_27_path, self.__use_psexec_path, "--addr", device_ip, "--username", user_name,
                        "--password", password, "--domain", domain_name]
        raise ad_exceptions.NoClientError()  # Couldn't find an appropriate client

    def put_file(self, device_data, file_buffer, dst_path):
        # Since Active Directory supports only windows, we will take the windows file
        dst_path = dst_path['windows']
        file_buffer = file_buffer['windows']

        # Creating a file from the buffer (to pass it on to PSEXEC)
        file_path = self._create_random_file(file_buffer)
        try:
            # Getting the base command (same for all actions)
            command = self._get_basic_psexec_command(device_data)
            command = command + ["sendfile", "--remote", dst_path, "--local", file_path]

            # Running the command
            command_result = subprocess.run(command, stdout=subprocess.PIPE)

            # Checking if return code is zero, if not, it will raise an exception
            command_result.check_returncode()

            # If we got here that means the the command executed successfuly
            result = 'Success'
            product = str(command_result.stdout)

        except subprocess.CalledProcessError as e:
            result = 'Failure'
            product = str(e)
        except Exception as e:
            raise e
        finally:
            os.remove(file_path)

        return {"result": result, "product": product}

    def get_file(self, device_data, file_path):
        # Since Active Directory supports only windows, we will take the windows file
        remote_file_path = file_path['windows']

        # Creating a file from the buffer (to pass it on to PSEXEC)
        local_file_path = self._create_random_file('')
        try:
            # Getting the base command (same for all actions)
            command = self._get_basic_psexec_command(device_data)
            command = command + ["getfile", "--remote", remote_file_path, "--local", local_file_path]

            # Running the command
            command_result = subprocess.run(command, stdout=subprocess.PIPE)

            # Checking if return code is zero, if not, it will raise an exception
            command_result.check_returncode()

            # If we got here that means the the command executed successfully
            result = 'Success'
            # TODO: Think about other way to send the file
            product = str(file_path)

        except subprocess.CalledProcessError as e:
            result = 'Failure'
            product = str(e)
        except Exception as e:
            raise e
        finally:
            os.remove(file_path)

        return {"result": result, "product": product}

    def execute_binary(self, device_data, binary_buffer):
        # Creating a file from the buffer (to pass it on to PSEXEC)
        # Since Active Directory supports only windows, we will take the windows file
        binary_buffer = standard_b64decode(binary_buffer['windows'])
        exe_path = self._create_random_file(binary_buffer, 'wb')
        try:
            # Getting the base command (same for all actions)
            command = self._get_basic_psexec_command(device_data)
            command = command + ["runexe", "--exepath", exe_path]

            # Running the command
            command_result = subprocess.run(command, stdout=subprocess.PIPE)

            # Checking if return code is zero, if not, it will raise an exception
            command_result.check_returncode()

            result = 'Success'
            product = 'nothing?'

        except subprocess.CalledProcessError as e:
            result = 'Failure'
            product = str(e)
        except Exception as e:
            raise e
        finally:
            os.remove(exe_path)

        return {"result": result, "product": product}

    def execute_wmi_queries(self, device_data, wmi_queries):
        # Creating a file from the buffer (to pass it on to PSEXEC)
        # Adding separator to the commands list
        queries = wmi_queries
        if queries is None:
            return {"result": 'Failure', "product": 'No WMI Queries list command supplied'}

        # Getting the base command (same for all actions)
        command = self._get_basic_wmiquery_command(device_data)
        product = []
        for single_query in queries:
            single_command = command + [single_query]

            self.logger.info("running query {0}".format(single_query))

            # Running the command
            command_result = subprocess.run(
                single_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            # Checking if return code is zero, if not, it will raise an exception
            try:
                command_result.check_returncode()
            except subprocess.CalledProcessError as e:
                raise ValueError("single_query: {0}, stdout: {1}, stderr: {2}, exception: {3}"
                                 .format(single_query,
                                         str(command_result.stdout),
                                         str(command_result.stderr),
                                         str(e)))

            product.append(json.loads(command_result.stdout.strip()))
            self.logger.info("query returned with return code 0 (successfully).")

        # If we got here that means the the command executed successfuly
        result = 'Success'

        return {"result": result, "product": product}

    def execute_shell(self, device_data, shell_command):
        # Creating a file from the buffer (to pass it on to PSEXEC)
        # Adding separator to the commands list
        shell_command_windows = shell_command.get('Windows')
        if shell_command_windows is None:
            return {"result": 'Failure', "product": 'No Windows command supplied'}

        SEPARATOR = '_SEPARATOR_STRING_'
        conf_path = self._create_random_file(SEPARATOR.join(shell_command_windows) + SEPARATOR)

        # Creating a file to write the result to
        result_path = self._create_random_file('')
        try:
            # Getting the base command (same for all actions)
            command = self._get_basic_psexec_command(device_data)
            command = command + ["runshell", "--command_path", conf_path, "--result_path", result_path]

            # Running the command
            command_result = subprocess.run(
                command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            # Checking if return code is zero, if not, it will raise an exception
            command_result.check_returncode()

            # If we got here that means the the command executed successfuly
            result = 'Success'

            result_file = open(result_path, 'r')
            product = str(result_file.read())
            if SEPARATOR in product:
                product = product.split(SEPARATOR)[:-1]
            result_file.close()

        except subprocess.CalledProcessError as e:
            result = 'Failure'
            product = "stdout: {0}, stderr: {1}, exception: {2}"\
                .format(str(command_result.stdout), str(command_result.stderr), str(e))
        except Exception as e:
            raise e
        finally:
            os.remove(conf_path)
            os.remove(result_path)

        return {"result": result, "product": product}

    def delete_file(self, device_data, file_path):
        return {"result": 'Failure', "product": 'Delete file is not implemeted yet'}

        # Exported API functions - None for now
