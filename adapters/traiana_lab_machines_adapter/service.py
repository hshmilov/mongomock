import requests

from axonius.adapter_base import AdapterBase
from axonius.adapter_exceptions import ClientConnectionException, CredentialErrorException
from axonius.devices.device import Device
from axonius.utils.files import get_local_config_file


class TraianaLabMachinesAdapter(AdapterBase):
    """
    TraianaLabMachinesAdapter: An adapter for a proprietary system that exists in Traiana, a client of ours.
    The following is based on https://axonius.atlassian.net/wiki/spaces/AX/pages/398819329/Traiana+17-01-2018
    """

    class MyDevice(Device):
        pass

    def __init__(self):
        super().__init__(get_local_config_file(__file__))

    def _get_client_id(self, client_config):
        return client_config["api_url"]

    def _connect_client(self, client_config):
        api_url = client_config['api_url']
        self.logger.info(f"Added a client with url '{api_url}'")

        # Try to connect to this url. This is the only way for us to check that things work.
        try:
            resp = requests.get(api_url)
        except requests.exceptions.RequestException as e:
            self.logger.exception(f"Failed adding url {api_url} as client")
            raise ClientConnectionException(
                "Failed adding client {0}: {1}".format(api_url, repr(e)))

        if resp.status_code != 200:
            raise ClientConnectionException(
                "Failed adding client {0}: got status code {1} instead of 200".format(api_url, resp.status_code))

        # All good.
        return api_url

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices.

        :param str client_name: the name of the client, which is the url.
        :param client_data: the client data, which is also the url.
        :return: a list of raw devices.
        """

        try:
            # Getting all devices at once so no progress is logged
            resp = requests.get(client_data)
            if resp.status_code != 200:
                raise ValueError("Status code from query devices on {0} should be 200, but its {1}".format(
                    client_data, resp.status_code))

            return resp.json()
        except (requests.exceptions.RequestException, ValueError) as e:
            self.logger.exception("Got an exception when querying {0}".format(client_data))
            raise CredentialErrorException(repr(e))

    def _clients_schema(self):
        """
        In general, we just need the url.

        :return: JSON scheme
        """
        return {
            "items": [
                {
                    "name": "api_url",
                    "title": "API URL",
                    "type": "string"
                }
            ],
            "required": [
                "api_url"
            ],
            "type": "array"
        }

    def _parse_raw_data(self, raw_data):
        devices_raw = raw_data['data']
        for device_raw in devices_raw:
            device = self._new_device()
            device.name = device_raw.get("name", "unknown")
            device.id = device_raw['id']
            device.figure_os(device_raw.get("os", ""))
            device.add_nic('', [device_raw.get("ip")] if device_raw.get("ip") else [], self.logger)
            device.set_raw(device_raw)
            yield device
