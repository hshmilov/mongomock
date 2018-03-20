from axonius.adapter_base import AdapterBase
from axonius.adapter_exceptions import ClientConnectionException
from axonius.devices.device import Device
from axonius.utils.files import get_local_config_file
from axonius.fields import Field

from bigfix_adapter.connection import BigfixConnection
from bigfix_adapter.exceptions import BigfixException
import json
import xml.etree.ElementTree as ET

from axonius.parsing_utils import parse_date


class BigfixAdapter(AdapterBase):

    class MyDevice(Device):
        agent_version = Field(str, 'Agent Version')
        bigfix_device_type = Field(str, "Device type")
        bigfix_computre_type = Field(str, "Computer type")

    def __init__(self):
        super().__init__(get_local_config_file(__file__))

    def _get_client_id(self, client_config):
        return client_config['Bigfix_Domain']

    def _connect_client(self, client_config):
        try:
            connection = BigfixConnection(logger=self.logger, domain=client_config["Bigfix_Domain"],
                                          verify_ssl=client_config["verify_ssl"])
            connection.set_credentials(username=client_config["username"], password=client_config["password"])
            with connection:
                pass  # check that the connection credentials are valid
            return connection
        except BigfixException as e:
            message = "Error connecting to client with domain {0}, reason: {1}".format(
                client_config['Bigfix_Domain'], str(e))
            raise ClientConnectionException(message)

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific Bigfix domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a Bigfix connection

        :return: A json with all the attributes returned from the Bigfix Server
        """
        with client_data:
            return client_data.get_device_list()

    def _clients_schema(self):
        """
        The schema BigfixAdapter expects from configs

        :return: JSON scheme
        """
        return {
            "items": [
                {
                    "name": "Bigfix_Domain",
                    "title": "Bigfix Domain",
                    "type": "string"
                },
                {
                    "name": "username",
                    "title": "User Name",
                    "type": "string"
                },
                {
                    "name": "password",
                    "title": "Password",
                    "type": "string",
                    "format": "password"
                },
                {
                    "name": "verify_ssl",
                    "title": "Verify SSL",
                    "type": "bool"
                }
            ],
            "required": [
                "Bigfix_Domain",
                "username",
                "password",
                "verify_ssl"
            ],
            "type": "array"
        }

    def _parse_raw_data(self, devices_raw_data):
        for device_raw_xml in devices_raw_data:
            try:
                device_raw = dict()
                for xml_property in ET.fromstring(device_raw_xml)[0]:
                    if xml_property.tag == 'Property':
                        if xml_property.attrib["Name"] in device_raw:
                            device_raw[xml_property.attrib["Name"]] += "," + str(xml_property.text)
                        else:
                            device_raw[xml_property.attrib["Name"]] = str(xml_property.text)
                device = self._new_device()
                if not device_raw.get("ID"):
                    continue
                else:
                    device.id = str(device_raw.get("ID"))
                device.hostname = device_raw.get("Computer Name", "")
                device.figure_os(device_raw.get("OS", ""))
                try:
                    device.add_nic(None, device_raw.get("IP Address", "").split(",") +
                                   device_raw.get("IPv6 Address", "").split(","), self.logger)
                except:
                    self.logger.exception("Problem adding nic to Bigfix")
                device.agent_version = device_raw.get("Agent Version", "")
                device.last_used_users = device_raw.get("User Name", "").split(",")
                device.last_seen = parse_date(device_raw.get("Last Report Time", ""))
                device.bigfix_device_type = device_raw.get("Device Type", "")
                device.bigfix_computre_type = device_raw.get("Computer Type", "")
                device.set_raw(device_raw)
                yield device
            except:
                self.logger.exception("Problem with fetching Bigfix Device")
