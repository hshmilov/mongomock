import logging

logger = logging.getLogger(f'axonius.{__name__}')
from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.devices.device_adapter import DeviceAdapter, MAC_FIELD
from axonius.utils.files import get_local_config_file
from puppet_adapter.connection import PuppetConnection
from puppet_adapter.exceptions import PuppetException
from axonius.fields import Field
from axonius.utils.datetime import parse_date
from axonius.clients.rest.connection import RESTConnection


# TODO ofir: Change the return values protocol


class PuppetAdapter(AdapterBase):
    """ A class containing all the Puppet Servers capabilities.

    Check AdapterBase documentation for additional params and exception details.

    """

    class MyDeviceAdapter(DeviceAdapter):
        version = Field(str, "Puppet Version")

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    def _parse_correlation_results(self, correlation_cmd_result, os_type):
        logger.error("_parse_correlation_results is not implemented for puppet adapter")
        raise NotImplementedError("_parse_correlation_results is not implemented for puppet adapter")

    def _get_client_id(self, client_config):
        return client_config["puppet_server_name"]

    def _test_reachability(self, client_config):
        return RESTConnection.test_reachability(client_config.get("puppet_server_name"))

    def _connect_client(self, client_config):
        try:
            return PuppetConnection(
                client_config['puppet_server_name'],
                self._grab_file_contents(client_config['ca_file']),
                self._grab_file_contents(client_config['cert_file']),
                self._grab_file_contents(client_config['private_key']))
        except PuppetException as e:
            message = "Error getting information from puppet server {0}. reason: {1}".format(
                client_config["puppet_server_name"],
                str(e))
            logger.exception(message)
        except KeyError as e:
            if "puppet_server_name" in client_config:
                message = f"Key error for Puppet {0}. details: {1}".format(client_config["puppet_server_name"], str(e))
            else:
                message = "Missing Puppet name for configuration line"
            logger.exception(message)
        raise ClientConnectionException

    def _clients_schema(self):
        """
        The keys PuppetAdapter expects from configs.abs

        :return: list of tuples, First is the name of the variable, second is the type. 
                 For example [("puppet_server_name", "str"), ("password", "str")]
        """
        return {
            "items": [
                {
                    "name": "puppet_server_name",
                    "title": "Server Name",
                    "type": "string"
                },
                {
                    "name": "ca_file",
                    "title": "CA File",
                    "description": "The binary contents of the ca_file",
                    "type": "file"
                },
                {
                    "name": "cert_file",
                    "title": "Certificate File",
                    "description": "The binary contents of the cert_file",
                    "type": "file"
                },
                {
                    "name": "private_key",
                    "title": "Private Key File",
                    "description": "The binary contents of the private_key",
                    "type": "file"
                }
            ],
            "required": [
                "puppet_server_name",
                "ca_file",
                "cert_file",
                "private_key"
            ],
            "type": "array"
        }

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific Puppet Server

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a puppet server connection

        :return: A json with all the attributes returned from the Puppet Server
        """
        yield from client_data.get_device_list()

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._new_device_adapter()
            device.hostname = device_raw['hostname']
            device.figure_os(' '.join([device_raw["operatingsystem"],
                                       device_raw["architecture"],
                                       device_raw["kernel"]]))
            try:
                if 'minor' in device_raw['os']['release']:
                    device.os.major = int(float(device_raw["os"]['release']['major']))
                    device.os.minor = int(float(device_raw["os"]['release']['minor']))
                else:
                    temp_release = device_raw["os"]['release']['major'].split('.')
                    device.os.major = int(temp_release[0])
                    if len(temp_release) > 1:
                        # In case major contains minor also
                        device.os.minor = int(temp_release[1])
            except Exception as e:
                logger.exception("Cannot parse os release number")

            device.id = device_raw[u'certname']
            try:
                for inet in device_raw.get('networking', {}).get('interfaces', {}).values():
                    device.add_nic(inet.get(MAC_FIELD, ''),
                                   [x['address'] for x in inet.get('bindings', []) if x.get('address')] +
                                   [x['address'] for x in inet.get('bindings6', []) if x.get('address')])
            except Exception:
                logger.exception("Problem adding nic to puppte")
            device.version = device_raw.get("puppetversion", '')
            device.number_of_processes = device_raw.get("processors", {}).get("count")
            try:
                for software_name in device_raw.get("apt_package_dist_updates", []):
                    device.add_installed_software(name=software_name)
            except Exception:
                logger.exception("Problemn adding software to Puppet")
            device.last_seen = parse_date(str(device_raw.get("facts_timestamp", "")))
            device.set_raw(device_raw)
            yield device

    # Exported API functions - None for now

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent]
