"""ActiveDirectoryPlugin.py: Implementation of the ActiveDirectory Adapter."""
# TODO ofir: Change the return values protocol

__author__ = "Ofir Yefet"

from axonius.AdapterBase import AdapterBase
from axonius.ParsingUtils import figure_out_os
from LdapConnection import LdapConnection
from base64 import standard_b64decode

import exceptions
import configparser
import subprocess
import uuid
import os
import errno
import dns.resolver
import tempfile

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
                                                                     dc_details['query_password'])
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
                    "type": "string"
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
                    "type": "string"
                },
                "query_user": {
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

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            yield{
                'name': device_raw['name'],
                'os': figure_out_os(device_raw['operatingSystem']),
                'id': device_raw['distinguishedName'],
                'raw': device_raw}

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

    def _resolve_device_name(self, device_data, client_config):
        # We are assuming that the dc is the DNS server
        dns_server_address = client_config["dc_name"]
        my_res = dns.resolver.Resolver()
        my_res.nameservers = [dns_server_address]
        device_name = device_data['data']['name']
        device_domain = client_config['domain_name'].replace(
            'DC=', '').replace(',', '.')
        full_device_name = device_name + '.' + device_domain
        answer = my_res.query(full_device_name)
        ip = str(answer.response.answer[0].items[0])
        return ip

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
                device_ip = self._resolve_device_name(
                    device_data, client_config)

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
        conf_path = self._create_random_file(shell_command['windows'])

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
