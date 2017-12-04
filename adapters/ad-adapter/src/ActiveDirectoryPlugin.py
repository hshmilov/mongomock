"""ActiveDirectoryPlugin.py: Implementation of the ActiveDirectory Adapter."""
# TODO ofir: Change the return values protocol

__author__ = "Ofir Yefet"

from axonius.AdapterBase import AdapterBase
from axonius.PluginBase import add_rule
from axonius.ParsingUtils import figure_out_os
from LdapConnection import LdapConnection
from base64 import standard_b64decode

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.executors.pool import ThreadPoolExecutor

import exceptions
import configparser
import subprocess
import uuid
import os
import socket
import errno
import dns.resolver
import tempfile
import threading
import time
from datetime import datetime, timedelta

# Plugin Version (Should be updated with each new version)
AD_VERSION = '1.0.0'
PLUGIN_TYPE = 'ad_adapter'


class ActiveDirectoryPlugin(AdapterBase):
    """ A class containing all the Active Directory capabilities.

    Check AdapterBase documentation for additional params and exception details.

    """

    # Functions
    def __init__(self, **kargs):
        """Class initialization.

        Check AdapterBase documentation for additional params and exception details.

        """

        # Initialize the base plugin (will initialize http server)
        super().__init__(**kargs)

        # Getting needed paths for execution
        config = configparser.ConfigParser()
        config.read('plugin_config.ini')
        self.python_27_path = config['paths']['python_27_path']
        self.use_psexec_path = config['paths']['psexec_path']

        self._resolving_thread_lock = threading.RLock()

        executors = {'default': ThreadPoolExecutor(2)}
        self._resolver_scheduler = BackgroundScheduler(
            executors=executors)
        # Thread for resolving IP addresses of devices
        self._resolver_scheduler.add_job(func=self._resolve_hosts_addr_thread,
                                         trigger=IntervalTrigger(
                                             minutes=2),
                                         next_run_time=datetime.now(),
                                         name='resolve_host_thread',
                                         id='resolve_host_thread',
                                         max_instances=1)
        # Thread for resetting the resolving process
        self._resolver_scheduler.add_job(func=self._resolve_change_status_thread,
                                         trigger=IntervalTrigger(
                                             seconds=60 * 60 * 2),  # Every two hours
                                         next_run_time=datetime.now() + timedelta(hours=1),
                                         name='change_resolve_status_thread',
                                         id='change_resolve_status_thread',
                                         max_instances=1)
        self._resolver_scheduler.start()

        # Try to create temp files dir
        try:
            os.mkdir("temp_files")
        except FileExistsError:
            pass  # Folder exists

    def _parse_clients_data(self, clients_config):
        # Each client inside _clients will hold an open LDAP connection object
        clients_dict = dict()
        for dc_details in clients_config:
            try:
                clients_dict[dc_details["dc_name"]] = LdapConnection(dc_details['dc_name'],
                                                                     dc_details['domain_name'],
                                                                     dc_details['query_user'],
                                                                     dc_details['query_password'],
                                                                     dc_details.get('dns_server_address'))
            except exceptions.LdapException as e:
                self.logger.error("Error in ldap process for dc {0}. reason: {1}".format(
                    dc_details["dc_name"], str(e)))
            except KeyError as e:
                if "dc_name" in dc_details:
                    self.logger.error("Key error for dc {0}. details: {1}".format(
                        dc_details["dc_name"], str(e)))
                else:
                    self.logger.error("Missing dc name for configuration line")
        return clients_dict

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
        try:
            return client_data.get_device_list()
        except exceptions.LdapException as e:
            self.logger.error(
                "Error while trying to get devices. Details: {0}", str(e))
            return str(e), 500

    def _resolve_hosts_addr_thread(self):
        """ Thread for ip resolving of devices.
        This thread will try to resolve IP's of known devices.
        """
        with self._resolving_thread_lock:
            hosts = self._get_collection("devices_data").find({'RESOLVE_STATUS': 'PENDING'},
                                                              projection={'_id': True,
                                                                          'raw.AXON_DNS_ADDR': True,
                                                                          'raw.AXON_DOMAIN_NAME': True,
                                                                          'hostname': True})

            for host in hosts:
                time_before_resolve = datetime.now()
                dns_name = host['raw']['AXON_DNS_ADDR']
                domain_name = host['raw']['AXON_DOMAIN_NAME']
                try:
                    ip = self._resolve_device_name(host['hostname'], {"dns_name": dns_name, "domain_name": domain_name})
                    network_interfaces = [{"MAC": None, "private_ip": [ip], "public_ip": []}]

                    self._get_collection("devices_data").update_one({"_id": host["_id"]},
                                                                    {'$set': {"network_interfaces": network_interfaces,
                                                                              "RESOLVE_STATUS": "RESOLVED"}})
                except Exception as e:
                    self.logger.error(f"Error resolving host ip from dc. Err: {str(e)}")
                    self._get_collection("devices_data").update_one({"_id": host["_id"]},
                                                                    {'$set': {"network_interfaces": [],
                                                                              "RESOLVE_STATUS": "FAILED"}})
                finally:
                    resolve_time = (datetime.now() - time_before_resolve).microseconds / 1e6  # seconds
                    time_to_sleep = max(0, 0.05 - resolve_time)
                    time.sleep(time_to_sleep)
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
        for device_raw in devices_raw_data:
            device_doc = {
                'hostname': device_raw['name'],
                'OS': figure_out_os(device_raw['operatingSystem']),
                'network_interfaces': [],
                'RESOLVE_STATUS': 'PENDING',
                'id': device_raw['distinguishedName'],
                'raw': device_raw}

            device_from_db = devices_collection.find({'id': device_raw['distinguishedName']})
            if device_from_db.count() > 0:
                # Device is on DB
                device_from_db = next(device_from_db)
                device_doc['network_interfaces'] = device_from_db['network_interfaces']
                device_doc['RESOLVE_STATUS'] = device_from_db['RESOLVE_STATUS']
            devices_collection.replace_one({'id': device_raw['distinguishedName']}, device_doc, upsert=True)

            yield device_doc

    def _create_random_file(self, file_buffer, attrib='w'):
        """ Creating a random file in the temp_file folder.

        :param bytes file_buffer: The buffer of the file we want to save
        :param string attrib: The attributes for the 'open' command

        :return string: The name of the file created
        """
        (file_handle_os, os_path) = tempfile.mkstemp(
            suffix='.tmp', dir='temp_files')

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
                            up to 2*timeout seconds
        :return: The ip address of the device
        :raises exception.IpResolveError: In case of an error in the query process
        """
        # We are assuming that the dc is the DNS server
        device_domain = client_config['domain_name'].replace(
            'DC=', '').replace(',', '.')
        full_device_name = device_name + '.' + device_domain

        dns_server_address = client_config.get("dns_name")
        if not dns_server_address:
            dns_server_address = client_config["dc_name"]
        try:
            # Try resolving using my dns list and the dns list. I am starting with the default dns list since
            # It is more likely that they provide dns services than the DC
            my_res = dns.resolver.Resolver()
            my_res.timeout = timeout
            my_res.lifetime = timeout
            my_res.nameservers.append(dns_server_address)
            answer = my_res.query(full_device_name, 'A')
        except Exception as e:
            try:
                # Trying only our DC
                my_res.nameservers = [dns_server_address]
                answer = my_res.query(full_device_name)
            except Exception as e2:
                raise exceptions.IpResolveError(f"Couldnt resolve IP. DC error: {str(e2)}, global dns error: {str(e)}")

        for rdata in answer:
            try:
                proposed_ip = str(rdata)
                socket.inet_aton(proposed_ip)
            except socket.error:
                continue
            return proposed_ip

        # If we got here that means that we couldnt find an appropriate ip for this device
        raise exceptions.IpResolveError(f"Could not find an appropriate ip")

    def _get_basic_psexec_command(self, device_data):
        """ Function for formatting the base psexec command.

        :param dict device_data: The device_data used to create this command
        :return string: The basic command
        """
        clients_config = self._get_clients_config()
        wanted_client = device_data['client_used']
        for client_config in clients_config:
            if client_config["dc_name"] == wanted_client:
                # We have found the correct client. Getting credentials
                domain_name, user_name = client_config['admin_user'].split(
                    '\\')
                password = client_config['admin_password']
                try:
                    device_ip = self._resolve_device_name(
                        device_data['data']['hostname'], client_config)
                except Exception as e:
                    self.logger.error(f"Could not resolve ip for execution. reason: {str(e)}")
                    raise exceptions.IpResolveError("Cant Resolve Ip")

                # Putting the file using usePsexec.py
                command = ('{py} {psexec} --addr {addr} --username "{user}" '
                           '--password "{password}" --domain "{domain}"').format(py=self.python_27_path,
                                                                                 psexec=self.use_psexec_path,
                                                                                 addr=device_ip,
                                                                                 user=user_name,
                                                                                 password=password,
                                                                                 domain=domain_name)
                return command
        raise exceptions.NoClientError()  # Couldn't find an appropriate client

    def put_file(self, device_data, file_buffer, dst_path):
        # Since Active Directory supports only windows, we will take the windows file
        dst_path = dst_path['windows']
        file_buffer = file_buffer['windows']

        # Creating a file from the buffer (to pass it on to PSEXEC)
        file_path = self._create_random_file(file_buffer)
        try:
            # Getting the base command (same for all actions)
            base_command = self._get_basic_psexec_command(device_data)

            # Building the full command
            command = "{base_command} sendfile --remote {remote} --local {local}".format(base_command=base_command,
                                                                                         remote=dst_path,
                                                                                         local=file_path)
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
            base_command = self._get_basic_psexec_command(device_data)

            # Building the full command
            command = "{base_command} getfile --remote {remote} --local {local}".format(base_command=base_command,
                                                                                        remote=remote_file_path,
                                                                                        local=local_file_path)
            # Running the command
            command_result = subprocess.run(command, stdout=subprocess.PIPE)

            # Checking if return code is zero, if not, it will raise an exception
            command_result.check_returncode()

            # If we got here that means the the command executed successfuly
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
            base_command = self._get_basic_psexec_command(device_data)

            # Building the full command
            command = "{base_command} runexe --exepath {exe_path}".format(base_command=base_command,
                                                                          exe_path=exe_path)
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

    def execute_shell(self, device_data, shell_command):
        # Creating a file from the buffer (to pass it on to PSEXEC)
        # Adding separator to the commands list
        SEPARATOR = '_SEPARATOR_STRING_'
        conf_path = self._create_random_file(SEPARATOR.join(shell_command['Windows']) + SEPARATOR)

        # Creating a file to write the result to
        result_path = self._create_random_file('')
        try:
            # Getting the base command (same for all actions)
            base_command = self._get_basic_psexec_command(device_data)

            # Building the full command
            command = ("{base_command} runshell --command_path {command_path} "
                       "--result_path {result_path}").format(base_command=base_command,
                                                             command_path=conf_path,
                                                             result_path=result_path)

            # Running the command
            command_result = subprocess.run(
                command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)

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
            product = str(command_result.stdout)
        except Exception as e:
            raise e
        finally:
            os.remove(conf_path)
            os.remove(result_path)

        return {"result": result, "product": product}

    def delete_file(self, device_data, file_path):
        return {"result": 'Failure', "product": 'Delete file is not implemeted yet'}

    # Exported API functions - None for now
