from axonius.adapter_base import AdapterBase
from axonius.adapter_exceptions import ClientConnectionException
from axonius.devices.device import Device
from axonius.utils.files import get_local_config_file
from axonius.fields import Field

from gotoassist_adapter.connection import GotoassistConnection
from gotoassist_adapter.exceptions import GotoassistException
import json
from axonius.parsing_utils import parse_date


class GotoassistAdapter(AdapterBase):

    class MyDevice(Device):
        company_id = Field(str, 'Company ID')

    def __init__(self):
        super().__init__(get_local_config_file(__file__))

    def _get_client_id(self, client_config):
        return client_config['user_name']

    def _connect_client(self, client_config):
        try:
            connection = GotoassistConnection(logger=self.logger, domain=client_config["Gotoassist_Domain"])
            connection.set_credentials(client_id=client_config["client_id"], client_secret=client_config["client_secret"],
                                       username=client_config["user_name"], password=client_config["password"])
            with connection:
                pass  # check that the connection credentials are valid
            return connection
        except GotoassistException as e:
            message = "Error connecting to client with domain {0}, reason: {1}".format(
                client_config['Gotoassist_Domain'], str(e))
            self.logger.exception(message)
            raise ClientConnectionException(message)

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific Gotoassist domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a Gotoassist connection

        :return: A json with all the attributes returned from the Gotoassist Server
        """
        with client_data:
            return client_data.get_device_list()

    def _clients_schema(self):
        """
        The schema GotoassistAdapter expects from configs

        :return: JSON scheme
        """
        return {
            "items": [
                {
                    "name": "Gotoassist_Domain",
                    "title": "Gotoassist Domain",
                    "type": "string"
                },
                {
                    "name": "client_id",
                    "title": "Client Id",
                    "type": "string"
                },
                {
                    "name": "client_secret",
                    "title": "Client Secret",
                    "type": "string"
                },
                {
                    "name": "user_name",
                    "title": "User Name",
                    "type": "string"
                },
                {
                    "name": "password",
                    "title": "Password",
                    "type": "string",
                    "format": "password"
                }
            ],
            "required": [
                "Gotoassist_Domain",
                "username",
                "password",
                "client_secret",
                "client_id"
            ],
            "type": "array"
        }

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            try:
                if device_raw.get("machineStatus", "Online") != "Online":
                    continue
                device = self._new_device()
                device_id = device_raw.get("machineUuid")
                if device_id is None:
                    self.logger.warning("Warning! machineUuid is None..")
                    continue
                device.id = device_id
                device.hostname = device_raw.get("dnsName")
                device.name = device_raw.get("machineName")

                try:
                    ip_address = device_raw.get("ipAddress")
                    if ip_address is not None:
                        device.add_nic(None, ip_address, self.logger)
                except:
                    self.logger.exception("Problem with adding nic to Gotoassist device")
                device.company_id = device_raw.get("companyId")
                device.set_raw(device_raw)
                yield device
            except:
                self.logger.exception("Problem with fetching Gotoassist Device: {str(device_raw)}")
