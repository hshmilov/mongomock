import logging
logger = logging.getLogger(f'axonius.{__name__}')
from itertools import groupby

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.parsing import parse_date
from axonius.utils.files import get_local_config_file
from qualys_adapter.exceptions import QualysException
from qualys_adapter.connection import QualysConnection
from axonius.fields import Field


QUALYS_ITERATOR_FORMAT = """
<?xml version="1.0" encoding="UTF-8" ?>
<ServiceRequest>
 <preferences>
 <startFromId>{0}</startFromId>
 <limitResults>{1}</limitResults>
 </preferences>
</ServiceRequest>
"""

QUALYS_DOMAIN = 'Qualys_Domain'
USERNAME = 'username'
PASSWORD = 'password'


class QualysAdapter(AdapterBase):

    class MyDeviceAdapter(DeviceAdapter):
        agent_version = Field(str, "Qualys agent version")
        location = Field(str, "Qualys agent location")
        agent_status = Field(str, "Agent Status")

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    def _get_client_id(self, client_config):
        return client_config[QUALYS_DOMAIN]

    def _connect_client(self, client_config):
        try:
            connection = QualysConnection(domain=client_config[QUALYS_DOMAIN])
            connection.set_credentials(username=client_config[USERNAME], password=client_config[PASSWORD])
            with connection:
                pass
            return connection
        except QualysException as e:
            message = "Error connecting to client with domain {0}, reason: {1}".format(
                client_config[QUALYS_DOMAIN], str(e))
            logger.exception(message)
            raise ClientConnectionException(message)

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific Qualys domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a Qualys connection

        :return: A json with all the attributes returned from the Qualys Server
        """
        with client_data:
            last_id = 0
            has_more_records = 'true'
            client_list = []
            devices_count = 0
            while has_more_records == 'true':
                logger.info(f"Got {devices_count*1000} devices so far")
                devices_count += 1
                current_iterator_data = QUALYS_ITERATOR_FORMAT.format(last_id, 1000)
                current_clients_page = client_data.get_device_iterator(data=current_iterator_data)
                client_list.extend(current_clients_page['data'])
                last_id = current_clients_page.get('lastId', None)
                has_more_records = current_clients_page['hasMoreRecords']
            return client_list

    def _clients_schema(self):
        """
        The schema QualysAdapter expects from configs

        :return: JSON scheme
        """
        return {
            "items": [
                {
                    "name": QUALYS_DOMAIN,
                    "title": "Qualys Domain",
                    "type": "string"
                },
                {
                    "name": USERNAME,
                    "title": "Username",
                    "type": "string",
                },
                {
                    "name": PASSWORD,
                    "title": "Password",
                    "type": "string",
                    "format": PASSWORD
                }
            ],
            "required": [
                QUALYS_DOMAIN,
                USERNAME,
                PASSWORD
            ],
            "type": "array"
        }

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device_raw = device_raw.get('HostAsset', '')
            device = self._new_device_adapter()
            device.hostname = device_raw.get('name', '')
            device.figure_os(device_raw.get('os', ''))
            ifaces = device_raw.get('networkInterface', {}).get('list')
            try:
                for mac, ip_ifaces in groupby(ifaces, lambda i: i['HostAssetInterface']['macAddress']):
                    device.add_nic(mac, [ip_iface['HostAssetInterface']['address']
                                         for ip_iface in ip_ifaces])
            except Exception:
                logger.exception("Problem with adding nic to Qualys agent")
            device.id = device_raw['agentInfo']['agentId']
            device.last_seen = parse_date(str(device_raw.get('agentInfo', {}).get("lastCheckedIn", "")))
            device.agent_version = device_raw.get('agentInfo', {}).get("agentVersion", "")
            device.location = device_raw.get('agentInfo', {}).get("location", "")
            device.boot_time = parse_date(str(device_raw.get("lastSystemBoot", "")))
            device.agent_status = device_raw.get('agentInfo', {}).get('status')
            try:
                for software_raw in device_raw.get("software", {}).get("list", []):
                    device.add_installed_software(name=software_raw["HostAssetSoftware"]["name"],
                                                  version=software_raw["HostAssetSoftware"]["version"])
            except Exception:
                logger.exception("Problem with adding software to Qualys agent")
            device.set_raw(device_raw)
            yield device

    def _correlation_cmds(self):
        """
        Correlation commands for Qualys
        :return: shell commands that help correlations
        """

        logger.error("correlation_cmds is not implemented for qualys adapter")
        raise NotImplementedError("correlation_cmds is not implemented for qualys adapter")

    def _parse_correlation_results(self, correlation_cmd_result, os_type):
        """
        Parses (very easily) the correlation cmd result, or None if failed
        :type correlation_cmd_result: str
        :param correlation_cmd_result: result of running cmd on a machine
        :type os_type: str
        :param os_type: the type of machine ran upon
        :return:
        """
        logger.error("_parse_correlation_results is not implemented for qualys adapter")
        raise NotImplementedError("_parse_correlation_results is not implemented for qualys adapter")

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Vulnerability_Assessment, AdapterProperty.Agent, AdapterProperty.Manager]
