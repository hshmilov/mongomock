import requests
import logging
logger = logging.getLogger(f"axonius.{__name__}")
from oracle_vm_adapter.exceptions import OracleVmAlreadyConnected, OracleVmConnectionError, OracleVmNotConnected, \
    OracleVmRequestException


class OracleVmConnection(object):
    def __init__(self, domain, verify_ssl):
        """ Initializes a connection to OracleVm using its rest API

        :param str domain: domain address for OracleVm
        :param bool verify_ssl Verify the ssl
        """
        self.domain = domain
        url = domain
        if not url.lower().startswith('https://'):
            url = 'https://' + url
        if not url.endswith('/'):
            url += '/'
        url += 'ovm/core/wsapi/rest/'
        self.url = url
        self.session = None
        self.username = None
        self.password = None
        self.verify_ssl = verify_ssl
        self.headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}

    def set_credentials(self, username, password):
        """ Set the connection credentials

        :param str username: The username
        :param str password: The password
        """
        self.username = username
        self.password = password

    def _get_url_request(self, request_name):
        """ Builds and returns the full url for the request

        :param request_name: the request name
        :return: the full request url
        """
        return self.url + request_name

    @property
    def is_connected(self):
        return self.session is not None

    def connect(self):
        """ Connects to the service """
        if self.is_connected:
            raise OracleVmAlreadyConnected()
        session = requests.Session()
        if self.username is not None and self.password is not None:
            try:
                response = session.get(self._get_url_request('Manager'), auth=(
                    self.username, self.password), verify=self.verify_ssl, timeout=(5, 30))
                response.raise_for_status()
                if response.json()[0].upper() != 'RUNNING':
                    raise OracleVmConnectionError(f"Server not in Running mode. Response was {response.text}")
            except requests.HTTPError as e:
                raise OracleVmConnectionError(str(e))
        else:
            raise OracleVmConnectionError("No user name or password")
        self.session = session

    def __del__(self):
        if hasattr(self, 'session') and self.is_connected:
            self.close()

    def close(self):
        """ Closes the connection """
        self.session.close()
        self.session = None

    def _post(self, name, params=None):
        """ Serves a POST request to OracleVm API

        :param str name: the name of the request
        :param dict params: Additional parameters
        :return: the response
        :rtype: dict
        """
        if not self.is_connected:
            raise OracleVmNotConnected()
        params = params or {}
        response = self.session.post(self._get_url_request(name), json=params,
                                     headers=self.headers, verify=self.verify_ssl, timeout=(5, 30))
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            raise OracleVmRequestException(str(e))
        return response.json()

    def _get(self, name, params=None):
        """ Serves a GET request to OracleVm API

        :param str name: the name of the request
        :param dict params: Additional parameters
        :return: the response
        :rtype: dict
        """
        if not self.is_connected:
            raise OracleVmNotConnected()
        params = params or {}
        response = self.session.get(self._get_url_request(name), params=params,
                                    headers=self.headers, verify=self.verify_ssl, timeout=(5, 30))
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            raise OracleVmRequestException(str(e))
        return response.json()

    def get_device_list(self, **kwargs):
        """ Returns a list of all agents

        :param dict kwargs: api query *string* parameters (ses OracleVm's API documentation for more info)
        :return: the response
        :rtype: dict
        """
        servers_raw = []
        vms_raw = []
        try:
            servers_raw = self._get('Server')
            for server_raw in servers_raw:
                ethernet_port_ids = list(server_raw.get("ethernetPortIds", []))
                etherent_ports_data = []
                for ethernet_port_id in ethernet_port_ids:
                    try:
                        etherent_ports_data.append(self._get(ethernet_port_id.get("uri"), ""))
                    except Exception:
                        logger.exception(f"Problem getting ethernet port for server {server_raw}")
                server_raw['ethernet_ports_data'] = etherent_ports_data
        except Exception:
            logger.exception("Problem getting servers")
        try:
            vms_raw = self._get('Vm')
            for vm_raw in vms_raw:
                virtual_nics_ids = list(vm_raw.get("virtualNicIds", []))
                virtual_nics_data = []
                for virtual_nic_id in virtual_nics_ids:
                    try:
                        virtual_nics_data.append(self._get(virtual_nic_id.get("uri"), ""))
                    except Exception:
                        logger.exception(f"Problem getting virtual nic for vm {vm_raw}")
            vm_raw['virtual_nics_data'] = virtual_nics_data
        except Exception:
            logger.exception("Problem getting vms")
        return {'servers': servers_raw, 'vms': vms_raw}

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, type, value, tb):
        self.close()
