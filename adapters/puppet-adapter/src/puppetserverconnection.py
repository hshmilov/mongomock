"""puppetserverconnection.py: Logic for connecting to a Puppet Server."""

__author__ = "Ofri Shur"

import requests
import paramiko
import scp
import exceptions
import os
import puppetconfig as config
import socket
import threading


class PuppetServerConnection:

    def __init__(self, logger, puppet_server_address, puppet_username, puppet_password):
        """Class initialization.

        :param obj logger: Logger object of the system
        :param str puppet_server_address: Server address (name or IP)
        :param str puppet_username: User name to connect with to the puppet server
        :param str puppet_password: Password
        """
        self.puppet_server_address = puppet_server_address
        self.puppet_username = puppet_username
        self.puppet_password = puppet_password
        self.logger = logger
        self.ssh_lock = threading.Lock()

        self._make_certificates_directory_and_init_certificates_files_names()
        self.base_puppet_url = config.PUPPET_CONNECTION_METHOD + \
            self.puppet_server_address + config.PUPPET_PORT_STRING
        self._check_certificates_existence()

    def _make_certificates_directory_and_init_certificates_files_names(self):
        """ This function create directories for the SSL certificates of the connection.
        :raises PuppetException in case of problems with creating the directories.
        """
        self.local_SSL_files_locations = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                      self.puppet_server_address,
                                                      config.RELATIVE_SSL_DIRECTORY_LOCATION)

        try:
            if not os.path.exists(self.local_SSL_files_locations):
                os.makedirs(self.local_SSL_files_locations)
            if not os.path.exists(os.path.join(self.local_SSL_files_locations, config.CERTS_FILES_DIRECTORY)):
                os.makedirs(os.path.join(self.local_SSL_files_locations, config.CERTS_FILES_DIRECTORY))
            if not os.path.exists(os.path.join(self.local_SSL_files_locations, config.PRIVATE_KEYS_DIRECTORY)):
                os.makedirs(os.path.join(self.local_SSL_files_locations, config.PRIVATE_KEYS_DIRECTORY))
        except os.error as directory_error:
            self.logger.exception("Error while creating directories")
            raise exceptions.PuppetException(str(directory_error))
        # Init local locations of the certificates files.
        self.certificate_name_in_puppet_server = config.CERTIFICATE_PREFIX_IN_PUPPET_SERVER + self.puppet_server_address

        self.local_ca_file_path = os.path.join(self.local_SSL_files_locations, config.CERTS_FILES_DIRECTORY,
                                               config.CA_FILE_NAME)
        self.certificate_file_name = self.certificate_name_in_puppet_server + config.CERTIFICATES_SUFFIX
        self.local_certificate_file_path = os.path.join(self.local_SSL_files_locations,
                                                        config.CERTS_FILES_DIRECTORY,
                                                        self.certificate_file_name)
        self.local_private_key_file_path = os.path.join(self.local_SSL_files_locations,
                                                        config.PRIVATE_KEYS_DIRECTORY,
                                                        self.certificate_file_name)

    def _enter_root_password_and_log_output_and_error(self, command):
        """ This function send a command to a remote SSH server, add the root password and log the output and error.
         :param str command: The command to execute
         :raises a PuppetException if a problems occurs in the ssh connection
        """
        try:
            ssh_stdin, ssh_stdout, ssh_stderr = self.ssh_client_connection.exec_command(
                command)
        except paramiko.ssh_exception.SSHException as ssh_exception:
            raise exceptions.PuppetException(str(ssh_exception))
        try:
            ssh_stdin.write(self.puppet_password + "\n")
            ssh_stdin.flush()
            data = ssh_stdout.readlines()
            for line in data:
                self.logger.debug("Output of ssh comand:{0}".format(line))
            data = ssh_stderr.readlines()
            for line in data:
                self.logger.debug("Error of ssh comand:{0}".format(line))
        except:
            self.logger.exception("Error occured in ssh command input or output")

    def _generate_certificates_at_puppet_server(self):
        """ This function uses ssh to connect to the puppet server and creates the ssl certificates in the server.
         :raises a PuppetException if a problems occurs in the ssh connection
        """
        self.clean_certificates_command = config.CERTIFICATES_CLEAN_COMMAND + \
            self.certificate_name_in_puppet_server
        self.generate_certificate_command = config.CERTIFICATES_CREATE_COMMAND + \
            self.certificate_name_in_puppet_server
        self.chmod_certificate_command = config.MAKE_FILE_READ_WRITE_TO_EVERYONE_COMMAND + \
            config.PRIVATE_KEYS_LOCATION_IN_PUPPET_SERVER + \
            self.certificate_name_in_puppet_server + \
            config.CERTIFICATES_SUFFIX

        self._enter_root_password_and_log_output_and_error(self.clean_certificates_command)
        self._enter_root_password_and_log_output_and_error(self.generate_certificate_command)
        self._enter_root_password_and_log_output_and_error(self.chmod_certificate_command)

    def _copy_certificates_to_local_space(self):
        """ This function uses ssh and scp to copy the certificates to the local storage.
         :raises a PuppetException if a problems occurs in the ssh or scp connection
        """
        # Define certificate and private key full path in the puppet server
        self.private_key_full_path_puppet_server = config.PRIVATE_KEYS_LOCATION_IN_PUPPET_SERVER + \
            self.certificate_name_in_puppet_server + config.CERTIFICATES_SUFFIX
        self.certificate_full_path_puppet_server = config.CERTIFICATE_LOCATION_IN_PUPPET_SERVER + \
            self.certificate_name_in_puppet_server + config.CERTIFICATES_SUFFIX
        try:
            self.scp_puppet_sever_connection = scp.SCPClient(
                self.ssh_client_connection.get_transport())
            # Copy CA certificate
            self.scp_puppet_sever_connection.get(config.CA_FILE_PUPPET_SERVER_PATH,
                                                 os.path.dirname(self.local_ca_file_path))
            # Copy certificate
            self.scp_puppet_sever_connection.get(self.certificate_full_path_puppet_server,
                                                 os.path.dirname(self.local_certificate_file_path))
            # Copy private key
            self.scp_puppet_sever_connection.get(self.private_key_full_path_puppet_server,
                                                 os.path.dirname(self.local_private_key_file_path))
            self.scp_puppet_sever_connection.close()
        except:
            # Making sure there is no part list of the files.
            if os.path.exists(self.local_ca_file_path):
                os.remove(self.local_ca_file_path)
            if os.path.exists(self.local_certificate_file_path):
                os.remove(self.local_certificate_file_path)
            if os.path.exists(self.local_private_key_file_path):
                os.remove(self.local_private_key_file_path)
            raise exceptions.PuppetException("Exception while copying the certificates.")

    def _generate_certificates_and_copy_to_local_storage(self):
        """ This function uses ssh to connect to the puppet server and creates the ssl certificates in the server.
            And then to copy the certificates to the local storage.
         :raises a PuppetException if a problems occurs in the ssh connection
        """
        try:
            # Connect to the puppet server with SSH
            self.ssh_client_connection = paramiko.SSHClient()
            self.ssh_client_connection.load_system_host_keys()
            self.ssh_client_connection.set_missing_host_key_policy(
                paramiko.AutoAddPolicy())
            self.ssh_client_connection.connect(self.puppet_server_address,
                                               username=self.puppet_username,
                                               password=self.puppet_password)
            self._generate_certificates_at_puppet_server()

            self._copy_certificates_to_local_space()
            # Close the SSH connection
            self.ssh_client_connection.close()
        except (paramiko.ssh_exception.BadHostKeyException,
                paramiko.ssh_exception.AuthenticationException,
                paramiko.ssh_exception.SSHException,
                socket.error) as err:
            raise exceptions.PuppetException(str(err))

    def _check_certificates_existence(self):
        """ This function checks to see if we already have the certificates needed to connect to the puppet server.
            If not it uses ssh to connect to the puppet server and creates the ssl certificates in the server.
            And then to copy the certificates to the local storage.
         :raises a PuppetException if a problems occurs in the ssh connection
        """
        # We need to create the private SSL keys to connect the https API
        try:
            if self.ssh_lock.acquire(timeout=60 * 5) is True:  # Blocks for 5 minutes
                if not (os.path.exists(self.local_ca_file_path) and
                        os.path.exists(self.local_certificate_file_path) and
                        os.path.exists(self.local_private_key_file_path)):
                    self._generate_certificates_and_copy_to_local_storage()
            else:
                self.logger.error("Timeout of ssh process")
                raise exceptions.PuppetException("Timeout of ssh process")
        finally:
            self.ssh_lock.release()

    def get_device_list(self):
        """ This function returns a json with all the data about all the devices in the server.
             :raises a PuppetException if a problems occurs in the response from the server or if ssh problems.
        """
        nodes_query_suffix = config.PUPPET_API_PREFIX + "/nodes"
        nodes_query_url = self.base_puppet_url + nodes_query_suffix
        try:
            query_response = requests.get(nodes_query_url,
                                          cert=(self.local_certificate_file_path, self.local_private_key_file_path),
                                          verify=self.local_ca_file_path)
        except requests.RequestException as err:
            self.logger.exception("Error in querying the nodes from the puppet server." +
                                  " Error information:{0}".format(str(err)))
            raise exceptions.PuppetException("Error in querying the nodes from the puppet server." +
                                             f" Error information:{str(err)}")
        parsed_query_nodes_json = self._parse_json_request(query_response)

        s = requests.Session()
        s.cert = (self.local_certificate_file_path,
                  self.local_private_key_file_path)
        s.verify = self.local_ca_file_path
        for json_node in parsed_query_nodes_json:
            try:
                yield self._query_fact_device(s, json_node)
            except exceptions.PuppetException as err:
                self.logger.exception(f"Error in getting information about node:{str(json_node)}. Error:{str(err)}")

    def _query_fact_device(self, opened_session, basic_json_node=None):
        """ This function gets a json with basic information about a node (or nothing if not needed),
            and query all the facts about the node and returns it as a json.
            :param requests.Session opened_session: An opened session (to increase performance)
            :param dict basic_json_node A dictionary with basic puppet information about the device
            :raises a PuppetException if a problems occurs in the response from the server or if ssh problems.
            :return device: a dict with all the facts on this device 
        """
        device = dict()
        if basic_json_node is not None:
            for basic_attribute in basic_json_node.items():
                device[basic_attribute[0]] = basic_attribute[1]

        facts_query_suffix = config.PUPPET_API_PREFIX + \
            "/nodes/" + basic_json_node['certname'] + "/facts"
        facts_query_url = self.base_puppet_url + facts_query_suffix
        try:
            query_response = opened_session.get(facts_query_url)
        except requests.RequestException as err:
            raise exceptions.PuppetException(str(err))
        parsed_query_facts = self._parse_json_request(query_response)
        for json_fact in parsed_query_facts:
            # Add check in dictionary
            device[json_fact['name']] = json_fact['value']
        return device

    def _parse_json_request(self, response):
        """ This function check the response of the query and parse the normal respond to a json.
            :raises a PuppetException if a problems occurs in the response from the server.
        """
        if response.ok:
            return response.json()
        else:
            raise exceptions.PuppetException("Query failed:" + str(response.status_code))
