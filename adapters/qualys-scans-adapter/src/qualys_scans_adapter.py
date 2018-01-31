"""
QualysScansAdapter.py: An adapter for Qualys Scans Dashboard.
"""

__author__ = "Asaf & Tal"

import dateutil.parser

from axonius.device import Device
import axonius.adapter_exceptions
from axonius.adapter_base import AdapterBase
import qualys_scans_connection
import qualys_scans_exceptions
from axonius.utils.xml2json_parser import Xml2Json


QUALYS_SCANS_ITERATOR_FORMAT = """
<?xml version="1.0" encoding="UTF-8" ?>
<ServiceRequest>
 <preferences>
 <startFromId>{0}</startFromId>
 <limitResults>{1}</limitResults>
 </preferences>
</ServiceRequest>
"""

QUALYS_SCANS_DOMAIN = 'Qualys_Scans_Domain'
USERNAME = 'username'
PASSWORD = 'password'

ALL_HOSTS_URL = "asset/host/"
ALL_HOSTS_PARAMS = 'action=list&details=All&truncation_limit=1000&id_min=0&show_tags=1'
ALL_HOSTS_OUTPUT = 'HOST_LIST_OUTPUT'

VM_HOST_URL = "asset/host/vm/detection/"
VM_HOST_PARAMS = 'action=list&truncation_limit=1000&id_min=0&show_tags=1'
VM_HOST_OUTPUT = 'HOST_LIST_VM_DETECTION_OUTPUT'


class QualysScansAdapter(AdapterBase):

    class MyDevice(Device):
        pass

    def _get_client_id(self, client_config):
        return client_config[QUALYS_SCANS_DOMAIN]

    def _connect_client(self, client_config):
        try:
            connection = qualys_scans_connection.QualysScansConnection(logger=self.logger,
                                                                       domain=client_config[QUALYS_SCANS_DOMAIN])
            connection.set_credentials(username=client_config[USERNAME], password=client_config[PASSWORD])
            with connection:
                pass
            return connection
        except qualys_scans_exceptions. QualysScansAPILimitException as e:
            self.create_notification(f"Qualys API limit reached, devices will not be collected at this time, "
                                     f"please try again in {e.seconds_to_wait} seconds")
            raise e
        except qualys_scans_exceptions.QualysScansException as e:
            message = "Error connecting to client with domain {0}, reason: {1}".format(
                client_config[QUALYS_SCANS_DOMAIN], str(e))
            self.logger.exception(message)
            raise axonius.adapter_exceptions.ClientConnectionException(message)

    def _get_qualys_scan_results(self, client_data, url, params, output_key):
        with client_data:
            client_list = []
            while params:
                response = client_data.get(url + '?' + params, auth=client_data.auth, headers=client_data.headers)
                current_clients_page = Xml2Json(response.text).result
                try:
                    # if there's no response field - there are no clients
                    response_json = current_clients_page[output_key]['RESPONSE']
                    client_list.extend(response_json.get('HOST_LIST', {}).get('HOST'))
                except KeyError:
                    self.logger.warn(f"No devices found: {response.text}")
                    return client_list
                params = response_json.get('WARNING', {}).get('URL', "?").split("?")[1]
            return client_list

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific QualysScans domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a QualysScans connection

        :return: A json with all the attributes returned from the QualysScans Server
        """

        all_hosts = {device['ID']: device for device in self._get_qualys_scan_results(client_data, url=ALL_HOSTS_URL,
                                                                                      params=ALL_HOSTS_PARAMS,
                                                                                      output_key=ALL_HOSTS_OUTPUT)}
        vm_hosts = self._get_qualys_scan_results(client_data, url=VM_HOST_URL,
                                                 params=VM_HOST_PARAMS, output_key=VM_HOST_OUTPUT)

        for device in vm_hosts:
            all_hosts[device['ID']]['DETECTION_LIST'] = device.get('DETECTION_LIST', {})
        return all_hosts.values()

    def _clients_schema(self):
        """
        The schema QualysScansAdapter expects from configs

        :return: JSON scheme
        """
        return {
            "items": [
                {
                    "name": QUALYS_SCANS_DOMAIN,
                    "title": "Qualys Scanner Domain",
                    "type": "string"
                },
                {
                    "name": USERNAME,
                    "title": "User Name",
                    "type": "string"
                },
                {
                    "name": PASSWORD,
                    "title": "Password",
                    "type": "string",
                    "format": "password"
                }
            ],
            "required": [
                QUALYS_SCANS_DOMAIN,
                USERNAME,
                PASSWORD
            ],
            "type": "array"
        }

    def _parse_raw_data(self, devices_raw_data):
        no_timestamp_count = 0
        no_hostname_count = 0
        for device_raw in devices_raw_data:
            hostname = device_raw.get('DNS', device_raw.get('NETBIOS', ''))
            if hostname == '':
                no_hostname_count += 1
                continue
            else:
                try:
                    last_seen = device_raw.get('LAST_VM_SCANNED_DATE', device_raw.get('LAST_VULN_SCAN_DATETIME'))
                    if last_seen is None:
                        # No data on the last timestamp of the device. Not inserting this device.
                        no_timestamp_count += 1
                        continue

                    # Parsing the timestamp.
                    last_seen = dateutil.parser.parse(last_seen)
                except Exception:
                    self.logger.exception("An Exception was raised while getting and parsing the last_seen field.")
                    continue

                device = self._new_device()
                device.hostname = hostname
                device.figure_os(device_raw.get('OS', ''))
                device.last_seen = last_seen
                if 'IP' in device_raw:
                    device.add_nic('', [device_raw['IP']], self.logger)
                device.id = device_raw.get('ID')
                device.scanner = True
                device.set_raw(device_raw)
                yield device

        if no_timestamp_count != 0:
            self.logger.warning(f"Got {no_timestamp_count} with no timestamp while parsing data")

        if no_hostname_count != 0:
            self.logger.warning(f"Got {no_hostname_count} with no hostname while parsing data")

    def _correlation_cmds(self):
        """
        Correlation commands for QualysScans
        :return: shell commands that help correlations
        """

        self.logger.error("correlation_cmds is not implemented for qualys adapter")
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
        self.logger.error("_parse_correlation_results is not implemented for qualys adapter")
        raise NotImplementedError("_parse_correlation_results is not implemented for qualys adapter")
