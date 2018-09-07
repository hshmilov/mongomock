import logging
logger = logging.getLogger(f'axonius.{__name__}')
import requests

from cisco_meraki_adapter.exceptions import CiscoMerakiAlreadyConnected, CiscoMerakiConnectionError, CiscoMerakiNotConnected, \
    CiscoMerakiRequestException


class CiscoMerakiConnection(object):
    def __init__(self, domain, apikey, verify_ssl):
        """ Initializes a connection to CiscoMeraki using its rest API

        :param str domain: domain address for CiscoMeraki
        :param bool verify_ssl Verify the ssl
        """
        self.domain = domain
        url = domain
        if not url.lower().startswith('https://'):
            url = 'https://' + url
        if not url.endswith('/'):
            url += '/'
        url += 'api/v0/'
        self.url = url
        self.session = None
        self.apikey = apikey
        self.verify_ssl = verify_ssl
        self.headers = {'Accept': 'application/json', 'charset': 'utf-8',
                        'Content-Type': 'application/json', 'X-Cisco-Meraki-API-Key': self.apikey}

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
            raise CiscoMerakiAlreadyConnected()
        session = requests.Session()
        if self.apikey is not None:
            response = session.get(self._get_url_request('organizations'), headers=self.headers, verify=self.verify_ssl)
            try:
                response.raise_for_status()
            except requests.HTTPError as e:
                raise ConnectionError(str(e))
        else:
            raise CiscoMerakiConnectionError("No Apikey")
        self.session = session

    def __del__(self):
        if hasattr(self, 'session') and self.is_connected:
            self.close()

    def close(self):
        """ Closes the connection """
        self.session.close()
        self.session = None

    def _get(self, name, params=None):
        """ Serves a GET request to CiscoMeraki API

        :param str name: the name of the request
        :param dict params: Additional parameters
        :return: the response
        :rtype: dict
        """
        if not self.is_connected:
            raise CiscoMerakiNotConnected()
        params = params or {}
        response = self.session.get(self._get_url_request(name), params=params,
                                    headers=self.headers, verify=self.verify_ssl)
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            raise CiscoMerakiRequestException(str(e))
        return response.json()

    def get_device_list(self, **kwargs):
        """ Returns a list of all agents

        :param dict kwargs: api query *string* parameters (ses CiscoMeraki's API documentation for more info)
        :return: the response
        :rtype: dict
        """
        organizations = []
        for organization_raw in self._get("organizations"):
            organizations.append(str(organization_raw['id']))
        logger.info(f"Got oragnizations: {str(organizations)}")

        networks_raw = []
        for organization in organizations:
            try:
                networks_organization_raw = self._get("organizations/" + str(organization) + "/networks")
                for network_raw in networks_organization_raw:
                    networks_raw.append(network_raw)
            except Exception:
                logger.exception(f'Got problem getting networks from org: {organization}')
        logger.info(f"Got networks: {str(networks_raw)}")

        devices = []
        for network_raw in networks_raw:
            try:
                devices_network_raw = self._get("networks/" + str(network_raw.get("id")) + "/devices")
                for device_raw in devices_network_raw:
                    device_raw["network_name"] = network_raw.get("name")
                devices.extend(devices_network_raw)
            except Exception:
                logger.exception(f'Problem getting devices in network {network_raw}')
        logger.info(f"Got number of devices: {len(devices)}")
        # Clients are the devices under the Cisco devices. PAY ATTENTION that we couldn't connect clients in our trial model. We must find a way to check this.
        clients = []
        for device in devices:
            try:
                serial = device.get('serial')
                if serial is None or serial == "":
                    continue
                # Take clients from the last 48 hours
                clients_device_raw = self._get("devices/" + str(serial) + "/clients?timespan=" + str(86400 * 2))
                for client_raw in clients_device_raw:
                    client_raw["associated_device"] = serial
                    client_raw["address"] = device.get("address")
                    client_raw["network_name"] = device.get("network_name")
                clients.extend(clients_device_raw)
            except Exception:
                logger.exception(f"Problem getting clients for device {str(device)}")
        logger.info(f"Got number of clients: {len(clients)}")

        return {'devices': devices, 'clients': clients}

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, type, value, tb):
        self.close()
